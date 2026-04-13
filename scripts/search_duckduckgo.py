from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.common import load_line_file, write_jsonl
from lib.search_pipeline import build_query_specs, search_duckduckgo


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed discovery using DuckDuckGo Instant Answer API")
    parser.add_argument("seed_query", nargs="*", help="Base query or queries to search")
    parser.add_argument("--query-file", help="One query per line; blank lines and comments are ignored")
    parser.add_argument("--output", default="data/staging/discovered-ddg.jsonl")
    parser.add_argument("--query-log")
    parser.add_argument("--country")
    parser.add_argument("--region")
    parser.add_argument("--program-family")
    parser.add_argument("--no-expand", action="store_true")
    parser.add_argument("--allow-host-file")
    parser.add_argument("--deny-host-file")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    args = parser.parse_args()

    queries = build_query_specs(
        seed_queries=args.seed_query,
        query_file=args.query_file,
        expand_queries=not args.no_expand,
        country=args.country,
        region=args.region,
        program_family=args.program_family,
    )
    if not queries:
        parser.error("provide at least one seed query or --query-file")

    result = search_duckduckgo(
        queries=queries,
        output_path=args.output,
        allow_hosts=load_line_file(Path(args.allow_host_file)) if args.allow_host_file else [],
        deny_hosts=load_line_file(Path(args.deny_host_file)) if args.deny_host_file else [],
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        sleep_seconds=args.sleep_seconds,
    )
    if args.query_log:
        write_jsonl(Path(args.query_log), result["query_log"])

    print(
        json.dumps(
            {
                "output": args.output,
                "queries": result["counts"]["queries"],
                "accepted_results": result["counts"]["accepted_results"],
                "query_errors": result["counts"]["query_errors"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
