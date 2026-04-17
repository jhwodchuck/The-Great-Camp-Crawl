"""Camp catalog API — public read-only access to all imported camps."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import Camp
from schemas import CampListOut, CampOut, CampStatsOut

router = APIRouter(prefix="/api/camps", tags=["camps"])


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
    price_max: Optional[float] = None,
    overnight: Optional[bool] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Paginated list of camps with filtering."""
    # Only surface curated records (draft + candidate); exclude raw crawl candidates
    # and any record flagged as excluded.
    _SHOW_STATUSES = ("draft", "candidate")
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
    _SHOW_STATUSES = ("draft", "candidate")
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
        by_program_family=pf_counts,
    )


@router.get("/{record_id}", response_model=CampOut)
def get_camp(record_id: str, db: Session = Depends(get_db)):
    """Single camp detail by record_id."""
    camp = db.query(Camp).filter(Camp.record_id == record_id).first()
    if not camp:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Camp not found")
    return CampOut.model_validate(camp)
