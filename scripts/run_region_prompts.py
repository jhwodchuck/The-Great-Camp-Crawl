#!/usr/bin/env python3
"""
Run region discovery prompts using SearXNG, producing discovery report JSON files.

Reads prompt files from prompts/discovery/01-country-and-region-scanner/us/
Skips states that already have a matching report in reports/discovery/
Runs SearXNG searches for each state's search angles
Saves discovery report JSON in the standard scan format

Usage:
    # Run all unprocessed states
    python scripts/run_region_prompts.py

    # Run specific states
    python scripts/run_region_prompts.py --regions NC WI OR

    # Preview what would run without running
    python scripts/run_region_prompts.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.search_pipeline import build_query_specs, search_duckduckgo

PROMPTS_DIR = Path("prompts/discovery/01-country-and-region-scanner/us")
REPORTS_DIR = Path("reports/discovery")
SEARXNG_BASE = "http://localhost:8080"


def parse_prompt(path: Path) -> dict:
    """Extract run_slug, country, region, region_name, and search angles from a prompt file."""
    text = path.read_text()

    def first_match(pattern: str, flags: int = 0) -> str | None:
        m = re.search(pattern, text, flags)
        return m.group(1) if m else None

    run_slug = first_match(r"`run_slug`:\s*`([^`]+)`")
    country = first_match(r"^- `country`:\s*`([^`]+)`", re.MULTILINE) or "US"
    region = first_match(r"^- `region`:\s*`([^`]+)`", re.MULTILINE)
    region_name = first_match(r"^- `region_name`:\s*`([^`]+)`", re.MULTILINE)

    # Extract search angles — lines like: - `"overnight summer camp" "Texas"`
    angles: list[str] = []
    in_angles = False
    for line in text.splitlines():
        if "Search angles to cover:" in line:
            in_angles = True
            continue
        if in_angles:
            stripped = line.strip()
            m = re.match(r"^-\s+`(.+)`$", stripped)
            if m:
                angles.append(m.group(1))
            elif stripped and not stripped.startswith("-") and angles:
                break  # end of section

    return {
        "run_slug": run_slug,
        "country": country,
        "region": region,
        "region_name": region_name,
        "search_angles": angles,
    }


def result_to_candidate(result: dict, region: str, country: str, query: str) -> dict:
    """Convert a SearXNG search result into the discovery report candidate schema."""
    return {
        "candidate_name": result.get("title", ""),
        "translated_name_hint": None,
        "operator_name": None,
        "venue_name": None,
        "city": None,
        "region": region,
        "country": country,
        "canonical_url": result.get("url", ""),
        "supporting_urls": [],
        "directory_source_url": None,
        "source_language": "en",
        "program_family_tags": [],
        "camp_type_tags": [],
        "candidate_shape": "venue_unconfirmed",
        "priority_flags": {
            "likely_college_precollege": None,
            "likely_one_week_plus": None,
        },
        "duration_hint_text": None,
        "overnight_evidence": {
            "snippet": result.get("snippet"),
            "url": result.get("url"),
        },
        "recent_activity_evidence": {
            "snippet": None,
            "url": None,
            "date_text": None,
        },
        "notes": f"searxng | query: {query}",
        "validation_needs": ["confirm_overnight", "confirm_active", "confirm_venue"],
        "confidence": "low",
    }


def run_state(meta: dict, args: argparse.Namespace) -> dict | None:
    """Search all angles for one state and return the assembled report, or None on fatal error."""
    run_slug = meta["run_slug"]
    region = meta["region"]
    country = meta["country"]
    angles = meta["search_angles"]

    if not run_slug or not region or not angles:
        print(f"  [SKIP] incomplete metadata: slug={run_slug} region={region} angles={len(angles)}")
        return None

    print(f"  {len(angles)} angle(s) to search...")

    all_results: list[dict] = []
    queries_used: list[str] = []

    for angle in angles:
        try:
            specs = build_query_specs(
                seed_queries=[angle],
                expand_queries=False,
                country=country,
                region=region,
            )
            result = search_duckduckgo(
                queries=specs,
                providers=["searxng"],
                searxng_base=args.searxng_url,
                timeout=args.timeout,
                retries=2,
                backoff_seconds=1.0,
                sleep_seconds=args.sleep_seconds,
            )
            hits = result.get("results", [])
            print(f"    {angle!r}: {len(hits)} hits")
            for r in hits:
                all_results.append({**r, "_query": angle})
            queries_used.append(angle)
            time.sleep(args.sleep_seconds)
        except Exception as exc:
            print(f"    ERROR on {angle!r}: {exc}")

    # Deduplicate by normalized_url, preserving insertion order
    seen: set[str] = set()
    candidates: list[dict] = []
    for r in all_results:
        url_key = r.get("normalized_url") or r.get("url", "")
        if url_key and url_key not in seen:
            seen.add(url_key)
            candidates.append(result_to_candidate(r, region, country, r.get("_query", "")))

    return {
        "scan_type": "country_region",
        "scope": {"country": country, "region": region, "city": None},
        "queries_used": queries_used,
        "next_queries": [],
        "candidates": candidates,
    }


def find_unprocessed(prompt_dir: Path, reports_dir: Path) -> list[Path]:
    """Return prompt files that don't yet have a base report in reports_dir."""
    existing_slugs: set[str] = set()
    for f in reports_dir.glob("*.json"):
        # Strip numeric suffixes like -02, -03 so us-tx-country-region-scan-02 -> us-tx-country-region-scan
        base = re.sub(r"-\d{2}$", "", f.stem)
        existing_slugs.add(base)

    unprocessed: list[Path] = []
    for f in sorted(prompt_dir.glob("[a-z][a-z]-*.md")):
        meta = parse_prompt(f)
        slug = meta.get("run_slug", "")
        if slug and slug not in existing_slugs:
            unprocessed.append(f)
    return unprocessed


def choose_output_path(reports_dir: Path, run_slug: str) -> Path:
    """Return the next available output path (adds -02, -03 suffixes if base exists)."""
    base = reports_dir / f"{run_slug}.json"
    if not base.exists():
        return base
    suffix = 2
    while True:
        candidate = reports_dir / f"{run_slug}-{suffix:02d}.json"
        if not candidate.exists():
            return candidate
        suffix += 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run region discovery prompts via SearXNG and write reports/discovery/*.json"
    )
    parser.add_argument("--regions", nargs="*", metavar="CODE",
                        help="Only run these region codes, e.g. NC WI OR")
    parser.add_argument("--prompts-dir", default=str(PROMPTS_DIR),
                        help="Directory containing state prompt .md files")
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR),
                        help="Output directory for discovery report JSON")
    parser.add_argument("--searxng-url", default=SEARXNG_BASE)
    parser.add_argument("--sleep-seconds", type=float, default=0.5,
                        help="Sleep between SearXNG calls (default: 0.5)")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would run without executing searches")
    args = parser.parse_args()

    prompt_dir = Path(args.prompts_dir)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    unprocessed = find_unprocessed(prompt_dir, reports_dir)

    if args.regions:
        wanted = {r.upper() for r in args.regions}
        unprocessed = [f for f in unprocessed
                       if parse_prompt(f).get("region", "").upper() in wanted]

    if not unprocessed:
        print("All states already have reports. Nothing to do.")
        return 0

    print(f"States to process ({len(unprocessed)}):")
    for f in unprocessed:
        meta = parse_prompt(f)
        print(f"  {meta.get('region'):4s} {meta.get('region_name')} -> {meta.get('run_slug')}")

    if args.dry_run:
        return 0

    print()
    succeeded = 0
    failed = 0

    for i, prompt_path in enumerate(unprocessed, 1):
        meta = parse_prompt(prompt_path)
        region = meta.get("region", "??")
        run_slug = meta.get("run_slug", "unknown")
        print(f"[{i}/{len(unprocessed)}] {region} — {meta.get('region_name')} ({run_slug})")

        try:
            report = run_state(meta, args)
            if report is None:
                failed += 1
                continue

            out_path = choose_output_path(reports_dir, run_slug)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
            print(f"  -> {out_path} ({len(report['candidates'])} candidates)\n")
            succeeded += 1

        except Exception as exc:
            print(f"  ERROR: {exc}\n")
            failed += 1

    print(f"Done: {succeeded} succeeded, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
