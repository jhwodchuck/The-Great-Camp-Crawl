from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lib.capture_pipeline import capture_urls
from lib.common import load_line_file, read_jsonl, utc_now_iso, write_jsonl
from lib.evidence_index import discover_capture_paths, index_capture_paths
from lib.url_utils import extract_host, normalize_url


DEFAULT_CANDIDATES = Path("data/staging/discovered-candidates.jsonl")
DEFAULT_EVIDENCE_INDEX = Path("data/normalized/evidence_index.jsonl")
DEFAULT_TEXT_DIR = Path("data/raw/evidence-pages/text")
DEFAULT_HTML_DIR = Path("data/raw/evidence-pages/html")
DEFAULT_MANIFEST_DIR = Path("data/raw/evidence-pages/manifests")
DEFAULT_SELECTION_DIR = Path("data/staging")
DEFAULT_DENY_HOSTS = Path("data/seed-queries/common-deny-hosts.txt")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _candidate_url(row: dict[str, Any]) -> str:
    raw = _as_dict(row.get("raw_discovery_source"))
    for value in (
        row.get("canonical_url"),
        row.get("website_url"),
        raw.get("canonical_url"),
        raw.get("website_url"),
    ):
        if not value:
            continue
        return normalize_url(str(value))
    return ""


def _covered_urls(rows: list[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for row in rows:
        for key in ("source_url", "resolved_url"):
            value = normalize_url(str(row.get(key) or ""))
            if value:
                covered.add(value)
    return covered


def _matches_filter(value: str | None, allowed: list[str]) -> bool:
    if not allowed:
        return True
    normalized = (value or "").strip().lower()
    return normalized in {item.strip().lower() for item in allowed}


def _is_multi_venue(row: dict[str, Any]) -> bool:
    if row.get("record_basis") == "multi_venue_candidate":
        return True
    flags = _as_dict(row.get("priority_flags"))
    return bool(flags.get("multi_venue"))


def _host_denied(host: str, deny_hosts: set[str]) -> bool:
    if not host:
        return True
    return any(host == denied or host.endswith(f".{denied}") for denied in deny_hosts)


def _sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    basis_rank = {
        "venue_candidate": 0,
        "venue_candidate_pending_confirmation": 1,
        "multi_venue_candidate": 2,
    }.get(str(row.get("record_basis") or ""), 9)
    activity_rank = 0 if row.get("activity_status_guess") == "active_recent" else 1
    one_week_rank = 0 if _as_dict(row.get("priority_flags")).get("one_week_plus") else 1
    return (
        activity_rank,
        basis_rank,
        one_week_rank,
        str(row.get("country") or ""),
        str(row.get("region") or ""),
        str(row.get("candidate_id") or ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture HTML/Markdown evidence for staged discovery candidates")
    parser.add_argument("--run-id", required=True, help="Stable run id used for manifest and selection outputs")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--evidence-index", default=str(DEFAULT_EVIDENCE_INDEX))
    parser.add_argument("--capture-dir", default=str(DEFAULT_TEXT_DIR))
    parser.add_argument("--html-dir", default=str(DEFAULT_HTML_DIR))
    parser.add_argument("--manifest")
    parser.add_argument("--selection-output")
    parser.add_argument("--record-basis", action="append", default=[])
    parser.add_argument("--activity-status", action="append", default=[])
    parser.add_argument("--country", action="append", default=[])
    parser.add_argument("--region", action="append", default=[])
    parser.add_argument("--exclude-multi-venue", action="store_true")
    parser.add_argument("--require-one-week-plus", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--deny-host-file", default=str(DEFAULT_DENY_HOSTS))
    parser.add_argument("--deny-host", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--refresh-evidence-index", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST_DIR / f"{args.run_id}.jsonl"
    selection_output = (
        Path(args.selection_output)
        if args.selection_output
        else DEFAULT_SELECTION_DIR / f"{args.run_id}_capture_selection.jsonl"
    )

    candidates = read_jsonl(Path(args.candidates))
    covered_urls = _covered_urls(read_jsonl(Path(args.evidence_index)))
    deny_hosts = {host.strip().lower() for host in load_line_file(Path(args.deny_host_file)) if host.strip()}
    deny_hosts.update(host.strip().lower() for host in args.deny_host if host.strip())

    selected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for row in sorted(candidates, key=_sort_key):
        capture_url = _candidate_url(row)
        if not capture_url:
            continue
        host = extract_host(capture_url).lower()
        if _host_denied(host, deny_hosts):
            continue
        if capture_url in covered_urls or capture_url in seen_urls:
            continue
        if not _matches_filter(str(row.get("record_basis") or ""), args.record_basis):
            continue
        if not _matches_filter(str(row.get("activity_status_guess") or ""), args.activity_status):
            continue
        if not _matches_filter(str(row.get("country") or ""), args.country):
            continue
        if not _matches_filter(str(row.get("region") or ""), args.region):
            continue
        if args.exclude_multi_venue and _is_multi_venue(row):
            continue
        if args.require_one_week_plus and not _as_dict(row.get("priority_flags")).get("one_week_plus"):
            continue

        selected.append(
            {
                **row,
                "capture_url": capture_url,
                "capture_host": host,
                "capture_selected_at": utc_now_iso(),
                "capture_run_id": args.run_id,
            }
        )
        seen_urls.add(capture_url)

        if args.limit and len(selected) >= args.limit:
            break

    write_jsonl(selection_output, selected)

    summary: dict[str, Any] = {
        "run_id": args.run_id,
        "selection_output": str(selection_output),
        "manifest_path": str(manifest_path),
        "counts": {
            "candidates_read": len(candidates),
            "selected": len(selected),
            "already_covered": len(covered_urls),
            "deny_hosts": len(deny_hosts),
        },
    }

    if args.dry_run or not selected:
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    capture_result = capture_urls(
        urls=[row["capture_url"] for row in selected],
        text_dir=Path(args.capture_dir),
        html_dir=Path(args.html_dir),
        manifest_path=manifest_path,
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        sleep_seconds=args.sleep_seconds,
        skip_existing=not args.no_skip_existing,
    )
    summary["capture_counts"] = capture_result["counts"]

    if args.refresh_evidence_index:
        refreshed_rows = index_capture_paths(
            discover_capture_paths(Path(args.capture_dir)),
            output_path=Path(args.evidence_index),
        )
        summary["evidence_index_rows"] = len(refreshed_rows)

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
