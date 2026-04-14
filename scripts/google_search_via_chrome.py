#!/usr/bin/env python3
"""
google_search_via_chrome.py

Drive headless Chrome via the DevTools Protocol (CDP) to execute Google
searches and extract result URLs/titles/snippets. Saves output as JSONL
in the same format that the rest of the discovery pipeline expects.

Usage:
    python scripts/google_search_via_chrome.py \
        --query "site:acacamps.org Arizona overnight camp" \
        --output /tmp/test.jsonl

    python scripts/google_search_via_chrome.py \
        --query-file data/seed-queries/my-queries.txt \
        --output reports/discovery/my-run.jsonl \
        --pages 3
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests
import websocket  # websocket-client

# ── CDP helpers ──────────────────────────────────────────────────────────────

DEFAULT_CDP = "http://localhost:9222"
GOOGLE_SEARCH = "https://www.google.com/search?q={q}&num=20&hl=en"


def get_ws_url(cdp_base: str = DEFAULT_CDP) -> str:
    resp = requests.put(f"{cdp_base}/json/new?about:blank", timeout=5)
    resp.raise_for_status()
    return resp.json()["webSocketDebuggerUrl"]


def cdp_send(ws: websocket.WebSocket, method: str, params: dict | None = None, msg_id: int = 1) -> dict:
    payload = json.dumps({"id": msg_id, "method": method, "params": params or {}})
    ws.send(payload)
    # drain until we get our response id back
    while True:
        raw = ws.recv()
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data
        # ignore events


def navigate_and_wait(ws: websocket.WebSocket, url: str, timeout: float = 15.0) -> None:
    cdp_send(ws, "Page.enable", msg_id=10)
    cdp_send(ws, "Runtime.enable", msg_id=11)
    cdp_send(ws, "Page.navigate", {"url": url}, msg_id=12)
    expression = (
        "JSON.stringify({"
        "href: location.href,"
        "ready: document.readyState,"
        "headings: document.querySelectorAll('h3').length,"
        "cards: document.querySelectorAll('div.MjjYud, div.g').length"
        "})"
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = cdp_send(ws, "Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
        }, msg_id=13)
        payload_raw = result.get("result", {}).get("result", {}).get("value")
        try:
            payload = json.loads(payload_raw or "{}")
        except json.JSONDecodeError:
            payload = {}
        href = str(payload.get("href") or "")
        ready = str(payload.get("ready") or "")
        headings = int(payload.get("headings") or 0)
        cards = int(payload.get("cards") or 0)
        if "google." in href and "/search" in href and ready == "complete" and (headings > 0 or cards > 0):
            return
        time.sleep(0.5)


def get_html(ws: websocket.WebSocket) -> str:
    result = cdp_send(ws, "Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True,
    }, msg_id=20)
    return result.get("result", {}).get("result", {}).get("value", "")


def extract_google_results(html: str, query: str) -> list[dict[str, Any]]:
    """Parse Google SERP HTML for result links/titles/snippets."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen_urls: set[str] = set()
    rank = 0

    for heading in soup.select("h3"):
        a = heading.find_parent("a", href=True)
        if not a:
            continue
        href = a["href"]
        if not href.startswith("http"):
            continue
        # Skip Google-internal links
        parsed = urllib.parse.urlparse(href)
        if "google.com" in parsed.netloc:
            continue
        normalized_url = href.rstrip("/")
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        title = heading.get_text(" ", strip=True) or href
        snippet = ""
        result_block = heading.find_parent(class_="MjjYud")
        if result_block is not None:
            snippet_node = result_block.select_one(".VwiC3b")
            if snippet_node is not None:
                snippet = snippet_node.get_text(" ", strip=True)

        rank += 1
        items.append({
            "query": query,
            "query_source": "google_chrome_cdp",
            "title": title,
            "url": href,
            "normalized_url": normalized_url,
            "snippet": snippet,
            "host": parsed.netloc,
            "source": "google_search",
            "provider": "google_chrome_cdp",
            "provider_rank": rank,
            "status": "discovered_raw",
        })

    return items


# ── Main search driver ───────────────────────────────────────────────────────

def search_google_via_chrome(
    queries: list[str],
    output_path: Path,
    cdp_base: str = DEFAULT_CDP,
    pages: int = 2,
    sleep_between: float = 3.0,
    allow_hosts: list[str] | None = None,
) -> dict[str, Any]:
    all_results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    errors = 0

    ws_url = get_ws_url(cdp_base)
    ws = websocket.create_connection(ws_url, timeout=20, suppress_origin=True)

    try:
        cdp_send(ws, "Page.enable", msg_id=1)

        for qi, query in enumerate(queries, start=1):
            for page in range(pages):
                start = page * 20
                url = GOOGLE_SEARCH.format(q=urllib.parse.quote_plus(query))
                if start:
                    url += f"&start={start}"

                logging.info(f"[{qi}/{len(queries)}] page={page+1} Google: {query!r}")
                try:
                    navigate_and_wait(ws, url, timeout=15.0)
                    time.sleep(2.0)  # let JS render
                    html = get_html(ws)
                    results = extract_google_results(html, query)

                    accepted = 0
                    for r in results:
                        # filter hosts if requested
                        if allow_hosts:
                            if not any(h in r["host"] for h in allow_hosts):
                                continue
                        norm = r["normalized_url"]
                        if norm in seen_urls:
                            continue
                        seen_urls.add(norm)
                        r["rank"] = len(all_results) + 1
                        all_results.append(r)
                        accepted += 1

                    logging.info(f"  → {len(results)} raw, {accepted} accepted")

                    if len(results) == 0:
                        break  # no results on this page, no point paginating

                except Exception as exc:
                    logging.warning(f"  Error: {exc}")
                    errors += 1

                if sleep_between:
                    time.sleep(sleep_between)
    finally:
        ws.close()

    # Write output JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for r in all_results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    return {
        "output": str(output_path),
        "queries": len(queries),
        "accepted_results": len(all_results),
        "errors": errors,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Google search via Chrome CDP")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--query", help="Single search query")
    grp.add_argument("--query-file", help="File with one query per line")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--pages", type=int, default=2, help="SERP pages per query")
    parser.add_argument("--sleep", type=float, default=3.0, help="Seconds between requests")
    parser.add_argument("--cdp", default=DEFAULT_CDP, help="Chrome CDP base URL")
    parser.add_argument("--allow-host", action="append", dest="allow_hosts",
                        help="Only keep results matching this host (repeatable)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.query:
        queries = [args.query]
    else:
        queries = [l.strip() for l in Path(args.query_file).read_text().splitlines()
                   if l.strip() and not l.startswith("#")]

    summary = search_google_via_chrome(
        queries=queries,
        output_path=Path(args.output),
        cdp_base=args.cdp,
        pages=args.pages,
        sleep_between=args.sleep,
        allow_hosts=args.allow_hosts,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
