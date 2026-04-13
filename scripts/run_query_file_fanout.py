from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from lib.common import load_line_file, slugify


def build_run_id(prefix: str, index: int, query: str) -> str:
    query_slug = slugify(query)[:48].strip("-")
    return f"{prefix}-{index:02d}-{query_slug}".strip("-")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a query file as many small discovery pipeline runs, one query per run"
    )
    parser.add_argument("--query-file", required=True)
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--country", default="US")
    parser.add_argument("--region", default="")
    parser.add_argument("--program-family")
    parser.add_argument("--city")
    parser.add_argument("--venue-name")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--allow-host-file")
    parser.add_argument("--deny-host-file")
    parser.add_argument("--search-providers", default="instant_answer,lite_html")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--pause-between-runs", type=float, default=1.0)
    parser.add_argument("--no-expand", action="store_true")
    parser.add_argument("--no-skip-existing-captures", action="store_true")
    parser.add_argument("--ingest-after", action="store_true")
    args = parser.parse_args()

    queries = load_line_file(Path(args.query_file))
    if not queries:
        parser.error("query file is empty")

    summaries: list[dict[str, object]] = []
    base_cmd = [sys.executable, "scripts/run_discovery_pipeline.py"]

    for index, query in enumerate(queries, start=1):
        run_id = build_run_id(args.run_prefix, index, query)
        cmd = [*base_cmd, query, "--run-id", run_id, "--country", args.country, "--region", args.region]
        if args.program_family:
            cmd.extend(["--program-family", args.program_family])
        if args.city:
            cmd.extend(["--city", args.city])
        if args.venue_name:
            cmd.extend(["--venue-name", args.venue_name])
        if args.limit is not None:
            cmd.extend(["--limit", str(args.limit)])
        if args.allow_host_file:
            cmd.extend(["--allow-host-file", args.allow_host_file])
        if args.deny_host_file:
            cmd.extend(["--deny-host-file", args.deny_host_file])
        if args.search_providers:
            cmd.extend(["--search-providers", args.search_providers])
        cmd.extend(
            [
                "--timeout",
                str(args.timeout),
                "--retries",
                str(args.retries),
                "--backoff-seconds",
                str(args.backoff_seconds),
                "--sleep-seconds",
                str(args.sleep_seconds),
            ]
        )
        if args.no_expand:
            cmd.append("--no-expand")
        if args.no_skip_existing_captures:
            cmd.append("--no-skip-existing-captures")

        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        summary: dict[str, object] = {
            "query": query,
            "run_id": run_id,
            "returncode": completed.returncode,
        }
        if completed.stdout.strip():
            try:
                summary["pipeline_summary"] = json.loads(completed.stdout)
            except json.JSONDecodeError:
                summary["stdout"] = completed.stdout.strip()
        if completed.stderr.strip():
            summary["stderr"] = completed.stderr.strip()
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False))

        if args.pause_between_runs and index < len(queries):
            time.sleep(args.pause_between_runs)

    if args.ingest_after:
        completed = subprocess.run(
            [sys.executable, "scripts/ingest_discovery_reports.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        ingest_summary: dict[str, object] = {
            "step": "ingest_after",
            "returncode": completed.returncode,
        }
        if completed.stdout.strip():
            try:
                ingest_summary["summary"] = json.loads(completed.stdout)
            except json.JSONDecodeError:
                ingest_summary["stdout"] = completed.stdout.strip()
        if completed.stderr.strip():
            ingest_summary["stderr"] = completed.stderr.strip()
        print(json.dumps(ingest_summary, ensure_ascii=False))

    failed = sum(1 for item in summaries if item["returncode"] != 0)
    print(
        json.dumps(
            {
                "query_file": args.query_file,
                "run_prefix": args.run_prefix,
                "total_runs": len(summaries),
                "failed_runs": failed,
            },
            ensure_ascii=False,
        )
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
