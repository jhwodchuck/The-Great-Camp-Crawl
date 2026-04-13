from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.capture_pipeline import capture_urls
from lib.common import load_line_file, write_jsonl
from lib.search_pipeline import build_query_specs, search_duckduckgo


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DDG discovery and capture Markdown pages")
    parser.add_argument("query", nargs="*")
    parser.add_argument("--query-file")
    parser.add_argument("--out-jsonl", default="data/staging/discovered-ddg-captured.jsonl")
    parser.add_argument("--capture-dir", default="data/raw/evidence-pages/text")
    parser.add_argument("--html-dir", default="data/raw/evidence-pages/html")
    parser.add_argument("--manifest", default="data/raw/evidence-pages/manifests/discover_and_capture_manifest.jsonl")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--country")
    parser.add_argument("--region")
    parser.add_argument("--program-family")
    parser.add_argument("--allow-host-file")
    parser.add_argument("--deny-host-file")
    parser.add_argument("--no-expand", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    queries = build_query_specs(
        seed_queries=args.query,
        query_file=args.query_file,
        expand_queries=not args.no_expand,
        country=args.country,
        region=args.region,
        program_family=args.program_family,
    )
    search_result = search_duckduckgo(
        queries=queries,
        allow_hosts=load_line_file(Path(args.allow_host_file)) if args.allow_host_file else [],
        deny_hosts=load_line_file(Path(args.deny_host_file)) if args.deny_host_file else [],
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        sleep_seconds=args.sleep_seconds,
    )
    hits = search_result["results"]
    if args.limit:
        hits = hits[: args.limit]

    capture_result = capture_urls(
        urls=[row["url"] for row in hits],
        text_dir=Path(args.capture_dir),
        html_dir=Path(args.html_dir),
        manifest_path=Path(args.manifest),
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        sleep_seconds=args.sleep_seconds,
        skip_existing=not args.no_skip_existing,
    )

    capture_map = {row["normalized_source_url"]: row for row in capture_result["manifest"]}
    merged_rows = []
    for hit in hits:
        capture_row = capture_map.get(hit["normalized_url"], {})
        merged_rows.append(
            {
                **hit,
                "markdown_capture_path": capture_row.get("markdown_path"),
                "html_capture_path": capture_row.get("html_path"),
                "capture_status": capture_row.get("status"),
                "capture_error": capture_row.get("error"),
            }
        )
    write_jsonl(Path(args.out_jsonl), merged_rows)
    print(json.dumps({"output": args.out_jsonl, "records": len(merged_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
