from __future__ import annotations

import json
from pathlib import Path

from lib.report_ingestion import discover_candidate_jsonl_reports, discover_raw_jsonl_reports, write_ingest_outputs


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


def test_ingest_discovery_reports_normalizes_candidate_jsonl_reports(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "discovery"
    staging_dir = tmp_path / "data" / "staging"
    reports_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)

    candidate_rows = [
        {
            "candidate_id": "wave1-jhu-ei",
            "record_basis": "venue_candidate",
            "name": "Johns Hopkins Engineering Innovation",
            "operator_name": "Johns Hopkins University",
            "venue_name": "Homewood Campus",
            "city": "Baltimore",
            "region": "MD",
            "country": "United States",
            "canonical_url": "https://ei.jhu.edu/",
            "source_language": "en",
            "program_family": ["college-pre-college", "academic", "stem"],
            "camp_types": ["residential-academic", "residential"],
            "duration_guess": {"label": "4 weeks", "min_days": 28, "max_days": 28},
            "overnight_evidence_snippet": "Residential: Live on campus and experience college life firsthand.",
            "recent_activity_evidence_snippet": "Current site references Summer 2026.",
            "verification_state": "partially_verified_from_current_source",
            "priority_flags": {"college_precollege": True, "one_week_plus": True},
            "validation_needs": ["pricing"],
            "status": "discovered",
        }
    ]
    with (reports_dir / "wave1.jsonl").open("w", encoding="utf-8") as handle:
        for row in candidate_rows:
            handle.write(json.dumps(row) + "\n")

    summary = write_ingest_outputs(reports_dir, staging_dir)

    assert summary["counts"]["aggregate_candidates"] == 1
    assert (reports_dir / "wave1_normalized.jsonl").exists()
    assert any(report["source_report"].endswith("wave1.jsonl") for report in summary["reports_ingested"])


def test_ingest_prefers_richer_duplicate_candidate_rows(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "discovery"
    staging_dir = tmp_path / "data" / "staging"
    reports_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)

    poorer = {
        "candidate_id": "cand-us-ca-nevada-city-camp-augusta-pending-venue-campaugusta-org",
        "record_basis": "venue_candidate",
        "name": "Camp Augusta",
        "venue_name": "venue to be confirmed",
        "city": "Nevada City",
        "region": "CA",
        "country": "US",
        "canonical_url": "https://campaugusta.org/",
        "validation_needs": ["confirm_overnight", "confirm_recent_activity"],
    }
    richer = {
        "candidate_id": "cand-us-ca-nevada-city-camp-augusta-pending-venue-campaugusta-org",
        "record_basis": "venue_candidate",
        "name": "Camp Augusta",
        "venue_name": "Camp Augusta",
        "city": "Nevada City",
        "region": "CA",
        "country": "US",
        "canonical_url": "https://campaugusta.org/",
        "operator_name": "Camp Augusta",
        "overnight_evidence_snippet": "Co-ed overnight camp in the Sierra Nevada mountains.",
        "recent_activity_evidence_snippet": "Summer 2026 registration is open.",
        "validation_needs": ["contact"],
    }
    (reports_dir / "a_poorer.jsonl").write_text(json.dumps(poorer) + "\n", encoding="utf-8")
    (reports_dir / "z_richer.jsonl").write_text(json.dumps(richer) + "\n", encoding="utf-8")

    write_ingest_outputs(reports_dir, staging_dir)

    rows = (staging_dir / "discovered-candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    merged = json.loads(rows[0])
    assert merged["venue_name"] == "Camp Augusta"
    assert merged["operator_name"] == "Camp Augusta"
    assert merged["recent_activity_evidence_snippet"] == "Summer 2026 registration is open."


def test_discover_candidate_jsonl_reports_skips_helper_match_files(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "discovery"
    reports_dir.mkdir(parents=True)

    helper_row = {
        "candidate_id": "cand-1",
        "candidate_name": "Camp Augusta",
        "candidate_host": "campaugusta.org",
        "matched_reason": ["unknown_venue"],
        "search_query": "overnight residential summer camp US CA",
    }
    (reports_dir / "pending_matches.jsonl").write_text(json.dumps(helper_row) + "\n", encoding="utf-8")

    reports = discover_candidate_jsonl_reports(reports_dir)

    assert reports == []


def test_discover_raw_jsonl_reports_skips_query_map_helpers(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "discovery"
    reports_dir.mkdir(parents=True)

    helper_row = {
        "query": "\"Camp Augusta\" Nevada City",
        "candidate_ids": ["cand-1"],
        "candidate_names": ["Camp Augusta"],
        "hosts": ["campaugusta.org"],
    }
    (reports_dir / "pending_query_map.jsonl").write_text(json.dumps(helper_row) + "\n", encoding="utf-8")

    reports = discover_raw_jsonl_reports(reports_dir)

    assert reports == []
