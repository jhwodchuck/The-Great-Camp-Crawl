from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_step(cmd: list[str]) -> None:
    print(json.dumps({"running": cmd}, ensure_ascii=False))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DDG discovery pipeline into repo conventions")
    parser.add_argument("query")
    parser.add_argument("--slug", required=True, help="Short run slug, e.g. us_candidates_2026-04-13")
    parser.add_argument("--country", default="US")
    parser.add_argument("--region", default="UNK")
    parser.add_argument("--city")
    parser.add_argument("--venue-name")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    reports_dir = Path("reports/discovery")
    staging_dir = Path("data/staging")
    reports_dir.mkdir(parents=True, exist_ok=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    raw_hits = reports_dir / f"{args.slug}_ddg_raw.jsonl"
    captured = reports_dir / f"{args.slug}_captured.jsonl"
    normalized = reports_dir / f"{args.slug}.jsonl"
    evidence_index = reports_dir / f"{args.slug}_evidence_index.jsonl"
    staging_copy = staging_dir / f"{args.slug}.jsonl"

    run_step([
        sys.executable,
        "scripts/search_duckduckgo.py",
        args.query,
        "--output",
        str(raw_hits),
    ])

    run_step([
        sys.executable,
        "scripts/discover_and_capture.py",
        args.query,
        "--out-jsonl",
        str(captured),
        "--limit",
        str(args.limit),
    ])

    normalize_cmd = [
        sys.executable,
        "scripts/ddg_discovery_to_candidate_schema.py",
        str(raw_hits),
        "--output",
        str(normalized),
        "--country",
        args.country,
        "--region",
        args.region,
    ]
    if args.city:
        normalize_cmd.extend(["--city", args.city])
    if args.venue_name:
        normalize_cmd.extend(["--venue-name", args.venue_name])
    run_step(normalize_cmd)

    run_step([
        sys.executable,
        "scripts/capture_to_evidence_index.py",
        "data/raw/evidence-pages/text",
        "--output",
        str(evidence_index),
    ])

    staging_copy.write_text(normalized.read_text(encoding="utf-8"), encoding="utf-8")

    summary = {
        "raw_hits": str(raw_hits),
        "captured": str(captured),
        "normalized": str(normalized),
        "staging_copy": str(staging_copy),
        "evidence_index": str(evidence_index),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
