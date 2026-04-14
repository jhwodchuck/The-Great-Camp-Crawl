from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from lib.college_precollege_prompt_pack import COUNTRY_COLLEGE_SPECS, generate_prompt_pack
from lib.common import slugify


DEFAULT_PROMPT_PACK_ROOT = "prompts/discovery/02-college-precollege-scanner-pack"


def _default_run_prefix(country: str) -> str:
    if country == "ALL":
        return "north-america-college-precollege"
    return f"{country.lower()}-college-precollege-nationwide"


def _parse_regions(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip().upper() for part in value.split(",") if part.strip()}


def _selected_specs(country: str, regions: set[str]) -> list[object]:
    country_codes = list(COUNTRY_COLLEGE_SPECS) if country == "ALL" else [country]
    specs = []
    for country_code in country_codes:
        for spec in COUNTRY_COLLEGE_SPECS[country_code]:
            if regions and spec.region_code.upper() not in regions:
                continue
            specs.append(spec)
    return specs


def _build_run_id(run_prefix: str, country_code: str, region_code: str) -> str:
    return slugify(f"{run_prefix}-{country_code.lower()}-{region_code.lower()}-college-precollege")


def _build_pipeline_cmd(args: argparse.Namespace, spec: object, run_id: str) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/run_discovery_pipeline.py",
        *spec.query_angles,
        "--run-id",
        run_id,
        "--country",
        spec.country_code,
        "--region",
        spec.region_code,
        "--program-family",
        "college-pre-college",
        "--search-providers",
        args.search_providers,
        "--timeout",
        str(args.timeout),
        "--retries",
        str(args.retries),
        "--backoff-seconds",
        str(args.backoff_seconds),
        "--sleep-seconds",
        str(args.sleep_seconds),
    ]
    if args.limit is not None:
        cmd.extend(["--limit", str(args.limit)])
    if args.allow_host_file:
        cmd.extend(["--allow-host-file", args.allow_host_file])
    if args.deny_host_file:
        cmd.extend(["--deny-host-file", args.deny_host_file])
    if args.no_expand:
        cmd.append("--no-expand")
    if args.no_skip_existing_captures:
        cmd.append("--no-skip-existing-captures")
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run college pre-college discovery nationwide, region by region, "
            "through the deterministic discovery pipeline"
        )
    )
    parser.add_argument("--country", choices=["US", "CA", "MX", "ALL"], default="US")
    parser.add_argument(
        "--regions",
        help="Optional comma-separated region codes to restrict the run, e.g. MD,MA,CA",
    )
    parser.add_argument("--run-prefix", help="Prefix used to build per-region run ids")
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
    parser.add_argument("--generate-prompt-pack", action="store_true")
    parser.add_argument("--prompt-pack-root", default=DEFAULT_PROMPT_PACK_ROOT)
    parser.add_argument("--ingest-after", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    selected_regions = _parse_regions(args.regions)
    specs = _selected_specs(args.country, selected_regions)
    if not specs:
        parser.error("no region specs matched the requested country/regions")

    run_prefix = slugify(args.run_prefix or _default_run_prefix(args.country))
    summary: dict[str, object] = {
        "country": args.country,
        "regions_requested": sorted(selected_regions),
        "run_prefix": run_prefix,
        "total_regions": len(specs),
        "prompt_pack_root": None,
        "runs": [],
    }

    if args.generate_prompt_pack:
        prompt_pack_root = Path(args.prompt_pack_root)
        generate_prompt_pack(prompt_pack_root)
        summary["prompt_pack_root"] = str(prompt_pack_root)

    for index, spec in enumerate(specs, start=1):
        run_id = _build_run_id(run_prefix, spec.country_code, spec.region_code)
        cmd = _build_pipeline_cmd(args, spec, run_id)
        run_summary: dict[str, object] = {
            "country": spec.country_code,
            "region": spec.region_code,
            "region_name": spec.region_name,
            "run_id": run_id,
            "query_count": len(spec.query_angles),
            "queries": list(spec.query_angles),
            "command": cmd,
        }
        if args.dry_run:
            summary["runs"].append(run_summary)
            continue

        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        run_summary["returncode"] = completed.returncode
        if completed.stdout.strip():
            try:
                run_summary["pipeline_summary"] = json.loads(completed.stdout)
            except json.JSONDecodeError:
                run_summary["stdout"] = completed.stdout.strip()
        if completed.stderr.strip():
            run_summary["stderr"] = completed.stderr.strip()
        summary["runs"].append(run_summary)

        print(json.dumps(run_summary, ensure_ascii=False))
        if args.pause_between_runs and index < len(specs):
            time.sleep(args.pause_between_runs)

    if args.ingest_after and not args.dry_run:
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
        summary["ingest_after"] = ingest_summary
        print(json.dumps(ingest_summary, ensure_ascii=False))

    failures = sum(1 for run in summary["runs"] if run.get("returncode", 0) != 0)
    summary["failed_runs"] = failures
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
