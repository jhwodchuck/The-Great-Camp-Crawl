"""
run_batch_searxng.py — Batch runner for SearXNG discovery scans.

Iterates over all discovery prompt files, extracts search angles and metadata,
and calls scripts/search_searxng.py for each run via subprocess.

Usage:
    python scripts/run_batch_searxng.py [options]

Options:
    --sleep-seconds FLOAT       Delay between queries within a run (default: 3.0)
    --inter-run-delay FLOAT     Delay between runs (default: 5.0)
    --skip-existing             Skip runs where output file already exists (default: True)
    --no-skip-existing          Force re-run even if output file exists
    --dry-run                   Print what would be run without executing
    --scan-type TYPE            Filter: country_region | college_precollege | all (default: all)
    --country CODE              Filter: US | CA | MX | all (default: all)
    --limit INT                 Only process first N files
    --prompt-dir PATH           Scan only this specific prompt directory instead of both
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROMPT_DIRS = {
    "country_region": REPO_ROOT / "prompts/discovery/01-country-and-region-scanner",
    "college_precollege": REPO_ROOT
    / "prompts/discovery/02-college-precollege-scanner-pack",
}

SKIP_FILENAMES = {"README.md", "TEMPLATE.md"}


def parse_args():
    parser = argparse.ArgumentParser(description="Batch SearXNG discovery runner.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=3.0,
        help="Delay between queries within a run (default: 3.0)",
    )
    parser.add_argument(
        "--inter-run-delay",
        type=float,
        default=5.0,
        help="Delay between runs (default: 5.0)",
    )
    parser.add_argument(
        "--skip-existing",
        dest="skip_existing",
        action="store_true",
        default=True,
        help="Skip runs where output file already exists (default)",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Force re-run even if output file exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be run without executing",
    )
    parser.add_argument(
        "--scan-type",
        choices=["country_region", "college_precollege", "all"],
        default="all",
        help="Filter which scan types to run (default: all)",
    )
    parser.add_argument(
        "--country",
        default="all",
        help="Filter to a specific country: US, CA, MX, or all (default: all)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Only process the first N files"
    )
    parser.add_argument(
        "--prompt-dir",
        type=Path,
        default=None,
        help="Scan only this specific prompt directory instead of both",
    )
    return parser.parse_args()


def extract_backtick_value(line):
    """Extract text inside the first pair of backticks on a line."""
    m = re.search(r"`([^`]+)`", line)
    return m.group(1) if m else None


def extract_last_backtick_value(line):
    """Extract text inside the last pair of backticks on a line."""
    matches = re.findall(r"`([^`]+)`", line)
    return matches[-1] if matches else None


def parse_prompt_file(path, scan_type):
    """Parse a discovery prompt .md file. Returns a dict or None if unparseable."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    run_slug = None
    country = None
    region = None
    angles = []
    in_angles = False

    for line in lines:
        stripped = line.strip()

        if "run_slug" in stripped and "`" in stripped:
            val = extract_last_backtick_value(stripped)
            if val and val != "run_slug":
                run_slug = val

        if re.search(r"`country`", stripped) and "`" in stripped:
            val = extract_last_backtick_value(stripped)
            if val and val != "country" and len(val) == 2 and val.isalpha():
                country = val.upper()

        if re.search(r"`region`", stripped) and "`" in stripped:
            val = extract_last_backtick_value(stripped)
            if val and val != "region":
                region = val.upper()

        if stripped == "Search angles to cover:":
            in_angles = True
            continue

        if in_angles:
            if stripped.startswith("- `") or stripped.startswith("- \\`"):
                val = extract_last_backtick_value(stripped)
                if val:
                    angles.append(val)
            elif stripped.startswith("#"):
                in_angles = False

    if not run_slug or not country or not region or not angles:
        return None

    return {
        "run_slug": run_slug,
        "country": country,
        "region": region,
        "scan_type": scan_type,
        "angles": angles,
        "source_file": path,
    }


def collect_prompt_files(prompt_dir_override, scan_type_filter):
    """Collect (path, scan_type) tuples for all eligible prompt files."""
    entries = []

    if prompt_dir_override:
        # Determine scan_type from directory name if possible
        dir_name = prompt_dir_override.name
        if "01-country" in dir_name:
            st = "country_region"
        elif "02-college" in dir_name:
            st = "college_precollege"
        else:
            st = "unknown"
        dirs_to_scan = [(prompt_dir_override, st)]
    else:
        dirs_to_scan = list(PROMPT_DIRS.items())  # (scan_type, path) — swap below
        dirs_to_scan = [(path, st) for st, path in PROMPT_DIRS.items()]

    for base_dir, scan_type in dirs_to_scan:
        if scan_type_filter != "all" and scan_type != scan_type_filter:
            continue
        if not base_dir.exists():
            print(f"[warn] Prompt directory not found, skipping: {base_dir}")
            continue
        for md_file in sorted(base_dir.rglob("*.md")):
            if md_file.name in SKIP_FILENAMES:
                continue
            entries.append((md_file, scan_type))

    return entries


def build_command(record, sleep_seconds):
    """Build the subprocess argument list for a search run."""
    script = str(REPO_ROOT / "scripts/search_searxng.py")
    output_path = str(REPO_ROOT / f"data/staging/searxng-{record['run_slug']}.jsonl")

    cmd = [sys.executable, script]
    for angle in record["angles"]:
        cmd.append(angle)
    cmd += [
        "--no-expand",
        "--country",
        record["country"],
        "--region",
        record["region"],
        "--output",
        output_path,
        "--sleep-seconds",
        str(sleep_seconds),
        "--backoff-seconds",
        "2.0",
    ]
    return cmd, output_path


def main():
    args = parse_args()

    entries = collect_prompt_files(args.prompt_dir, args.scan_type)

    if args.country != "all":
        country_filter = args.country.upper()
    else:
        country_filter = None

    # Parse all files first
    records = []
    for path, scan_type in entries:
        rec = parse_prompt_file(path, scan_type)
        if rec is None:
            print(
                f"[warn] Could not parse or incomplete: {path.relative_to(REPO_ROOT)}"
            )
            continue
        if country_filter and rec["country"] != country_filter:
            continue
        records.append(rec)

    if args.limit:
        records = records[: args.limit]

    total = len(records)
    skipped = 0
    executed = 0
    failed = 0

    print(f"[batch] {total} run(s) to process.")

    for i, rec in enumerate(records, 1):
        run_slug = rec["run_slug"]
        cmd, output_path = build_command(rec, args.sleep_seconds)
        output_exists = Path(output_path).exists()

        prefix = f"[{i}/{total}] {run_slug}"

        if args.skip_existing and output_exists:
            print(f"{prefix} — SKIP (output exists: {output_path})")
            skipped += 1
            continue

        print(
            f"{prefix} — {len(rec['angles'])} angle(s), country={rec['country']}, region={rec['region']}"
        )

        if args.dry_run:
            print(f"  DRY-RUN cmd: {' '.join(repr(a) for a in cmd)}")
            executed += 1
        else:
            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                print(f"  [error] {run_slug} exited with code {result.returncode}")
                failed += 1
            else:
                executed += 1

        if i < total:
            if not args.dry_run:
                print(f"  [sleep] inter-run delay {args.inter_run_delay}s …")
                time.sleep(args.inter_run_delay)

    print()
    print("=" * 60)
    print(
        f"Summary: total={total}  skipped={skipped}  executed={executed}  failed={failed}"
    )


if __name__ == "__main__":
    main()
