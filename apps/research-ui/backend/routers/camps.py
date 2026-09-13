"""Camp catalog API — public read-only access to all imported camps."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import models
from auth import get_current_user, get_current_user_optional
from database import get_db
from models import Camp, User
from schemas import CampEnrichmentUpdate, CampListOut, CampModerationUpdate, CampOut, CampPlanMembership, CampStatsOut

router = APIRouter(prefix="/api/camps", tags=["camps"])
_SHOW_STATUSES = ("draft", "candidate")


@router.get("", response_model=CampListOut)
def list_camps(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    country: Optional[str] = None,
    region: Optional[str] = None,
    program_family: Optional[str] = None,
    camp_type: Optional[str] = None,
    ages_min: Optional[int] = None,
    ages_max: Optional[int] = None,
    grades_min: Optional[int] = None,
    grades_max: Optional[int] = None,
    price_max: Optional[float] = None,
    overnight: Optional[bool] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Paginated list of camps with filtering."""
    # Only surface curated records (draft + candidate); exclude raw crawl candidates
    # and any record flagged as excluded.
    query = (
        db.query(Camp)
        .filter(Camp.is_excluded.is_not(True))
        .filter(Camp.draft_status.in_(_SHOW_STATUSES))
    )

    if country:
        query = query.filter(Camp.country == country.upper())
    if region:
        query = query.filter(Camp.region == region.upper())
    if program_family:
        query = query.filter(Camp.program_family.contains(program_family))
    if camp_type:
        query = query.filter(Camp.camp_types.contains(camp_type))
    if ages_min is not None:
        query = query.filter(or_(Camp.ages_max >= ages_min, Camp.ages_max.is_(None)))
    if ages_max is not None:
        query = query.filter(or_(Camp.ages_min <= ages_max, Camp.ages_min.is_(None)))
    if grades_min is not None:
        query = query.filter(or_(Camp.grades_max >= grades_min, Camp.grades_max.is_(None)))
    if grades_max is not None:
        query = query.filter(or_(Camp.grades_min <= grades_max, Camp.grades_min.is_(None)))
    if price_max is not None:
        query = query.filter(or_(Camp.pricing_min <= price_max, Camp.pricing_min.is_(None)))
    if overnight is not None:
        query = query.filter(Camp.overnight_confirmed == overnight)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Camp.name.ilike(pattern),
                Camp.display_name.ilike(pattern),
                Camp.city.ilike(pattern),
                Camp.operator_name.ilike(pattern),
            )
        )

    total = query.count()
    items = (
        query.order_by(Camp.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return CampListOut(
        items=[CampOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=CampStatsOut)
def camp_stats(db: Session = Depends(get_db)):
    """Aggregate counts for filter facets."""
    base = db.query(Camp).filter(Camp.is_excluded.is_not(True)).filter(Camp.draft_status.in_(_SHOW_STATUSES))
    total = base.count()
    by_country = dict(
        base.filter(Camp.country.isnot(None))
        .with_entities(Camp.country, func.count(Camp.id))
        .group_by(Camp.country)
        .all()
    )
    by_region = dict(
        base.filter(Camp.region.isnot(None))
        .with_entities(Camp.region, func.count(Camp.id))
        .group_by(Camp.region)
        .all()
    )
    regions_by_country: dict[str, dict[str, int]] = {}
    region_rows = (
        base.filter(Camp.country.isnot(None), Camp.region.isnot(None))
        .with_entities(Camp.country, Camp.region, func.count(Camp.id))
        .group_by(Camp.country, Camp.region)
        .all()
    )
    for country, region, count in region_rows:
        country_bucket = regions_by_country.setdefault(country, {})
        country_bucket[region] = count
    # program_family is a JSON array stored as text, so we count per camp
    pf_counts: dict[str, int] = {}
    rows = base.filter(Camp.program_family.isnot(None)).with_entities(Camp.program_family).all()
    for (pf_raw,) in rows:
        try:
            families = json.loads(pf_raw) if pf_raw else []
        except (json.JSONDecodeError, TypeError):
            families = []
        for f in families:
            pf_counts[f] = pf_counts.get(f, 0) + 1

    return CampStatsOut(
        total=total,
        by_country=by_country,
        by_region=by_region,
        regions_by_country=regions_by_country,
        by_program_family=pf_counts,
    )


@router.get("/{record_id}", response_model=CampOut)
def get_camp(
    record_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """Single camp detail by record_id."""
    query = db.query(Camp).filter(Camp.record_id == record_id)
    if current_user is None:
        query = query.filter(Camp.is_excluded.is_not(True)).filter(
            Camp.draft_status.in_(_SHOW_STATUSES)
        )
    camp = query.first()
    if not camp:
        raise HTTPException(status_code=404, detail="Camp not found")
    if camp.is_excluded and (current_user is None or current_user.role != "parent"):
        raise HTTPException(status_code=404, detail="Camp not found")
    return CampOut.model_validate(camp)


@router.get("/{record_id}/plans", response_model=List[CampPlanMembership])
def get_camp_plans(
    record_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return all active plans this camp appears on, with shortlist status."""
    camp = db.query(Camp).filter(Camp.record_id == record_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Camp not found")
    items = (
        db.query(models.ShortlistItem)
        .join(models.SummerPlan)
        .filter(
            models.ShortlistItem.camp_id == camp.id,
            models.SummerPlan.is_active == 1,
        )
        .all()
    )
    return [
        CampPlanMembership(
            plan_id=item.plan_id,
            plan_title=item.plan.title,
            plan_year=item.plan.year,
            shortlist_item_id=item.id,
            status=item.status.value if hasattr(item.status, "value") else item.status,
        )
        for item in items
    ]


@router.patch("/{record_id}/moderation", response_model=CampOut)
def moderate_camp(
    record_id: str,
    payload: CampModerationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hide or restore a camp. Parents can hide/restore any reason; children can only flag (not restore)."""
    if current_user.role not in ("parent", "child"):
        raise HTTPException(status_code=403, detail="Sign in required")
    # Children can flag but not restore, and only for specific reasons
    if current_user.role == "child":
        if not payload.is_excluded:
            raise HTTPException(status_code=403, detail="Only parents can restore records")
        allowed_reasons = {"not_a_camp", "duplicate_or_wrong_venue"}
        if payload.reason not in allowed_reasons:
            raise HTTPException(status_code=403, detail="Children can only flag as 'not a camp' or 'duplicate'")
    camp = db.query(Camp).filter(Camp.record_id == record_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Camp not found")

    camp.is_excluded = payload.is_excluded
    if payload.is_excluded:
        camp.exclusion_reason = payload.reason
        camp.exclusion_notes = payload.notes
        camp.excluded_at = datetime.now(timezone.utc)
        camp.excluded_by_user_id = current_user.id
    else:
        camp.exclusion_reason = None
        camp.exclusion_notes = None
        camp.excluded_at = None
        camp.excluded_by_user_id = None

    db.commit()
    db.refresh(camp)
    return CampOut.model_validate(camp)


@router.patch("/{record_id}/enrich", response_model=CampOut)
def enrich_camp(
    record_id: str,
    payload: CampEnrichmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update enrichment fields on a camp from ChatGPT research."""
    camp = db.query(Camp).filter(Camp.record_id == record_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Camp not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(camp, field, value)

    if update_data:
        camp.enriched_at = datetime.now(timezone.utc)
        camp.enrichment_model = "chatgpt-manual"

    db.commit()
    db.refresh(camp)
    return CampOut.model_validate(camp)
