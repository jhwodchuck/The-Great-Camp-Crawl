"""Favorites API — authenticated users can bookmark camps with notes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
from models import Camp, Favorite, User
from schemas import FavoriteCreate, FavoriteOut, FavoriteUpdate

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("/", response_model=list[FavoriteOut])
def list_favorites(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's favorites with camp details."""
    return (
        db.query(Favorite)
        .options(joinedload(Favorite.camp))
        .filter(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )


@router.post("/", response_model=FavoriteOut)
def add_favorite(
    payload: FavoriteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a camp to the current user's favorites."""
    camp = db.query(Camp).filter(Camp.id == payload.camp_id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Camp not found")
    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == user.id, Favorite.camp_id == payload.camp_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already in favorites")
    fav = Favorite(
        user_id=user.id,
        camp_id=payload.camp_id,
        notes=payload.notes or "",
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)
    # Eagerly load camp for the response
    db.refresh(fav, attribute_names=["camp"])
    return fav


@router.patch("/{camp_id}", response_model=FavoriteOut)
def update_favorite(
    camp_id: int,
    payload: FavoriteUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update notes on a favorite."""
    fav = (
        db.query(Favorite)
        .filter(Favorite.user_id == user.id, Favorite.camp_id == camp_id)
        .first()
    )
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    if payload.notes is not None:
        fav.notes = payload.notes
    db.commit()
    db.refresh(fav, attribute_names=["camp"])
    return fav


@router.delete("/{camp_id}", status_code=204)
def remove_favorite(
    camp_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a camp from favorites."""
    fav = (
        db.query(Favorite)
        .filter(Favorite.user_id == user.id, Favorite.camp_id == camp_id)
        .first()
    )
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(fav)
    db.commit()
