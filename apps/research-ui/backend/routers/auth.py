"""Auth router: register and login."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models
import schemas
from auth import create_access_token, hash_password, verify_password, get_current_user
from database import get_db
from settings import (
    RESEARCH_UI_ALLOW_UNINVITED_FIRST_PARENT,
    RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME,
    RESEARCH_UI_PARENT_INVITE_CODE,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _parent_exists(db: Session) -> bool:
    return (
        db.query(models.User.id)
        .filter(models.User.role == models.UserRole.parent)
        .first()
        is not None
    )


def _first_parent_slot_open(db: Session) -> bool:
    return RESEARCH_UI_ALLOW_UNINVITED_FIRST_PARENT and not _parent_exists(db)


@router.get("/register-options", response_model=schemas.RegisterOptions)
def register_options(db: Session = Depends(get_db)):
    first_parent_slot_open = _first_parent_slot_open(db)
    parent_invite_required = bool(RESEARCH_UI_PARENT_INVITE_CODE) and not first_parent_slot_open
    parent_self_signup_enabled = first_parent_slot_open or bool(RESEARCH_UI_PARENT_INVITE_CODE)

    message = None
    if parent_invite_required:
        message = "Parent registration requires the deployment's invite code."
    elif parent_self_signup_enabled:
        message = "The first parent account can be created from this screen."
    elif RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME:
        message = "Parent access is pre-configured. Use the login page for the bootstrap parent account."
    else:
        message = "Parent self-registration is disabled for this deployment."

    return schemas.RegisterOptions(
        parent_self_signup_enabled=parent_self_signup_enabled,
        parent_invite_required=parent_invite_required,
        bootstrap_parent_configured=bool(RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME),
        message=message,
    )


@router.post("/register", response_model=schemas.Token, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    if payload.role == models.UserRole.parent:
        if _first_parent_slot_open(db):
            pass
        elif RESEARCH_UI_PARENT_INVITE_CODE:
            if payload.parent_invite_code != RESEARCH_UI_PARENT_INVITE_CODE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="A valid parent invite code is required to create a parent account",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Parent self-registration is disabled for this deployment",
            )

    user = models.User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.username})
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user.username})
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserOut.model_validate(current_user)
