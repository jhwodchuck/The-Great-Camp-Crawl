"""JWT authentication utilities."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db
from settings import (
    RESEARCH_UI_BOOTSTRAP_PARENT_DISPLAY_NAME,
    RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD,
    RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME,
    RESEARCH_UI_SECRET,
    TOKEN_EXPIRE_MINUTES,
)

SECRET_KEY = RESEARCH_UI_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exc
    return user


def require_parent(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != models.UserRole.parent:
        raise HTTPException(status_code=403, detail="Parent role required")
    return current_user


def ensure_bootstrap_parent(db: Session) -> None:
    """Create the configured bootstrap parent account once, if requested."""
    if not RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME or not RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD:
        return

    existing = (
        db.query(models.User)
        .filter(models.User.username == RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME)
        .first()
    )
    if existing:
        if existing.role != models.UserRole.parent:
            raise RuntimeError(
                "RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME already exists with a non-parent role."
            )
        return

    db.add(
        models.User(
            username=RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME,
            display_name=RESEARCH_UI_BOOTSTRAP_PARENT_DISPLAY_NAME,
            password_hash=hash_password(RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD),
            role=models.UserRole.parent,
        )
    )
    db.commit()
