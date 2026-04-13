from __future__ import annotations

import argparse
from pathlib import Path
from lib.candidate_normalization import normalize_candidate_rows
from lib.common import read_jsonl, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize discovery JSONL into repo candidate schema")
    parser.add_argument("input_jsonl")
    parser.add_argument("--output", required=True)
    parser.add_argument("--country", default="US")
    parser.add_argument("--region", default="UNK")
    parser.add_argument("--city")
    parser.add_argument("--venue-name")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input_jsonl))
    normalized = normalize_candidate_rows(
        rows,
        defaults={
            "country": args.country,
            "region": args.region,
            "city": args.city,
            "venue_name": args.venue_name,
        },
    )
    write_jsonl(Path(args.output), normalized)
    print(f"Wrote {len(normalized)} normalized candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
