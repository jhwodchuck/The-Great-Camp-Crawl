#!/usr/bin/env python3
"""
scrape_aca_via_chrome.py

Uses headless Chrome (already running on --remote-debugging-port=9222)
to load the ACA Find-a-Camp page per state and extract real camp listings.

Chrome handles all cookies/JS/Cloudflare challenges automatically because
it's a real browser.

Usage:
    # Ensure Chrome is running:
    # google-chrome --remote-debugging-port=9222 --no-first-run \
    #   --user-data-dir=/tmp/chrome-camp-crawl &

    python scripts/scrape_aca_via_chrome.py \
        --states AZ NM UT NV \
        --output-dir reports/discovery \
        --concurrency 1

Requirements:
    .venv/bin/pip install websocket-client beautifulsoup4 requests
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import random
import urllib.parse
from pathlib import Path
from typing import Any

import requests
import websocket
from bs4 import BeautifulSoup

# ── Chrome CDP helpers ────────────────────────────────────────────────────────

CDP_BASE = "http://localhost:9222"

STATE_NAMES = {
    'AK': 'Alaska', 'AL': 'Alabama', 'AR': 'Arkansas', 'AZ': 'Arizona',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'IA': 'Iowa',
    'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'MA': 'Massachusetts', 'MD': 'Maryland',
    'ME': 'Maine', 'MI': 'Michigan', 'MN': 'Minnesota', 'MO': 'Missouri',
    'MS': 'Mississippi', 'MT': 'Montana', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'NE': 'Nebraska', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
    'NV': 'Nevada', 'NY': 'New York', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VA': 'Virginia', 'VT': 'Vermont', 'WA': 'Washington', 'WI': 'Wisconsin',
    'WV': 'West Virginia', 'WY': 'Wyoming'
}

_msg_id = 0

def _next_id() -> int:
    global _msg_id
    _msg_id += 1
    return _msg_id


def open_tab(cdp_base: str = CDP_BASE) -> str:
    """Open a new tab and return its WebSocket debugger URL."""
    resp = requests.get(f"{cdp_base}/json/new", timeout=10)
    resp.raise_for_status()
    return resp.json()["webSocketDebuggerUrl"]


def close_tab(ws_url: str, cdp_base: str = CDP_BASE) -> None:
    tab_id = ws_url.split("/")[-1]
    requests.get(f"{cdp_base}/json/close/{tab_id}", timeout=5)


def cdp(ws: websocket.WebSocket, method: str, params: dict | None = None) -> dict:
    mid = _next_id()
    ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        data = json.loads(ws.recv())
        if data.get("id") == mid:
            return data.get("result", {})


def navigate(ws: websocket.WebSocket, url: str, wait: float = 8.0) -> None:
    cdp(ws, "Page.enable")
    cdp(ws, "Page.navigate", {"url": url})
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            ws.settimeout(1.0)
            raw = ws.recv()
            data = json.loads(raw)
            if data.get("method") in ("Page.loadEventFired", "Page.frameStoppedLoading"):
                return
        except Exception:
            pass
    ws.settimeout(20.0)


def get_html(ws: websocket.WebSocket) -> str:
    result = cdp(ws, "Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True,
    })
    return result.get("result", {}).get("value", "")


# ── ACA page parsers ──────────────────────────────────────────────────────────

ACA_FIND_CAMP = "https://www.acacamps.org/campers-families/find-camp?program_type%5B%5D=Resident&state={state}"
ACA_GOOGLE = "https://www.google.com/search?q=site:acacamps.org+%22{state_enc}%22+%22resident+camp%22&num=20"


def parse_aca_find_camp_html(html: str, state: str) -> list[dict[str, Any]]:
    """Parse the ACA find-a-camp search results page."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # ACA uses article cards or list items for each camp
    # Try multiple selector strategies
    cards = (
        soup.select("article.camp-result") or
        soup.select("div.camp-listing") or
        soup.select(".views-row") or
        soup.select("li.camp-item") or
        soup.select(".view-content > div") or
        soup.select("article")
    )

    for card in cards:
        # Camp name
        name_el = card.find(["h2", "h3", "h4"]) or card.find(class_=["camp-name", "title"])
        if not name_el:
            continue
        name = name_el.get_text(" ", strip=True)
        if not name or len(name) < 3:
            continue

        # URL
        link = card.find("a", href=True)
        url = ""
        if link:
            href = link["href"]
            if href.startswith("/"):
                url = "https://www.acacamps.org" + href
            elif href.startswith("http"):
                url = href

        # Snippet / description
        snippet_el = card.find(class_=["snippet", "description", "field-content"]) or card.find("p")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

        results.append({
            "query": f"ACA Find-a-Camp state={state}",
            "query_source": "aca_find_camp_page",
            "title": name,
            "url": url or f"https://www.acacamps.org/campers-families/find-camp?state={state}",
            "normalized_url": (url or "").rstrip("/"),
            "snippet": snippet,
            "host": "www.acacamps.org",
            "source": "aca_find_camp",
            "provider": "chrome_cdp",
            "provider_rank": len(results) + 1,
            "status": "discovered_raw",
        })

    return results


def parse_google_results(html: str, query: str) -> list[dict[str, Any]]:
    """Fall back to parsing Google SERP for acacamps.org links."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for div in soup.select("div.g, div[data-hveid]"):
        a = div.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        if not href.startswith("http") or "acacamps.org" not in href:
            continue
        parsed = urllib.parse.urlparse(href)
        if "google.com" in parsed.netloc:
            continue

        title_el = div.find("h3")
        title = title_el.get_text(" ", strip=True) if title_el else href

        snippet = ""
        for span in div.find_all("span"):
            text = span.get_text(" ", strip=True)
            if len(text) > 40:
                snippet = text
                break

        results.append({
            "query": query,
            "query_source": "google_fallback",
            "title": title,
            "url": href,
            "normalized_url": href.rstrip("/"),
            "snippet": snippet,
            "host": parsed.netloc,
            "source": "google_serp",
            "provider": "chrome_cdp",
            "provider_rank": len(results) + 1,
            "status": "discovered_raw",
        })

    return results


# ── Per-state scrape ──────────────────────────────────────────────────────────

def scrape_state(state: str, out_dir: Path) -> dict[str, Any]:
    state = state.upper()
    full_state = STATE_NAMES.get(state, state)
    output_file = out_dir / f"us-{state.lower()}-aca-crawl.jsonl"

    logging.info(f"[{state}] Starting scrape for {full_state}...")

    ws_url = open_tab()
    ws = websocket.create_connection(ws_url, timeout=20)
    all_results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    try:
        cdp(ws, "Network.enable")
        cdp(ws, "Page.enable")

        # ── Strategy 1: ACA's own Find-a-Camp page (filtered to Resident) ──
        aca_url = ACA_FIND_CAMP.format(state=state)
        logging.info(f"[{state}] Loading ACA Find-a-Camp: {aca_url}")
        navigate(ws, aca_url, wait=12.0)
        time.sleep(4.0)  # let JS render the results
        html = get_html(ws)

        # Check if Cloudflare blocked us
        if "Just a moment" in html or "cf-browser-verification" in html:
            logging.warning(f"[{state}] Cloudflare challenge on ACA site — trying Google fallback")
            results = []
        else:
            results = parse_aca_find_camp_html(html, state)
            logging.info(f"[{state}] ACA page: {len(results)} raw results")

        for r in results:
            norm = r["normalized_url"]
            if norm not in seen_urls:
                seen_urls.add(norm)
                r["rank"] = len(all_results) + 1
                all_results.append(r)

        # ── Strategy 2: Google search (acacamps.org site: query) ──
        # Use 3 Google queries per state for better coverage
        google_queries = [
            f'site:acacamps.org "{full_state}" "resident camp"',
            f'site:acacamps.org "{full_state}" overnight camp',
            f'acacamps.org {full_state} ACA accredited overnight',
        ]

        for gq in google_queries:
            gurl = f"https://www.google.com/search?q={urllib.parse.quote_plus(gq)}&num=20"
            logging.info(f"[{state}] Google: {gq!r}")
            navigate(ws, gurl, wait=10.0)
            time.sleep(random.uniform(2.5, 4.5))
            ghtml = get_html(ws)

            # CAPTCHA check
            if "detected unusual traffic" in ghtml.lower() or "recaptcha" in ghtml.lower():
                logging.warning(f"[{state}] Google CAPTCHA — skipping remaining Google queries")
                break

            gr = parse_google_results(ghtml, gq)
            logging.info(f"[{state}] Google '{gq[:40]}...': {len(gr)} raw results")
            for r in gr:
                norm = r["normalized_url"]
                if norm not in seen_urls:
                    seen_urls.add(norm)
                    r["rank"] = len(all_results) + 1
                    all_results.append(r)

            time.sleep(random.uniform(3.0, 6.0))

    finally:
        try:
            ws.close()
        except Exception:
            pass
        close_tab(ws_url)

    # Write JSONL
    with output_file.open("w", encoding="utf-8") as fh:
        for r in all_results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    logging.info(f"[{state}] Done — {len(all_results)} results → {output_file}")
    return {"state": state, "results": len(all_results), "output": str(output_file)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape ACA directory via Chrome CDP")
    parser.add_argument("--states", nargs="+", required=True)
    parser.add_argument("--output-dir", default="reports/discovery")
    parser.add_argument("--concurrency", type=int, default=1,
                        help="States in parallel (keep at 1 to avoid CAPTCHA)")
    parser.add_argument("--cdp", default=CDP_BASE)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Verify Chrome is reachable
    try:
        r = requests.get(f"{args.cdp}/json/version", timeout=5)
        r.raise_for_status()
        logging.info(f"Chrome CDP connected: {r.json().get('Browser','?')}")
    except Exception as e:
        logging.error(f"Cannot reach Chrome on {args.cdp}: {e}")
        logging.error("Start Chrome with: google-chrome --remote-debugging-port=9222 "
                      "--user-data-dir=/tmp/chrome-camp-crawl &")
        return 1

    states = [s.upper() for s in args.states]
    summaries = []

    if args.concurrency == 1:
        for state in states:
            summary = scrape_state(state, out_dir)
            summaries.append(summary)
            time.sleep(random.uniform(2.0, 5.0))
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futs = {ex.submit(scrape_state, s, out_dir): s for s in states}
            for fut in concurrent.futures.as_completed(futs):
                try:
                    summaries.append(fut.result())
                except Exception as e:
                    logging.error(f"Error: {e}")

    print(json.dumps({"total_states": len(summaries), "results": summaries}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
