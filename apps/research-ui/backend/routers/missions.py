"""Missions router."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user, require_parent
from database import get_db

router = APIRouter(prefix="/api/missions", tags=["missions"])


@router.get("/", response_model=List[schemas.MissionOut])
def list_missions(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.query(models.Mission).filter(models.Mission.is_active == 1).order_by(models.Mission.id.desc()).all()


@router.post("/", response_model=schemas.MissionOut, status_code=201)
def create_mission(
    payload: schemas.MissionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_parent),
):
    mission = models.Mission(**payload.model_dump(), created_by=current_user.id)
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


@router.get("/{mission_id}", response_model=schemas.MissionOut)
def get_mission(mission_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.patch("/{mission_id}", response_model=schemas.MissionOut)
def update_mission(
    mission_id: int,
    payload: schemas.MissionUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_parent),
):
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(mission, field, value)
    db.commit()
    db.refresh(mission)
    return mission


@router.delete("/{mission_id}", status_code=204)
def delete_mission(
    mission_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_parent),
):
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    mission.is_active = 0
    db.commit()
