from __future__ import annotations

import json
import sys
from pathlib import Path

import run_college_precollege_nationwide


def test_nationwide_runner_builds_region_runs_and_ingest(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    class CompletedProcess:
        def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd: list[str], capture_output: bool, text: bool, check: bool) -> CompletedProcess:
        calls.append(cmd)
        if cmd[1] == "scripts/ingest_discovery_reports.py":
            return CompletedProcess(stdout=json.dumps({"status": "ok"}))
        return CompletedProcess(stdout=json.dumps({"run_id": cmd[cmd.index("--run-id") + 1], "status": "ok"}))

    monkeypatch.setattr(run_college_precollege_nationwide.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_college_precollege_nationwide.py",
            "--country",
            "US",
            "--regions",
            "MD,MA",
            "--run-prefix",
            "wave-1",
            "--ingest-after",
        ],
    )

    assert run_college_precollege_nationwide.main() == 0
    out = capsys.readouterr().out
    summary = json.loads(out.strip().splitlines()[-1])

    assert len(calls) == 3
    assert calls[0][1] == "scripts/run_discovery_pipeline.py"
    assert calls[1][1] == "scripts/run_discovery_pipeline.py"
    assert calls[2][1] == "scripts/ingest_discovery_reports.py"
    assert "--program-family" in calls[0]
    assert "college-pre-college" in calls[0]
    assert summary["failed_runs"] == 0
    assert summary["total_regions"] == 2


def test_nationwide_runner_dry_run_generates_prompt_pack(monkeypatch, tmp_path: Path, capsys) -> None:
    generated_roots: list[Path] = []

    def fake_generate_prompt_pack(path: Path) -> dict[str, int]:
        generated_roots.append(path)
        return {"total": 100}

    monkeypatch.setattr(run_college_precollege_nationwide, "generate_prompt_pack", fake_generate_prompt_pack)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_college_precollege_nationwide.py",
            "--country",
            "CA",
            "--regions",
            "ON",
            "--generate-prompt-pack",
            "--prompt-pack-root",
            str(tmp_path / "pack"),
            "--dry-run",
        ],
    )

    assert run_college_precollege_nationwide.main() == 0
    out = capsys.readouterr().out
    summary = json.loads(out.strip().splitlines()[-1])

    assert generated_roots == [tmp_path / "pack"]
    assert summary["prompt_pack_root"] == str(tmp_path / "pack")
    assert summary["failed_runs"] == 0
    assert summary["runs"][0]["region"] == "ON"
