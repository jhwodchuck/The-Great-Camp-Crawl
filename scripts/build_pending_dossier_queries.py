from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.common import ensure_parent, read_jsonl, utc_now_iso, write_jsonl
from lib.pending_dossier_queries import (
    DEFAULT_EXCLUDE_RECORD_BASES,
    DEFAULT_INCLUDE_REASONS,
    build_pending_query_pack,
)


def write_query_file(path: Path, queries: list[str]) -> None:
    ensure_parent(path)
    path.write_text("\n".join(queries) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic SearXNG query pack for skipped pending dossiers"
    )
    parser.add_argument("input", help="Skipped dossier JSONL file")
    parser.add_argument("--output-query-file", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--output-query-map", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument(
        "--include-reason",
        action="append",
        dest="include_reasons",
        help="Reason to include; repeat to override the default pending-like reason set",
    )
    parser.add_argument(
        "--exclude-record-basis",
        action="append",
        dest="exclude_record_bases",
        help="Record basis to exclude; repeat to override the default exclusion set",
    )
    parser.add_argument("--year", type=int, help="Override the current year for recent-activity queries")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    include_reasons = tuple(args.include_reasons or DEFAULT_INCLUDE_REASONS)
    exclude_record_bases = tuple(args.exclude_record_bases or DEFAULT_EXCLUDE_RECORD_BASES)
    pack = build_pending_query_pack(
        rows,
        include_reasons=include_reasons,
        exclude_record_bases=exclude_record_bases,
        current_year=args.year,
    )

    query_file_path = Path(args.output_query_file)
    manifest_path = Path(args.output_manifest)
    query_map_path = Path(args.output_query_map)
    summary_path = Path(args.summary_output)

    write_query_file(query_file_path, pack["query_lines"])
    write_jsonl(manifest_path, pack["manifest_rows"])
    write_jsonl(query_map_path, pack["query_rows"])

    summary = {
        "generated_at": utc_now_iso(),
        "input": str(Path(args.input)),
        "outputs": {
            "query_file": str(query_file_path),
            "manifest": str(manifest_path),
            "query_map": str(query_map_path),
            "summary": str(summary_path),
        },
        **pack["summary"],
    }
    ensure_parent(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
