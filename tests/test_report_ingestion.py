from __future__ import annotations

import json
from pathlib import Path

from lib.report_ingestion import write_ingest_outputs


def test_ingest_discovery_reports_normalizes_arrays_and_updates_staging(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "discovery"
    staging_dir = tmp_path / "data" / "staging"
    reports_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)

    payload = [
        {
            "name": "Test Residential Program",
            "operator_name": "Test University",
            "venue_name": "Test Campus",
            "city": "Austin",
            "region": "TX",
            "country": "US",
            "canonical_url": "https://example.edu/program",
            "program_family": ["college-pre-college", "academic"],
            "camp_types": ["overnight", "residential-academic"],
            "duration_guess": {"label": "two-week", "min_days": 14, "max_days": 14},
            "priority_flags": {"college_precollege": True, "one_week_plus": True},
            "status": "seed_candidate",
        }
    ]
    (reports_dir / "test_seed_dump.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary = write_ingest_outputs(reports_dir, staging_dir)

    assert summary["counts"]["aggregate_candidates"] == 1
    assert (reports_dir / "test_seed_dump_normalized.jsonl").exists()
    assert (reports_dir / "test_seed_dump_followup_queue.jsonl").exists()
    assert (staging_dir / "discovered-candidates.jsonl").exists()
    discovered_rows = (staging_dir / "discovered-candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(discovered_rows) == 1


def test_ingest_discovery_reports_normalizes_raw_jsonl_search_hits(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "discovery"
    staging_dir = tmp_path / "data" / "staging"
    reports_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)

    raw_rows = [
        {
            "query": "test residential program",
            "title": "Test Residential Program",
            "url": "https://example.edu/program",
            "snippet": "Residential two-week summer program on campus.",
            "source": "duckduckgo_lite_html",
            "provider": "lite_html",
        }
    ]
    with (reports_dir / "test_probe.jsonl").open("w", encoding="utf-8") as handle:
        for row in raw_rows:
            handle.write(json.dumps(row) + "\n")

    summary = write_ingest_outputs(reports_dir, staging_dir)

    assert summary["counts"]["aggregate_candidates"] == 1
    assert (reports_dir / "test_probe_normalized.jsonl").exists()
