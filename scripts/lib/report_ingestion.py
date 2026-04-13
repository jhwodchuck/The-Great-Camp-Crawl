from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.candidate_normalization import normalize_candidate_rows
from lib.common import read_jsonl, utc_now_iso, write_jsonl
from lib.followup_queue import generate_followup_queue
from lib.split_queue import generate_split_queue


SKIP_REPORT_SUFFIXES = (
    "_summary.json",
    "_README.md",
    "_queries.jsonl",
    "_queries_probe.jsonl",
    "_raw.jsonl",
    "_raw_probe.jsonl",
    "_evidence_index.jsonl",
    "_followup_queue.jsonl",
    "_split_queue.jsonl",
    "_split_stubs.jsonl",
)


@dataclass(frozen=True)
class CandidateArrayReport:
    path: Path
    stem: str


@dataclass(frozen=True)
class RawJsonlReport:
    path: Path
    stem: str


def discover_candidate_array_reports(reports_dir: Path) -> list[CandidateArrayReport]:
    reports: list[CandidateArrayReport] = []
    for path in sorted(reports_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".json":
            continue
        if path.name.endswith("_summary.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
            reports.append(CandidateArrayReport(path=path, stem=path.stem))
    return reports


def discover_raw_jsonl_reports(reports_dir: Path) -> list[RawJsonlReport]:
    reports: list[RawJsonlReport] = []
    for path in sorted(reports_dir.glob("*.jsonl")):
        if not path.is_file():
            continue
        if path.name.endswith("_normalized.jsonl"):
            continue
        if path.name.endswith(SKIP_REPORT_SUFFIXES):
            continue
        rows = read_jsonl(path)
        if not rows:
            continue
        first = rows[0]
        if not isinstance(first, dict):
            continue
        if "candidate_id" in first:
            continue
        if not any(key in first for key in ["url", "title", "query", "source", "provider"]):
            continue
        reports.append(RawJsonlReport(path=path, stem=path.stem))
    return reports


def _write_companion_outputs(stem: str, reports_dir: Path, normalized_rows: list[dict[str, Any]]) -> dict[str, Path]:
    normalized_path = reports_dir / f"{stem}_normalized.jsonl"
    followup_path = reports_dir / f"{stem}_followup_queue.jsonl"
    split_queue_path = reports_dir / f"{stem}_split_queue.jsonl"
    split_stubs_path = reports_dir / f"{stem}_split_stubs.jsonl"

    write_jsonl(normalized_path, normalized_rows)
    write_jsonl(followup_path, generate_followup_queue(normalized_rows))
    split_tasks, split_stubs = generate_split_queue(normalized_rows)
    write_jsonl(split_queue_path, split_tasks)
    write_jsonl(split_stubs_path, split_stubs)

    return {
        "normalized": normalized_path,
        "followup": followup_path,
        "split_queue": split_queue_path,
        "split_stubs": split_stubs_path,
    }


def ingest_candidate_array_reports(reports_dir: Path) -> list[dict[str, Any]]:
    ingested: list[dict[str, Any]] = []
    for report in discover_candidate_array_reports(reports_dir):
        payload = json.loads(report.path.read_text(encoding="utf-8"))
        normalized_rows = normalize_candidate_rows(payload)
        outputs = _write_companion_outputs(report.stem, reports_dir, normalized_rows)
        ingested.append(
            {
                "source_report": str(report.path),
                "records": len(payload),
                "outputs": {key: str(value) for key, value in outputs.items()},
            }
        )
    return ingested


def ingest_raw_jsonl_reports(reports_dir: Path) -> list[dict[str, Any]]:
    ingested: list[dict[str, Any]] = []
    for report in discover_raw_jsonl_reports(reports_dir):
        normalized_path = reports_dir / f"{report.stem}_normalized.jsonl"
        if normalized_path.exists():
            continue
        rows = read_jsonl(report.path)
        normalized_rows = normalize_candidate_rows(rows)
        outputs = _write_companion_outputs(report.stem, reports_dir, normalized_rows)
        ingested.append(
            {
                "source_report": str(report.path),
                "records": len(rows),
                "outputs": {key: str(value) for key, value in outputs.items()},
            }
        )
    return ingested


def discover_normalized_reports(reports_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in reports_dir.glob("*_normalized.jsonl")
        if path.is_file() and not path.name.endswith("_summary.jsonl")
    )


def aggregate_normalized_reports(reports_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    merged: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for path in discover_normalized_reports(reports_dir):
        rows = read_jsonl(path)
        for row in rows:
            candidate_id = row.get("candidate_id")
            if not candidate_id:
                continue
            tagged_row = {**row, "source_reports": [path.name]}
            existing = merged.get(candidate_id)
            if existing is None:
                merged[candidate_id] = tagged_row
                continue
            existing_sources = set(existing.get("source_reports", []))
            existing_sources.add(path.name)
            existing["source_reports"] = sorted(existing_sources)
            if existing.get("canonical_url") != row.get("canonical_url") or existing.get("name") != row.get("name"):
                duplicates.append(
                    {
                        "candidate_id": candidate_id,
                        "source_report": path.name,
                        "canonical_url": row.get("canonical_url"),
                        "name": row.get("name"),
                    }
                )
    aggregate_rows = sorted(merged.values(), key=lambda row: row["candidate_id"])
    return aggregate_rows, duplicates


def write_ingest_outputs(reports_dir: Path, staging_dir: Path) -> dict[str, Any]:
    ingested_reports = [
        *ingest_candidate_array_reports(reports_dir),
        *ingest_raw_jsonl_reports(reports_dir),
    ]
    aggregate_rows, duplicate_candidates = aggregate_normalized_reports(reports_dir)
    followup_rows = generate_followup_queue(aggregate_rows)
    split_rows, split_stubs = generate_split_queue(aggregate_rows)

    discovered_path = staging_dir / "discovered-candidates.jsonl"
    followup_path = staging_dir / "discovery-followup-queue.jsonl"
    split_queue_path = staging_dir / "discovery-split-queue.jsonl"
    split_stubs_path = staging_dir / "discovery-split-stubs.jsonl"
    summary_path = staging_dir / "discovery-ingest-summary.json"

    write_jsonl(discovered_path, aggregate_rows)
    write_jsonl(followup_path, followup_rows)
    write_jsonl(split_queue_path, split_rows)
    write_jsonl(split_stubs_path, split_stubs)

    summary = {
        "generated_at": utc_now_iso(),
        "reports_ingested": ingested_reports,
        "normalized_reports_used": [path.name for path in discover_normalized_reports(reports_dir)],
        "counts": {
            "aggregate_candidates": len(aggregate_rows),
            "aggregate_followups": len(followup_rows),
            "aggregate_split_tasks": len(split_rows),
            "duplicate_candidate_ids": len(duplicate_candidates),
        },
        "duplicates": duplicate_candidates,
        "outputs": {
            "discovered_candidates": str(discovered_path),
            "followup_queue": str(followup_path),
            "split_queue": str(split_queue_path),
            "split_stubs": str(split_stubs_path),
            "summary": str(summary_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary
