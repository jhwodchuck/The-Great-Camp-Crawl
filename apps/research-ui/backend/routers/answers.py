"""Answers (guided questions) router."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/api/contributions/{contribution_id}/answers", tags=["answers"])

# Guided question definitions shown to the child contributor
GUIDED_QUESTIONS: List[dict] = [
    {"key": "overnight_evidence", "label": "How do you know kids sleep there overnight?", "hint": "Copy a sentence from the website that proves kids stay the night."},
    {"key": "recent_activity", "label": "Is this camp still running?", "hint": "Find a date (like '2024' or 'Summer 2025') on the website and paste it here."},
    {"key": "age_range", "label": "What ages or grades is this camp for?", "hint": "E.g. 'Ages 8-16' or 'Grades 3-10'"},
    {"key": "program_type", "label": "What kind of camp is it?", "hint": "E.g. 'arts camp', 'science camp', 'sports camp', 'music camp'"},
    {"key": "cost_info", "label": "How much does it cost (if shown)?", "hint": "Copy the price or write 'not shown' if you can't find it."},
    {"key": "why_interesting", "label": "Why does this camp seem cool or interesting?", "hint": "Write in your own words what makes this camp special."},
]


@router.get("/questions")
def get_questions(_: models.User = Depends(get_current_user)):
    return GUIDED_QUESTIONS


@router.get("/", response_model=List[schemas.AnswerOut])
def list_answers(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if current_user.role == models.UserRole.child and c.contributor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your contribution")
    return db.query(models.Answer).filter(models.Answer.contribution_id == contribution_id).all()


@router.put("/", response_model=List[schemas.AnswerOut])
def upsert_answers(
    contribution_id: int,
    payload: List[schemas.AnswerUpsert],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if current_user.role == models.UserRole.child and c.contributor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your contribution")
    if c.status not in (
        models.ContributionStatus.draft,
        models.ContributionStatus.changes_requested,
    ):
        raise HTTPException(status_code=409, detail="Answers can only be edited in draft or changes-requested state")

    for item in payload:
        existing = db.query(models.Answer).filter(
            models.Answer.contribution_id == contribution_id,
            models.Answer.question_key == item.question_key,
        ).first()
        if existing:
            existing.answer_text = item.answer_text
        else:
            db.add(models.Answer(contribution_id=contribution_id, **item.model_dump()))
    db.commit()
    return db.query(models.Answer).filter(models.Answer.contribution_id == contribution_id).all()
