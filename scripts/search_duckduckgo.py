from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

import requests

DDG_API = "https://api.duckduckgo.com/"
USER_AGENT = "TheGreatCampCrawl/0.1 (+https://github.com/jhwodchuck/The-Great-Camp-Crawl)"


@dataclass
class SearchHit:
    query: str
    title: str
    url: str
    snippet: str
    source: str = "duckduckgo_instant_answer"


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def flatten_related_topics(items: list[dict]) -> Iterable[dict]:
    for item in items:
        if "FirstURL" in item:
            yield item
        elif "Topics" in item:
            yield from flatten_related_topics(item["Topics"])


def build_query_variants(seed: str) -> list[str]:
    return [
        seed,
        f"{seed} overnight camp",
        f"{seed} residential summer camp",
        f"{seed} pre-college residential program",
        f"{seed} one week residential youth program",
    ]


def search_once(query: str, timeout: int = 30) -> list[SearchHit]:
    params = {
        "q": query,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1,
        "skip_disambig": 0,
        "t": "the-great-camp-crawl",
    }
    resp = requests.get(DDG_API, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    data = resp.json()

    hits: list[SearchHit] = []

    abstract_url = data.get("AbstractURL") or ""
    if abstract_url:
        hits.append(
            SearchHit(
                query=query,
                title=data.get("Heading") or abstract_url,
                url=abstract_url,
                snippet=data.get("AbstractText") or "",
            )
        )

    for item in data.get("Results", []):
        url = item.get("FirstURL") or ""
        if not url:
            continue
        hits.append(
            SearchHit(
                query=query,
                title=item.get("Text") or url,
                url=url,
                snippet=item.get("Text") or "",
            )
        )

    for item in flatten_related_topics(data.get("RelatedTopics", [])):
        url = item.get("FirstURL") or ""
        if not url:
            continue
        hits.append(
            SearchHit(
                query=query,
                title=item.get("Text") or url,
                url=url,
                snippet=item.get("Text") or "",
            )
        )

    return hits


def dedupe_hits(hits: Iterable[SearchHit]) -> list[SearchHit]:
    seen: set[str] = set()
    out: list[SearchHit] = []
    for hit in hits:
        key = hit.url.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed discovery using DuckDuckGo Instant Answer API")
    parser.add_argument("seed_query", help="Base query to search")
    parser.add_argument("--output", default="data/staging/discovered-ddg.jsonl")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    all_hits: list[SearchHit] = []
    for query in build_query_variants(args.seed_query):
        try:
            all_hits.extend(search_once(query))
        except requests.HTTPError as exc:
            print(json.dumps({"query": query, "error": f"http_error: {exc}"}))
        except requests.RequestException as exc:
            print(json.dumps({"query": query, "error": f"request_error: {exc}"}))
        time.sleep(args.sleep_seconds)

    deduped = dedupe_hits(all_hits)
    with open(args.output, "w", encoding="utf-8") as fh:
        for hit in deduped:
            host = urlparse(hit.url).netloc
            record = {
                "query": hit.query,
                "title": hit.title,
                "url": hit.url,
                "snippet": hit.snippet,
                "source": hit.source,
                "host": host,
                "url_slug": slugify(hit.url),
                "status": "discovered_raw",
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(deduped)} deduplicated hits to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
