"""Database setup using SQLAlchemy."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from settings import DATABASE_URL, IS_SQLITE, SQLITE_DB_PATH

engine_kwargs = {"pool_pre_ping": True}
if IS_SQLITE:
    if SQLITE_DB_PATH is None:
        raise RuntimeError("SQLite database path was not resolved")
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
