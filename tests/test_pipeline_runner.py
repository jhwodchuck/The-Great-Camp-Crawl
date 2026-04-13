from __future__ import annotations

import json
import sys
from pathlib import Path

import responses

import run_discovery_pipeline


@responses.activate
def test_pipeline_runner_completes_mocked_run(tmp_path: Path, fixture_path: Path, monkeypatch) -> None:
    sample_ddg = (fixture_path / "ddg" / "sample_response.json").read_text(encoding="utf-8")
    sample_html = (fixture_path / "html" / "sample_page.html").read_text(encoding="utf-8")

    responses.add(
        responses.GET,
        "https://api.duckduckgo.com/",
        body=sample_ddg,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        "https://ei.jhu.edu/",
        status=302,
        headers={"Location": "https://ei.jhu.edu/programs/residential/"},
    )
    responses.add(
        responses.GET,
        "https://ei.jhu.edu/programs/residential/",
        body=sample_html,
        status=200,
        headers={"Content-Type": "text/html"},
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_discovery_pipeline.py",
            "engineering innovation",
            "--run-id",
            "fixture-run",
            "--country",
            "US",
            "--region",
            "MD",
            "--program-family",
            "college-pre-college",
            "--no-expand",
        ],
    )

    assert run_discovery_pipeline.main() == 0

    summary_path = tmp_path / "reports/discovery/fixture-run_summary.json"
    normalized_path = tmp_path / "reports/discovery/fixture-run_normalized.jsonl"
    followup_path = tmp_path / "reports/discovery/fixture-run_followup_queue.jsonl"
    evidence_index_path = tmp_path / "data/normalized/evidence_index.jsonl"
    capture_manifest_path = tmp_path / "data/raw/discovery-runs/fixture-run/capture_manifest.jsonl"

    assert summary_path.exists()
    assert normalized_path.exists()
    assert followup_path.exists()
    assert evidence_index_path.exists()
    assert capture_manifest_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    normalized_rows = [json.loads(line) for line in normalized_path.read_text(encoding="utf-8").splitlines() if line]
    followup_rows = [json.loads(line) for line in followup_path.read_text(encoding="utf-8").splitlines() if line]

    assert summary["counts"]["raw_results"] == 1
    assert summary["counts"]["normalized_candidates"] == 1
    assert summary["counts"]["followup_items"] >= 1
    assert normalized_rows[0]["country"] == "US"
    assert followup_rows
