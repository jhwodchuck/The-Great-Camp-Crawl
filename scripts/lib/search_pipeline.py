from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests

from lib.common import USER_AGENT, load_line_file, utc_now_iso, write_jsonl
from lib.url_utils import extract_host, is_host_allowed, normalize_url


DDG_API = "https://api.duckduckgo.com/"

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

    for seed in all_seeds:
        templates = ["{seed}"]
        if expand_queries:
            templates = [*DEFAULT_EXPANSIONS, *family_templates]
        for template in templates:
            query = template.format(seed=seed).strip()
            if country:
                query = f"{query} {country}".strip()
            if region:
                query = f"{query} {region}".strip()
            if query.lower() in seen:
                continue
            seen.add(query.lower())
            source = "file" if seed in file_queries else "cli"
            if template != "{seed}":
                source = f"{source}_expanded"
            specs.append(QuerySpec(query=query, source=source, parent_query=seed if query != seed else None))
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


def search_duckduckgo(
    queries: list[QuerySpec],
    output_path: str | None = None,
    allow_hosts: list[str] | None = None,
    deny_hosts: list[str] | None = None,
    timeout: int = 20,
    retries: int = 3,
    backoff_seconds: float = 1.0,
    sleep_seconds: float = 0.0,
) -> dict[str, Any]:
    allow_hosts = allow_hosts or []
    deny_hosts = deny_hosts or []
    accepted_urls: set[str] = set()
    results: list[dict[str, Any]] = []
    query_log: list[dict[str, Any]] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for query_index, spec in enumerate(queries):
        searched_at = utc_now_iso()
        params = {
            "q": spec.query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1,
            "skip_disambig": 0,
            "t": "the-great-camp-crawl",
        }
        try:
            response = _request_json(session, DDG_API, params, timeout, retries, backoff_seconds)
            payload = response.json()
            query_result_count = 0
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
                    host = extract_host(normalized_url)
                    result_status = "accepted"
                    if not is_host_allowed(normalized_url, allow_hosts, deny_hosts):
                        result_status = "filtered_host"
                    elif normalized_url in accepted_urls:
                        result_status = "duplicate_url"
                    if result_status == "accepted":
                        accepted_urls.add(normalized_url)
                        query_result_count += 1
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
                                "rank": rank,
                                "host": host,
                                "status": "discovered_raw",
                            }
                        )
            query_log.append(
                {
                    "query": spec.query,
                    "query_source": spec.source,
                    "query_parent": spec.parent_query,
                    "search_timestamp": searched_at,
                    "status": "ok",
                    "accepted_results": query_result_count,
                }
            )
        except requests.RequestException as exc:
            query_log.append(
                {
                    "query": spec.query,
                    "query_source": spec.source,
                    "query_parent": spec.parent_query,
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
