from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
import websocket
from bs4 import BeautifulSoup

from lib.common import USER_AGENT, load_line_file, utc_now_iso, write_jsonl
from lib.url_utils import extract_host, is_host_allowed, normalize_url


DDG_API = "https://api.duckduckgo.com/"
DDG_LITE_HTML = "https://lite.duckduckgo.com/lite/"
GOOGLE_CDP = "http://localhost:9222"
GOOGLE_SEARCH = "https://www.google.com/search?q={q}&num=10&hl=en"
SEARXNG_BASE = "http://localhost:8080"

DEFAULT_EXPANSIONS = [
    "{seed}",
    "{seed} overnight camp",
    "{seed} residential summer camp",
    "{seed} youth overnight program",
]

IGNORED_SCOPE_TOKENS = {
    "",
    "all",
    "any",
    "multi",
    "na",
    "n/a",
    "national",
    "nationwide",
    "unk",
    "unknown",
}

PROGRAM_FAMILY_EXPANSIONS = {
    "college-pre-college": [
        "{seed} pre-college residential program",
        "{seed} summer residential high school program",
        "{seed} on-campus summer program for high school students",
    ],
    "sports": [
        "{seed} overnight sports camp",
        "{seed} residential athletic camp",
    ],
    "arts": [
        "{seed} residential arts camp",
    ],
    "music": [
        "{seed} residential music camp",
        "{seed} band camp overnight",
    ],
    "faith-based": [
        "{seed} youth retreat overnight",
        "{seed} faith-based summer camp residential",
    ],
    "family": [
        "{seed} family camp lodging",
    ],
}


@dataclass(frozen=True)
class QuerySpec:
    query: str
    source: str
    parent_query: str | None = None


def flatten_related_topics(items: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for item in items:
        if "FirstURL" in item:
            yield item
        elif "Topics" in item:
            yield from flatten_related_topics(item["Topics"])


def build_query_specs(
    seed_queries: list[str],
    query_file: str | None = None,
    expand_queries: bool = True,
    country: str | None = None,
    region: str | None = None,
    program_family: str | None = None,
) -> list[QuerySpec]:
    file_queries = load_line_file(Path(query_file)) if query_file else []
    all_seeds = [query.strip() for query in [*seed_queries, *file_queries] if query.strip()]
    seen: set[str] = set()
    specs: list[QuerySpec] = []

    family_templates = PROGRAM_FAMILY_EXPANSIONS.get((program_family or "").lower(), [])
    scope_parts = []
    for part in [country, region]:
        normalized = (part or "").strip()
        if not normalized or normalized.lower() in IGNORED_SCOPE_TOKENS:
            continue
        scope_parts.append(normalized)
    scope_suffix = " ".join(scope_parts).strip()

    for seed in all_seeds:
        templates = ["{seed}"]
        if expand_queries:
            templates = [*DEFAULT_EXPANSIONS, *family_templates]
        for template in templates:
            source = "file" if seed in file_queries else "cli"
            if template != "{seed}":
                source = f"{source}_expanded"
            base_query = template.format(seed=seed).strip()
            variants = [(base_query, source)]
            if scope_suffix:
                lowered = base_query.lower()
                if scope_suffix.lower() not in lowered:
                    variants.append((f"{base_query} {scope_suffix}".strip(), f"{source}_scoped"))
            for query, variant_source in variants:
                if query.lower() in seen:
                    continue
                seen.add(query.lower())
                specs.append(QuerySpec(query=query, source=variant_source, parent_query=seed if query != seed else None))
    return specs


def _request_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    timeout: int,
    retries: int,
    backoff_seconds: float,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(backoff_seconds * attempt)
    if last_error is None:
        raise RuntimeError("request failed without an error")
    raise last_error


def _request_text(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    timeout: int,
    retries: int,
    backoff_seconds: float,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(backoff_seconds * attempt)
    if last_error is None:
        raise RuntimeError("request failed without an error")
    raise last_error


def _parse_ddg_lite_url(href: str) -> str:
    href = unescape((href or "").strip())
    if not href:
        return ""
    absolute = urljoin("https://duckduckgo.com", href)
    parsed = urlsplit(absolute)
    query = parse_qs(parsed.query)
    uddg = query.get("uddg", [])
    if uddg:
        return unquote(uddg[0])
    return absolute


def _create_cdp_target(cdp_base: str, url: str) -> str:
    response = requests.put(f"{cdp_base}/json/new?{url}", timeout=10)
    response.raise_for_status()
    payload = response.json()
    ws_url = payload.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("missing webSocketDebuggerUrl from Chrome target response")
    return str(ws_url)


def _cdp_send(ws: websocket.WebSocket, method: str, params: dict[str, Any] | None = None, msg_id: int = 1) -> dict[str, Any]:
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        data = json.loads(ws.recv())
        if data.get("id") == msg_id:
            return data


def _wait_for_page_load(ws: websocket.WebSocket, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = json.loads(ws.recv())
        if data.get("method") in {"Page.loadEventFired", "Page.frameStoppedLoading"}:
            return


def _wait_for_google_results(ws: websocket.WebSocket, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    expression = (
        "JSON.stringify({"
        "href: location.href,"
        "ready: document.readyState,"
        "headings: document.querySelectorAll('h3').length,"
        "cards: document.querySelectorAll('div.MjjYud, div.g').length"
        "})"
    )
    while time.time() < deadline:
        result = _cdp_send(ws, "Runtime.evaluate", {"expression": expression, "returnByValue": True}, msg_id=30)
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


def _get_page_html(ws: websocket.WebSocket) -> str:
    result = _cdp_send(
        ws,
        "Runtime.evaluate",
        {"expression": "document.documentElement.outerHTML", "returnByValue": True},
        msg_id=20,
    )
    return result.get("result", {}).get("result", {}).get("value", "")


def _is_noise_result(url: str, title: str) -> bool:
    normalized_url = normalize_url(url)
    host = extract_host(normalized_url)
    lowered_title = (title or "").strip().lower()
    if host == "duckduckgo.com":
        return True
    if lowered_title == "more info":
        return True
    return False


def _search_instant_answer(
    session: requests.Session,
    spec: QuerySpec,
    timeout: int,
    retries: int,
    backoff_seconds: float,
    query_index: int,
    searched_at: str,
) -> list[dict[str, Any]]:
    params = {
        "q": spec.query,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1,
        "skip_disambig": 0,
        "t": "the-great-camp-crawl",
    }
    response = _request_json(session, DDG_API, params, timeout, retries, backoff_seconds)
    payload = response.json()
    results: list[dict[str, Any]] = []
    sections = [
        ("abstract", [payload] if payload.get("AbstractURL") else []),
        ("results", payload.get("Results", [])),
        ("related_topics", list(flatten_related_topics(payload.get("RelatedTopics", [])))),
    ]
    for section_name, items in sections:
        for rank, item in enumerate(items, start=1):
            url = item.get("AbstractURL") or item.get("FirstURL") or ""
            if not url:
                continue
            normalized_url = normalize_url(url)
            results.append(
                {
                    "query": spec.query,
                    "query_source": spec.source,
                    "query_parent": spec.parent_query,
                    "query_index": query_index,
                    "search_timestamp": searched_at,
                    "title": item.get("Heading") or item.get("Text") or url,
                    "url": url,
                    "normalized_url": normalized_url,
                    "snippet": item.get("AbstractText") or item.get("Text") or "",
                    "source": "duckduckgo_instant_answer",
                    "source_section": section_name,
                    "provider": "instant_answer",
                    "provider_rank": rank,
                    "host": extract_host(normalized_url),
                    "status": "discovered_raw",
                }
            )
    return results


def _search_lite_html(
    session: requests.Session,
    spec: QuerySpec,
    timeout: int,
    retries: int,
    backoff_seconds: float,
    query_index: int,
    searched_at: str,
) -> list[dict[str, Any]]:
    params = {"q": spec.query}
    response = _request_text(session, DDG_LITE_HTML, params, timeout, retries, backoff_seconds)
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, Any]] = []
    for rank, link in enumerate(soup.select("a.result-link"), start=1):
        url = _parse_ddg_lite_url(link.get("href", ""))
        if not url:
            continue
        title = link.get_text(" ", strip=True) or url
        if _is_noise_result(url, title):
            continue
        snippet = ""
        row = link.find_parent("tr")
        if row is not None:
            snippet_row = row.find_next_sibling("tr")
            if snippet_row is not None:
                snippet_cell = snippet_row.find("td", class_="result-snippet")
                if snippet_cell is not None:
                    snippet = snippet_cell.get_text(" ", strip=True)
        normalized_url = normalize_url(url)
        results.append(
            {
                "query": spec.query,
                "query_source": spec.source,
                "query_parent": spec.parent_query,
                "query_index": query_index,
                "search_timestamp": searched_at,
                "title": title,
                "url": url,
                "normalized_url": normalized_url,
                "snippet": snippet,
                "source": "duckduckgo_lite_html",
                "source_section": "lite_results",
                "provider": "lite_html",
                "provider_rank": rank,
                "host": extract_host(normalized_url),
                "status": "discovered_raw",
            }
        )
    return results


def _search_google_cdp(
    spec: QuerySpec,
    timeout: int,
    query_index: int,
    searched_at: str,
    cdp_base: str = GOOGLE_CDP,
) -> list[dict[str, Any]]:
    search_url = GOOGLE_SEARCH.format(q=urllib.parse.quote_plus(spec.query))
    ws_url = _create_cdp_target(cdp_base, "about:blank")
    ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
    try:
        _cdp_send(ws, "Page.enable", msg_id=10)
        _cdp_send(ws, "Runtime.enable", msg_id=11)
        _cdp_send(ws, "Page.navigate", {"url": search_url}, msg_id=12)
        _wait_for_google_results(ws, timeout=float(timeout))
        html = _get_page_html(ws)
    finally:
        ws.close()

    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    rank = 0
    for heading in soup.select("h3"):
        link = heading.find_parent("a", href=True)
        if link is None:
            continue
        url = (link.get("href") or "").strip()
        if not url.startswith("http"):
            continue
        normalized_url = normalize_url(url)
        if extract_host(normalized_url) == "google.com":
            continue
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        rank += 1
        title = heading.get_text(" ", strip=True) or url
        snippet = ""
        result_block = heading.find_parent(class_="MjjYud")
        if result_block is not None:
            snippet_node = result_block.select_one(".VwiC3b")
            if snippet_node is not None:
                snippet = snippet_node.get_text(" ", strip=True)
        results.append(
            {
                "query": spec.query,
                "query_source": spec.source,
                "query_parent": spec.parent_query,
                "query_index": query_index,
                "search_timestamp": searched_at,
                "title": title,
                "url": url,
                "normalized_url": normalized_url,
                "snippet": snippet,
                "source": "google_search_cdp",
                "source_section": "organic_results",
                "provider": "google_cdp",
                "provider_rank": rank,
                "host": extract_host(normalized_url),
                "status": "discovered_raw",
            }
        )
    return results


def _search_searxng(
    session: requests.Session,
    spec: QuerySpec,
    timeout: int,
    retries: int,
    backoff_seconds: float,
    query_index: int,
    searched_at: str,
    searxng_base: str = SEARXNG_BASE,
    searxng_engines: str | None = None,
) -> list[dict[str, Any]]:
    params = {
        "q": spec.query,
        "format": "json",
        "language": "en",
        "safesearch": 0,
    }
    if searxng_engines:
        params["engines"] = searxng_engines
    response = _request_json(session, f"{searxng_base}/search", params, timeout, retries, backoff_seconds)
    payload = response.json()
    results: list[dict[str, Any]] = []
    for rank, item in enumerate(payload.get("results", []), start=1):
        url = (item.get("url") or "").strip()
        if not url:
            continue
        normalized_url = normalize_url(url)
        title = item.get("title") or url
        snippet = item.get("content") or ""
        results.append(
            {
                "query": spec.query,
                "query_source": spec.source,
                "query_parent": spec.parent_query,
                "query_index": query_index,
                "search_timestamp": searched_at,
                "title": title,
                "url": url,
                "normalized_url": normalized_url,
                "snippet": snippet,
                "source": "searxng",
                "source_section": "organic_results",
                "provider": "searxng",
                "provider_rank": rank,
                "host": extract_host(normalized_url),
                "status": "discovered_raw",
            }
        )
    return results


def search_duckduckgo(
    queries: list[QuerySpec],
    output_path: str | None = None,
    allow_hosts: list[str] | None = None,
    deny_hosts: list[str] | None = None,
    providers: list[str] | None = None,
    timeout: int = 20,
    retries: int = 3,
    backoff_seconds: float = 1.0,
    sleep_seconds: float = 0.0,
    searxng_base: str = SEARXNG_BASE,
    searxng_engines: str | None = None,
) -> dict[str, Any]:
    allow_hosts = allow_hosts or []
    deny_hosts = deny_hosts or []
    providers = providers or ["instant_answer", "lite_html"]
    accepted_urls: set[str] = set()
    results: list[dict[str, Any]] = []
    query_log: list[dict[str, Any]] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for query_index, spec in enumerate(queries):
        searched_at = utc_now_iso()
        provider_accept_count = 0
        for provider in providers:
            try:
                if provider == "instant_answer":
                    provider_results = _search_instant_answer(
                        session, spec, timeout, retries, backoff_seconds, query_index, searched_at
                    )
                elif provider == "lite_html":
                    provider_results = _search_lite_html(
                        session, spec, timeout, retries, backoff_seconds, query_index, searched_at
                    )
                elif provider == "google_cdp":
                    provider_results = _search_google_cdp(spec, timeout, query_index, searched_at)
                elif provider == "searxng":
                    provider_results = _search_searxng(
                        session, spec, timeout, retries, backoff_seconds, query_index, searched_at,
                        searxng_base=searxng_base,
                        searxng_engines=searxng_engines,
                    )
                else:
                    raise ValueError(f"unsupported provider: {provider}")
                accepted_for_provider = 0
                for item in provider_results:
                    normalized_url = item["normalized_url"]
                    result_status = "accepted"
                    if not is_host_allowed(normalized_url, allow_hosts, deny_hosts):
                        result_status = "filtered_host"
                    elif normalized_url in accepted_urls:
                        result_status = "duplicate_url"
                    if result_status != "accepted":
                        continue
                    accepted_urls.add(normalized_url)
                    accepted_for_provider += 1
                    provider_accept_count += 1
                    item["rank"] = len(results) + 1
                    results.append(item)
                query_log.append(
                    {
                        "query": spec.query,
                        "query_source": spec.source,
                        "query_parent": spec.parent_query,
                        "provider": provider,
                        "search_timestamp": searched_at,
                        "status": "ok",
                        "raw_results": len(provider_results),
                        "accepted_results": accepted_for_provider,
                    }
                )
            except (requests.RequestException, ValueError) as exc:
                query_log.append(
                    {
                        "query": spec.query,
                        "query_source": spec.source,
                        "query_parent": spec.parent_query,
                        "provider": provider,
                        "search_timestamp": searched_at,
                        "status": "error",
                        "error": str(exc),
                    }
                )
        if sleep_seconds:
            time.sleep(sleep_seconds)

    if output_path:
        write_jsonl(Path(output_path), results)

    return {
        "query_log": query_log,
        "results": results,
        "counts": {
            "queries": len(queries),
            "accepted_results": len(results),
            "query_errors": sum(1 for row in query_log if row["status"] != "ok"),
        },
    }
