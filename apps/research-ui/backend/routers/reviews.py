"""Reviews router (parent only)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from auth import require_parent
from database import get_db

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

_STATUS_AFTER_ACTION = {
    models.ReviewAction.approve: models.ContributionStatus.approved,
    models.ReviewAction.reject: models.ContributionStatus.rejected,
    models.ReviewAction.request_changes: models.ContributionStatus.changes_requested,
}


@router.get("/queue", response_model=List[schemas.ContributionOut])
def review_queue(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_parent),
):
    """Return all contributions pending review (submitted or under_review)."""
    return (
        db.query(models.Contribution)
        .filter(
            models.Contribution.status.in_([
                models.ContributionStatus.submitted,
                models.ContributionStatus.under_review,
            ])
        )
        .order_by(models.Contribution.submitted_at.asc())
        .all()
    )


@router.post("/{contribution_id}", response_model=schemas.ReviewOut, status_code=201)
def post_review(
    contribution_id: int,
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_parent),
):
    c = db.query(models.Contribution).filter(models.Contribution.id == contribution_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if c.status not in (
        models.ContributionStatus.submitted,
        models.ContributionStatus.under_review,
    ):
        raise HTTPException(status_code=409, detail="Contribution is not in a reviewable state")

    review = models.Review(
        contribution_id=contribution_id,
        reviewer_id=current_user.id,
        action=payload.action,
        notes=payload.notes,
    )
    db.add(review)
    c.status = _STATUS_AFTER_ACTION[payload.action]
    db.commit()
    db.refresh(review)
    return review


@router.get("/{contribution_id}", response_model=List[schemas.ReviewOut])
def get_reviews(
    contribution_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_parent),
):
    return (
        db.query(models.Review)
        .filter(models.Review.contribution_id == contribution_id)
        .order_by(models.Review.created_at.desc())
        .all()
    )
