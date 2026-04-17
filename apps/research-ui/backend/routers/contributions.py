"""Contributions router."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user, require_parent
from database import get_db

router = APIRouter(prefix="/api/contributions", tags=["contributions"])


def _owned_or_parent(contribution: models.Contribution, current_user: models.User) -> None:
    if current_user.role == models.UserRole.parent:
        return
    if contribution.contributor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your contribution")


@router.post("/", response_model=schemas.ContributionOut, status_code=201)
def create_contribution(
    payload: schemas.ContributionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    mission = db.query(models.Mission).filter(models.Mission.id == payload.mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    contribution = models.Contribution(**payload.model_dump(), contributor_id=current_user.id)
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return contribution


@router.get("/", response_model=List[schemas.ContributionOut])
def list_contributions(
    mission_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Contribution)
    if current_user.role == models.UserRole.child:
        q = q.filter(models.Contribution.contributor_id == current_user.id)
    if mission_id:
        q = q.filter(models.Contribution.mission_id == mission_id)
    if status:
        q = q.filter(models.Contribution.status == status)
    return q.order_by(models.Contribution.updated_at.desc()).all()


@router.get("/{contribution_id}", response_model=schemas.ContributionOut)
def get_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    _owned_or_parent(c, current_user)
    return c


@router.patch("/{contribution_id}", response_model=schemas.ContributionOut)
def update_contribution(
    contribution_id: int,
    payload: schemas.ContributionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    _owned_or_parent(c, current_user)
    if c.status not in (
        models.ContributionStatus.draft,
        models.ContributionStatus.changes_requested,
    ):
        raise HTTPException(status_code=409, detail="Only draft or changes-requested contributions can be edited")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


@router.post("/{contribution_id}/submit", response_model=schemas.ContributionOut)
def submit_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    _owned_or_parent(c, current_user)
    if c.status not in (
        models.ContributionStatus.draft,
        models.ContributionStatus.changes_requested,
    ):
        raise HTTPException(status_code=409, detail="Only draft or changes-requested contributions can be submitted")
    c.status = models.ContributionStatus.submitted
    c.submitted_at = datetime.now(timezone.utc)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{contribution_id}", status_code=204)
def delete_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    _owned_or_parent(c, current_user)
    if c.status not in (models.ContributionStatus.draft, models.ContributionStatus.changes_requested):
        raise HTTPException(status_code=409, detail="Cannot delete a submitted contribution")
    db.delete(c)
    db.commit()
