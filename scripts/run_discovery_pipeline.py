from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.candidate_normalization import normalize_candidate_rows
from lib.capture_pipeline import capture_urls
from lib.common import load_line_file, read_jsonl, utc_now_iso, write_jsonl
from lib.evidence_index import index_capture_paths
from lib.followup_queue import generate_followup_queue
from lib.run_model import build_run_layout, detect_git_revision, generate_run_id
from lib.search_pipeline import build_query_specs, search_duckduckgo
from lib.split_queue import generate_split_queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic discovery pipeline into repo conventions")
    parser.add_argument("query", nargs="*")
    parser.add_argument("--query-file")
    parser.add_argument("--run-id", help="Optional run slug, e.g. us-college-precollege-2026-04-13")
    parser.add_argument("--country", default="US")
    parser.add_argument("--region", default="UNK")
    parser.add_argument("--program-family")
    parser.add_argument("--city")
    parser.add_argument("--venue-name")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--allow-host-file")
    parser.add_argument("--deny-host-file")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--no-expand", action="store_true")
    parser.add_argument("--no-skip-existing-captures", action="store_true")
    args = parser.parse_args()

    run_id = generate_run_id(args.run_id, timestamp=utc_now_iso())
    layout = build_run_layout(run_id)
    layout.ensure_directories()

    queries = build_query_specs(
        seed_queries=args.query,
        query_file=args.query_file,
        expand_queries=not args.no_expand,
        country=args.country,
        region=args.region,
        program_family=args.program_family,
    )
    if not queries:
        parser.error("provide at least one query or --query-file")

    allow_hosts = load_line_file(Path(args.allow_host_file)) if args.allow_host_file else []
    deny_hosts = load_line_file(Path(args.deny_host_file)) if args.deny_host_file else []
    search_result = search_duckduckgo(
        queries=queries,
        allow_hosts=allow_hosts,
        deny_hosts=deny_hosts,
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        sleep_seconds=args.sleep_seconds,
    )
    raw_rows = search_result["results"]
    if args.limit:
        raw_rows = raw_rows[: args.limit]
    write_jsonl(layout.raw_query_log, search_result["query_log"])
    write_jsonl(layout.raw_search_results, raw_rows)
    write_jsonl(layout.reports_raw, raw_rows)

    capture_result = capture_urls(
        urls=[row["url"] for row in raw_rows],
        text_dir=layout.global_text_dir,
        html_dir=layout.global_html_dir,
        manifest_path=layout.raw_capture_manifest,
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        sleep_seconds=args.sleep_seconds,
        skip_existing=not args.no_skip_existing_captures,
    )

    normalized_rows = normalize_candidate_rows(
        raw_rows,
        defaults={
            "country": args.country,
            "region": args.region,
            "city": args.city,
            "venue_name": args.venue_name,
        },
    )
    write_jsonl(layout.reports_normalized, normalized_rows)
    write_jsonl(layout.staging_discovered, normalized_rows)

    followup_rows = generate_followup_queue(normalized_rows)
    write_jsonl(layout.reports_followup, followup_rows)
    write_jsonl(layout.staging_followup, followup_rows)

    split_rows, split_skeletons = generate_split_queue(normalized_rows)
    write_jsonl(layout.reports_split_queue, split_rows)
    write_jsonl(layout.staging_split_queue, split_rows)
    split_skeleton_path = layout.staging_run_dir / "split_stubs.jsonl"
    write_jsonl(split_skeleton_path, split_skeletons)

    capture_paths = []
    for row in read_jsonl(layout.raw_capture_manifest):
        markdown_path = row.get("markdown_path")
        if markdown_path and Path(markdown_path).exists():
            capture_paths.append(Path(markdown_path))
    evidence_rows = index_capture_paths(capture_paths, output_path=layout.reports_evidence_index)
    global_index_path = Path("data/normalized/evidence_index.jsonl")
    global_capture_paths = sorted(layout.global_text_dir.rglob("*.md"))
    index_capture_paths(global_capture_paths, output_path=global_index_path)

    summary = {
        "run_id": run_id,
        "started_at": layout.started_at,
        "git_revision": detect_git_revision(),
        "scope": {
            "country": args.country,
            "region": args.region,
            "program_family": args.program_family,
            "city": args.city,
            "venue_name": args.venue_name,
        },
        "inputs": {
            "seed_queries": [query.query for query in queries],
            "query_file": args.query_file,
            "allow_hosts": allow_hosts,
            "deny_hosts": deny_hosts,
        },
        "counts": {
            "queries": search_result["counts"]["queries"],
            "raw_results": len(raw_rows),
            "captured": capture_result["counts"]["captured"],
            "capture_failed": capture_result["counts"]["failed"],
            "normalized_candidates": len(normalized_rows),
            "followup_items": len(followup_rows),
            "split_tasks": len(split_rows),
            "evidence_index_rows": len(evidence_rows),
        },
        "outputs": {
            **layout.as_dict(),
            "global_evidence_index": str(global_index_path),
            "split_stub_path": str(split_skeleton_path),
        },
        "status": "ok",
    }
    layout.run_metadata.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    layout.reports_summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
