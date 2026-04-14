from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lib.common import ensure_parent, read_jsonl, utc_now_iso, write_jsonl
from lib.report_ingestion import PLACEHOLDER_CITIES, PLACEHOLDER_VENUES, _candidate_preference_key, discover_normalized_reports


def load_candidate_ids(matches_path: Path) -> list[str]:
    ids: list[str] = []
    for row in read_jsonl(matches_path):
        candidate_id = str(row.get("candidate_id") or "")
        if candidate_id and candidate_id not in ids:
            ids.append(candidate_id)
    return ids


def load_best_rows(reports_dir: Path) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for path in discover_normalized_reports(reports_dir):
        for row in read_jsonl(path):
            candidate_id = row.get("candidate_id")
            if not candidate_id:
                continue
            current = best.get(candidate_id)
            if current is None or _candidate_preference_key(row) < _candidate_preference_key(current):
                best[candidate_id] = row
    return best


def is_placeholder(value: Any, placeholders: set[str]) -> bool:
    return str(value or "").strip().lower() in placeholders


def resolve_row(row: dict[str, Any]) -> dict[str, Any]:
    notes = list(row.get("notes") or [])
    resolution_note = "Venue name resolved to the branded single-site camp/program name using official-site capture and SearXNG host match."
    if resolution_note not in notes:
        notes.append(resolution_note)
    raw_source = row.get("raw_discovery_source")
    if not isinstance(raw_source, dict):
        raw_source = {}
    resolved = {
        **row,
        "venue_name": row.get("name"),
        "record_basis": "venue_candidate",
        "notes": notes,
        "raw_discovery_source": {
            **raw_source,
            "venue_name": row.get("name"),
            "record_basis": "venue_candidate",
            "resolution_note": resolution_note,
        },
    }
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a resolved candidate report for pending dossiers with strong host-matched evidence"
    )
    parser.add_argument("--matches", required=True, help="JSONL of candidate matches used to select pending dossiers")
    parser.add_argument("--reports-dir", default="reports/discovery")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", required=True)
    args = parser.parse_args()

    matches_path = Path(args.matches)
    reports_dir = Path(args.reports_dir)
    candidate_ids = load_candidate_ids(matches_path)
    best_rows = load_best_rows(reports_dir)

    resolved_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        row = best_rows.get(candidate_id)
        if row is None:
            skipped.append({"candidate_id": candidate_id, "reason": "missing_candidate"})
            continue
        if is_placeholder(row.get("city"), PLACEHOLDER_CITIES):
            skipped.append({"candidate_id": candidate_id, "reason": "unknown_city"})
            continue
        if not is_placeholder(row.get("venue_name"), PLACEHOLDER_VENUES):
            skipped.append({"candidate_id": candidate_id, "reason": "already_has_venue"})
            continue
        if str(row.get("record_basis") or "") == "multi_venue_candidate":
            skipped.append({"candidate_id": candidate_id, "reason": "multi_venue_candidate"})
            continue
        resolved_rows.append(resolve_row(row))

    output_path = Path(args.output)
    summary_path = Path(args.summary_output)
    write_jsonl(output_path, resolved_rows)
    summary = {
        "generated_at": utc_now_iso(),
        "matches": str(matches_path),
        "reports_dir": str(reports_dir),
        "counts": {
            "selected_candidate_ids": len(candidate_ids),
            "resolved_rows": len(resolved_rows),
            "skipped": len(skipped),
        },
        "skipped": skipped,
        "outputs": {
            "resolved_report": str(output_path),
            "summary": str(summary_path),
        },
    }
    ensure_parent(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
