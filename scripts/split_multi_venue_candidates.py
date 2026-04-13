from __future__ import annotations

import argparse
from pathlib import Path

from lib.common import read_jsonl, write_jsonl
from lib.split_queue import generate_split_queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate split tasks for multi-venue candidates")
    parser.add_argument("input_jsonl")
    parser.add_argument("--output", required=True, help="Split-task queue output path")
    parser.add_argument("--skeleton-output", help="Optional split stub output path")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input_jsonl))
    tasks, skeletons = generate_split_queue(rows)
    write_jsonl(Path(args.output), tasks)
    if args.skeleton_output:
        write_jsonl(Path(args.skeleton_output), skeletons)
    print(f"Wrote {len(tasks)} split tasks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
