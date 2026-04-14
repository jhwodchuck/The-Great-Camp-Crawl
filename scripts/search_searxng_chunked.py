from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from lib.common import ensure_parent, load_line_file, read_jsonl, utc_now_iso, write_jsonl


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def write_query_file(path: Path, queries: list[str]) -> None:
    ensure_parent(path)
    path.write_text("\n".join(queries) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run scripts/search_searxng.py over a large query file in smaller deterministic chunks"
    )
    parser.add_argument("--query-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--query-log", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--pause-between-chunks", type=float, default=2.0)
    parser.add_argument("--searxng-url", default="http://localhost:8080")
    parser.add_argument("--searxng-engines")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.1)
    args = parser.parse_args()

    queries = load_line_file(Path(args.query_file))
    if not queries:
        parser.error("query file is empty")
    if args.chunk_size <= 0:
        parser.error("--chunk-size must be positive")

    query_chunks = chunked(queries, args.chunk_size)
    merged_results: list[dict[str, object]] = []
    merged_query_log: list[dict[str, object]] = []
    chunk_summaries: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="searxng-batch-") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        for chunk_index, query_chunk in enumerate(query_chunks, start=1):
            chunk_query_file = tmp_dir / f"chunk-{chunk_index:03d}-queries.txt"
            chunk_output = tmp_dir / f"chunk-{chunk_index:03d}-raw.jsonl"
            chunk_query_log = tmp_dir / f"chunk-{chunk_index:03d}-queries.jsonl"
            write_query_file(chunk_query_file, query_chunk)

            cmd = [
                sys.executable,
                "scripts/search_searxng.py",
                "--query-file",
                str(chunk_query_file),
                "--no-expand",
                "--output",
                str(chunk_output),
                "--query-log",
                str(chunk_query_log),
                "--searxng-url",
                args.searxng_url,
            ]
            if args.searxng_engines:
                cmd.extend(
                    [
                        "--searxng-engines",
                        args.searxng_engines,
                    ]
                )
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
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)

            chunk_summary: dict[str, object] = {
                "chunk_index": chunk_index,
                "chunk_queries": len(query_chunk),
                "returncode": completed.returncode,
            }
            if completed.stdout.strip():
                try:
                    chunk_summary["search_summary"] = json.loads(completed.stdout)
                except json.JSONDecodeError:
                    chunk_summary["stdout"] = completed.stdout.strip()
            if completed.stderr.strip():
                chunk_summary["stderr"] = completed.stderr.strip()

            if completed.returncode == 0:
                merged_results.extend(read_jsonl(chunk_output))
                merged_query_log.extend(read_jsonl(chunk_query_log))

            chunk_summaries.append(chunk_summary)
            print(json.dumps(chunk_summary, ensure_ascii=False))

            if args.pause_between_chunks and chunk_index < len(query_chunks):
                time.sleep(args.pause_between_chunks)

    output_path = Path(args.output)
    query_log_path = Path(args.query_log)
    summary_path = Path(args.summary_output)
    write_jsonl(output_path, merged_results)
    write_jsonl(query_log_path, merged_query_log)

    failed_chunks = [summary["chunk_index"] for summary in chunk_summaries if summary["returncode"] != 0]
    summary = {
        "generated_at": utc_now_iso(),
        "query_file": args.query_file,
        "chunk_size": args.chunk_size,
        "counts": {
            "queries": len(queries),
            "chunks": len(query_chunks),
            "failed_chunks": len(failed_chunks),
            "accepted_results": len(merged_results),
            "query_log_rows": len(merged_query_log),
        },
        "failed_chunk_indexes": failed_chunks,
        "outputs": {
            "output": str(output_path),
            "query_log": str(query_log_path),
            "summary": str(summary_path),
        },
        "chunks": chunk_summaries,
    }
    ensure_parent(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary["counts"], ensure_ascii=False))
    return 0 if not failed_chunks else 1


if __name__ == "__main__":
    raise SystemExit(main())
