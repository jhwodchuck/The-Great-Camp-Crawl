from __future__ import annotations

import time
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from lib.common import USER_AGENT, load_line_file, utc_now_iso, write_jsonl
from lib.url_utils import extract_host, is_host_allowed, normalize_url


DDG_API = "https://api.duckduckgo.com/"
DDG_LITE_HTML = "https://lite.duckduckgo.com/lite/"

DEFAULT_EXPANSIONS = [
    "{seed}",
    "{seed} overnight camp",
    "{seed} residential summer camp",
    "{seed} youth overnight program",
]

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
    scope_suffix = " ".join(part for part in [country, region] if part).strip()

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
                "title": link.get_text(" ", strip=True) or url,
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
