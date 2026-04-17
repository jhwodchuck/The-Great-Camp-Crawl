"""Export / promote approved contributions to repo-compatible staging artifacts."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from auth import require_parent
from database import get_db

router = APIRouter(prefix="/api/export", tags=["export"])

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRIBUTIONS_DIR = REPO_ROOT / "data" / "staging" / "contributions"
REVIEW_QUEUE_DIR = REPO_ROOT / "data" / "staging" / "review-queue"


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text)


def _contribution_to_candidate(c: models.Contribution, evidence: list, answers: list) -> dict:
    answer_map = {a.question_key: a.answer_text for a in answers}
    return {
        "candidate_id": f"ui-contrib-{c.id}-{_slugify(c.camp_name)}",
        "name": c.camp_name,
        "website_url": c.website_url,
        "country": c.country or "US",
        "region": c.region,
        "city": c.city,
        "venue_name": c.venue_name,
        "overnight_confirmed": c.overnight_confirmed,
        "notes": c.notes,
        "status": "contributed",
        "record_basis": "child_contribution",
        "source": "research_ui",
        "contributor_notes": {
            "overnight_evidence": answer_map.get("overnight_evidence"),
            "recent_activity": answer_map.get("recent_activity"),
            "age_range": answer_map.get("age_range"),
            "program_type": answer_map.get("program_type"),
            "cost_info": answer_map.get("cost_info"),
            "why_interesting": answer_map.get("why_interesting"),
        },
        "evidence": [
            {"url": ev.url, "snippet": ev.snippet, "capture_notes": ev.capture_notes}
            for ev in evidence
        ],
        "provenance": {
            "contribution_id": c.id,
            "contributor_id": c.contributor_id,
            "mission_id": c.mission_id,
            "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.post("/{contribution_id}", response_model=schemas.ExportResult)
def promote_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_parent),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if c.status != models.ContributionStatus.approved:
        raise HTTPException(status_code=409, detail="Only approved contributions can be promoted")

    evidence = db.query(models.Evidence).filter(models.Evidence.contribution_id == contribution_id).all()
    answers = db.query(models.Answer).filter(models.Answer.contribution_id == contribution_id).all()

    candidate = _contribution_to_candidate(c, evidence, answers)
    slug = _slugify(c.camp_name)
    filename = f"contrib-{c.id}-{slug}.json"
    out_path = CONTRIBUTIONS_DIR / filename
    CONTRIBUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")

    return schemas.ExportResult(
        contribution_id=c.id,
        artifact_path=str(out_path.relative_to(REPO_ROOT)),
        message=f"Contribution promoted to {filename}",
    )


@router.get("/preview/{contribution_id}")
def preview_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_parent),
):
    """Preview the candidate JSON without writing to disk."""
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    evidence = db.query(models.Evidence).filter(models.Evidence.contribution_id == contribution_id).all()
    answers = db.query(models.Answer).filter(models.Answer.contribution_id == contribution_id).all()
    return _contribution_to_candidate(c, evidence, answers)
