"""SQLAlchemy ORM models for the research-ui app."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class UserRole(str, enum.Enum):
    parent = "parent"
    child = "child"


class ContributionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    changes_requested = "changes_requested"
    approved = "approved"
    rejected = "rejected"


class ReviewAction(str, enum.Enum):
    approve = "approve"
    reject = "reject"
    request_changes = "request_changes"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.child)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    missions: Mapped[list["Mission"]] = relationship("Mission", back_populates="created_by_user")
    contributions: Mapped[list["Contribution"]] = relationship("Contribution", back_populates="contributor")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="reviewer")


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    region: Mapped[str] = mapped_column(String(8), nullable=True)
    country: Mapped[str] = mapped_column(String(4), nullable=True, default="US")
    program_family: Mapped[str] = mapped_column(String(128), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_by_user: Mapped["User"] = relationship("User", back_populates="missions")
    contributions: Mapped[list["Contribution"]] = relationship("Contribution", back_populates="mission")


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, ForeignKey("missions.id"), nullable=False)
    contributor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Core camp info
    camp_name: Mapped[str] = mapped_column(String(256), nullable=False)
    website_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    country: Mapped[str] = mapped_column(String(4), nullable=True)
    region: Mapped[str] = mapped_column(String(8), nullable=True)
    city: Mapped[str] = mapped_column(String(128), nullable=True)
    venue_name: Mapped[str] = mapped_column(String(256), nullable=True)
    overnight_confirmed: Mapped[str] = mapped_column(String(8), nullable=True)  # yes/no/unknown
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")

    status: Mapped[ContributionStatus] = mapped_column(
        Enum(ContributionStatus), nullable=False, default=ContributionStatus.draft
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    mission: Mapped["Mission"] = relationship("Mission", back_populates="contributions")
    contributor: Mapped["User"] = relationship("User", back_populates="contributions")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="contribution", cascade="all, delete-orphan")
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="contribution", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="contribution", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contribution_id: Mapped[int] = mapped_column(Integer, ForeignKey("contributions.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    capture_notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    contribution: Mapped["Contribution"] = relationship("Contribution", back_populates="evidence")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contribution_id: Mapped[int] = mapped_column(Integer, ForeignKey("contributions.id"), nullable=False)
    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    contribution: Mapped["Contribution"] = relationship("Contribution", back_populates="answers")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contribution_id: Mapped[int] = mapped_column(Integer, ForeignKey("contributions.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    action: Mapped[ReviewAction] = mapped_column(Enum(ReviewAction), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    contribution: Mapped["Contribution"] = relationship("Contribution", back_populates="reviews")
    reviewer: Mapped["User"] = relationship("User", back_populates="reviews")
