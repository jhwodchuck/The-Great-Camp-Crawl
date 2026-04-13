from __future__ import annotations

import argparse
from pathlib import Path

from lib.common import read_jsonl, write_jsonl
from lib.followup_queue import generate_followup_queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic follow-up queue items from normalized candidates")
    parser.add_argument("input_jsonl")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input_jsonl))
    followups = generate_followup_queue(rows)
    write_jsonl(Path(args.output), followups)
    print(f"Wrote {len(followups)} follow-up items to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
