"""Evidence router."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/api/contributions/{contribution_id}/evidence", tags=["evidence"])


def _get_contribution_and_check(contribution_id: int, current_user: models.User, db: Session) -> models.Contribution:
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if current_user.role == models.UserRole.child and c.contributor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your contribution")
    return c


@router.get("/", response_model=List[schemas.EvidenceOut])
def list_evidence(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_contribution_and_check(contribution_id, current_user, db)
    return db.query(models.Evidence).filter(models.Evidence.contribution_id == contribution_id).all()


@router.post("/", response_model=schemas.EvidenceOut, status_code=201)
def add_evidence(
    contribution_id: int,
    payload: schemas.EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = _get_contribution_and_check(contribution_id, current_user, db)
    if c.status not in (
        models.ContributionStatus.draft,
        models.ContributionStatus.changes_requested,
    ):
        raise HTTPException(status_code=409, detail="Evidence can only be added to draft or changes-requested contributions")
    ev = models.Evidence(contribution_id=contribution_id, **payload.model_dump())
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/{evidence_id}", status_code=204)
def delete_evidence(
    contribution_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    c = _get_contribution_and_check(contribution_id, current_user, db)
    if c.status not in (
        models.ContributionStatus.draft,
        models.ContributionStatus.changes_requested,
    ):
        raise HTTPException(status_code=409, detail="Cannot remove evidence from a submitted contribution")
    ev = db.query(models.Evidence).filter(
        models.Evidence.id == evidence_id,
        models.Evidence.contribution_id == contribution_id,
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    db.delete(ev)
    db.commit()
