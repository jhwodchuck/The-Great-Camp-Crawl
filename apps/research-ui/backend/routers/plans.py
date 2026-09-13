"""Summer Plans, Shortlist, and Notes router."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/api/plans", tags=["plans"])


# ---------------------------------------------------------------------------
# Summer Plans
# ---------------------------------------------------------------------------


@router.get("/", response_model=List[schemas.SummerPlanOut])
def list_plans(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return (
        db.query(models.SummerPlan)
        .filter(models.SummerPlan.is_active == 1)
        .order_by(models.SummerPlan.year.asc())
        .all()
    )


@router.post("/", response_model=schemas.SummerPlanOut, status_code=201)
def create_plan(
    payload: schemas.SummerPlanCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    plan = models.SummerPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=schemas.SummerPlanOut)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    plan = db.query(models.SummerPlan).filter(models.SummerPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.patch("/{plan_id}", response_model=schemas.SummerPlanOut)
def update_plan(
    plan_id: int,
    payload: schemas.SummerPlanUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    plan = db.query(models.SummerPlan).filter(models.SummerPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# Shortlist Items
# ---------------------------------------------------------------------------


@router.get("/{plan_id}/shortlist", response_model=List[schemas.ShortlistItemOut])
def list_shortlist(
    plan_id: int,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    plan = db.query(models.SummerPlan).filter(models.SummerPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    q = (
        db.query(models.ShortlistItem)
        .options(joinedload(models.ShortlistItem.camp), joinedload(models.ShortlistItem.notes).joinedload(models.ShortlistNote.author))
        .filter(models.ShortlistItem.plan_id == plan_id)
    )
    if status:
        q = q.filter(models.ShortlistItem.status == status)
    items = q.order_by(models.ShortlistItem.created_at.desc()).all()
    # Patch author display names into notes
    for item in items:
        for note in item.notes:
            note.author_display_name = note.author.display_name if note.author else None
    return items


@router.post("/{plan_id}/shortlist", response_model=schemas.ShortlistItemOut, status_code=201)
def add_to_shortlist(
    plan_id: int,
    payload: schemas.ShortlistItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = db.query(models.SummerPlan).filter(models.SummerPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if payload.camp_id:
        camp = db.query(models.Camp).filter(models.Camp.id == payload.camp_id).first()
        if not camp:
            raise HTTPException(status_code=404, detail="Camp not found")
        existing = (
            db.query(models.ShortlistItem)
            .filter(models.ShortlistItem.plan_id == plan_id, models.ShortlistItem.camp_id == payload.camp_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Camp already on shortlist for this plan")
    elif not payload.custom_camp_name:
        raise HTTPException(status_code=400, detail="Provide camp_id or custom_camp_name")

    item = models.ShortlistItem(
        plan_id=plan_id,
        camp_id=payload.camp_id,
        custom_camp_name=payload.custom_camp_name,
        custom_camp_url=payload.custom_camp_url,
        status=payload.status,
        added_by=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    if item.camp_id:
        db.refresh(item, attribute_names=["camp"])
    return item


@router.patch("/shortlist/{item_id}", response_model=schemas.ShortlistItemOut)
def update_shortlist_item(
    item_id: int,
    payload: schemas.ShortlistItemUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    item = (
        db.query(models.ShortlistItem)
        .options(joinedload(models.ShortlistItem.camp), joinedload(models.ShortlistItem.notes).joinedload(models.ShortlistNote.author))
        .filter(models.ShortlistItem.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Shortlist item not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    for note in item.notes:
        note.author_display_name = note.author.display_name if note.author else None
    return item


@router.delete("/shortlist/{item_id}", status_code=204)
def remove_from_shortlist(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    item = db.query(models.ShortlistItem).filter(models.ShortlistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shortlist item not found")
    db.delete(item)
    db.commit()


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@router.post("/shortlist/{item_id}/notes", response_model=schemas.ShortlistNoteOut, status_code=201)
def add_note(
    item_id: int,
    payload: schemas.ShortlistNoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.ShortlistItem).filter(models.ShortlistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shortlist item not found")
    note = models.ShortlistNote(
        shortlist_item_id=item_id,
        author_id=current_user.id,
        body=payload.body,
        source_url=payload.source_url,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    note.author_display_name = current_user.display_name
    return note


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    note = db.query(models.ShortlistNote).filter(models.ShortlistNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()


# ---------------------------------------------------------------------------
# Research Clipboard — copy/paste for ChatGPT
# ---------------------------------------------------------------------------


@router.get("/{plan_id}/clipboard", response_model=schemas.ResearchClipboard)
def get_research_clipboard(
    plan_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Generate a structured text block suitable for pasting into ChatGPT."""
    plan = db.query(models.SummerPlan).filter(models.SummerPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    items = (
        db.query(models.ShortlistItem)
        .options(joinedload(models.ShortlistItem.camp), joinedload(models.ShortlistItem.notes))
        .filter(models.ShortlistItem.plan_id == plan_id)
        .order_by(models.ShortlistItem.created_at)
        .all()
    )

    result_items = []
    for item in items:
        camp_name = item.camp.name if item.camp else item.custom_camp_name or "Unknown"
        camp_url = (item.camp.website_url if item.camp else item.custom_camp_url) or ""
        camp_location = ""
        if item.camp:
            parts = [p for p in [item.camp.city, item.camp.region, item.camp.country] if p]
            camp_location = ", ".join(parts)

        entry: dict = {
            "name": camp_name,
            "url": camp_url,
            "location": camp_location,
            "status": item.status.value if hasattr(item.status, "value") else item.status,
        }
        if item.camp:
            if item.camp.ages_min or item.camp.ages_max:
                entry["ages"] = f"{item.camp.ages_min or '?'}-{item.camp.ages_max or '?'}"
            if item.camp.pricing_min or item.camp.pricing_max:
                entry["pricing"] = f"${item.camp.pricing_min or '?'}-${item.camp.pricing_max or '?'}"
            if item.camp.duration_min_days or item.camp.duration_max_days:
                entry["duration_days"] = f"{item.camp.duration_min_days or '?'}-{item.camp.duration_max_days or '?'}"

        notes_list = [n.body for n in item.notes if n.body.strip()]
        if notes_list:
            entry["our_notes"] = notes_list

        result_items.append(entry)

    return schemas.ResearchClipboard(plan_title=plan.title, items=result_items)


@router.post("/{plan_id}/import-research", status_code=200)
def import_research(
    plan_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Import structured research notes from ChatGPT response.

    Expects: { "items": [ { "name": "...", "notes": "..." }, ... ] }
    Matches by camp name to existing shortlist items and appends notes.
    """
    plan = db.query(models.SummerPlan).filter(models.SummerPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    items_data = payload.get("items", [])
    if not isinstance(items_data, list):
        raise HTTPException(status_code=400, detail="Expected 'items' array")

    shortlist = (
        db.query(models.ShortlistItem)
        .options(joinedload(models.ShortlistItem.camp))
        .filter(models.ShortlistItem.plan_id == plan_id)
        .all()
    )

    # Build name -> item lookup (case-insensitive)
    name_map: dict[str, models.ShortlistItem] = {}
    for item in shortlist:
        name = (item.camp.name if item.camp else item.custom_camp_name or "").lower().strip()
        if name:
            name_map[name] = item

    added = 0
    for entry in items_data:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").lower().strip()
        notes_text = entry.get("notes") or entry.get("research") or entry.get("body") or ""
        source_url = entry.get("source_url") or entry.get("url") or None

        if not name or not notes_text:
            continue

        matched_item = name_map.get(name)
        if not matched_item:
            continue

        note = models.ShortlistNote(
            shortlist_item_id=matched_item.id,
            author_id=current_user.id,
            body=notes_text.strip(),
            source_url=source_url,
        )
        db.add(note)
        added += 1

    db.commit()
    return {"imported": added, "total_in_payload": len(items_data)}
