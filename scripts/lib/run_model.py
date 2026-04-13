from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from lib.common import ensure_parent, slugify, utc_now_iso


def detect_git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def generate_run_id(run_slug: str | None = None, timestamp: str | None = None) -> str:
    if run_slug:
        return slugify(run_slug)
    stamp = (timestamp or utc_now_iso()).replace(":", "").replace("-", "").replace("T", "-").replace("Z", "")
    return slugify(f"discovery-{stamp}")


@dataclass(frozen=True)
class RunLayout:
    run_id: str
    started_at: str
    raw_run_dir: Path
    raw_query_log: Path
    raw_search_results: Path
    raw_capture_manifest: Path
    global_html_dir: Path
    global_text_dir: Path
    global_manifest_dir: Path
    reports_raw: Path
    reports_normalized: Path
    reports_followup: Path
    reports_split_queue: Path
    reports_evidence_index: Path
    reports_summary: Path
    staging_run_dir: Path
    staging_discovered: Path
    staging_followup: Path
    staging_split_queue: Path
    run_metadata: Path

    def ensure_directories(self) -> None:
        for path in [
            self.raw_query_log,
            self.raw_search_results,
            self.raw_capture_manifest,
            self.reports_raw,
            self.reports_normalized,
            self.reports_followup,
            self.reports_split_queue,
            self.reports_evidence_index,
            self.reports_summary,
            self.staging_discovered,
            self.staging_followup,
            self.staging_split_queue,
            self.run_metadata,
        ]:
            ensure_parent(path)
        self.global_html_dir.mkdir(parents=True, exist_ok=True)
        self.global_text_dir.mkdir(parents=True, exist_ok=True)
        self.global_manifest_dir.mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "raw_run_dir": str(self.raw_run_dir),
            "raw_query_log": str(self.raw_query_log),
            "raw_search_results": str(self.raw_search_results),
            "raw_capture_manifest": str(self.raw_capture_manifest),
            "reports_raw": str(self.reports_raw),
            "reports_normalized": str(self.reports_normalized),
            "reports_followup": str(self.reports_followup),
            "reports_split_queue": str(self.reports_split_queue),
            "reports_evidence_index": str(self.reports_evidence_index),
            "reports_summary": str(self.reports_summary),
            "staging_run_dir": str(self.staging_run_dir),
        }


def build_run_layout(run_id: str, started_at: str | None = None, repo_root: Path | None = None) -> RunLayout:
    root = repo_root or Path(".")
    started = started_at or utc_now_iso()
    raw_run_dir = root / "data/raw/discovery-runs" / run_id
    staging_run_dir = root / "data/staging/discovery-runs" / run_id
    return RunLayout(
        run_id=run_id,
        started_at=started,
        raw_run_dir=raw_run_dir,
        raw_query_log=raw_run_dir / "queries.jsonl",
        raw_search_results=raw_run_dir / "search_results.jsonl",
        raw_capture_manifest=raw_run_dir / "capture_manifest.jsonl",
        global_html_dir=root / "data/raw/evidence-pages/html",
        global_text_dir=root / "data/raw/evidence-pages/text",
        global_manifest_dir=root / "data/raw/evidence-pages/manifests",
        reports_raw=root / "reports/discovery" / f"{run_id}_raw.jsonl",
        reports_normalized=root / "reports/discovery" / f"{run_id}_normalized.jsonl",
        reports_followup=root / "reports/discovery" / f"{run_id}_followup_queue.jsonl",
        reports_split_queue=root / "reports/discovery" / f"{run_id}_split_queue.jsonl",
        reports_evidence_index=root / "reports/discovery" / f"{run_id}_evidence_index.jsonl",
        reports_summary=root / "reports/discovery" / f"{run_id}_summary.json",
        staging_run_dir=staging_run_dir,
        staging_discovered=staging_run_dir / "discovered_candidates.jsonl",
        staging_followup=staging_run_dir / "followup_queue.jsonl",
        staging_split_queue=staging_run_dir / "split_queue.jsonl",
        run_metadata=raw_run_dir / "run.json",
    )

