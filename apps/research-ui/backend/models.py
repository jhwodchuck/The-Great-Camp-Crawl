"""SQLAlchemy ORM models for the research-ui app."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contribution_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contributions.id"),
        nullable=False,
        unique=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    contribution: Mapped["Contribution"] = relationship("Contribution")


# ---------------------------------------------------------------------------
# Camp Catalog
# ---------------------------------------------------------------------------


class CampSource(str, enum.Enum):
    discovery_pipeline = "discovery_pipeline"
    child_contribution = "child_contribution"
    manual = "manual"


class Camp(Base):
    __tablename__ = "camps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=True)
    country: Mapped[str] = mapped_column(String(4), nullable=True, index=True)
    region: Mapped[str] = mapped_column(String(8), nullable=True, index=True)
    city: Mapped[str] = mapped_column(String(256), nullable=True)
    venue_name: Mapped[str] = mapped_column(String(512), nullable=True)
    program_family: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array as text
    camp_types: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array as text
    website_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    ages_min: Mapped[int] = mapped_column(Integer, nullable=True)
    ages_max: Mapped[int] = mapped_column(Integer, nullable=True)
    grades_min: Mapped[int] = mapped_column(Integer, nullable=True)
    grades_max: Mapped[int] = mapped_column(Integer, nullable=True)
    duration_min_days: Mapped[int] = mapped_column(Integer, nullable=True)
    duration_max_days: Mapped[int] = mapped_column(Integer, nullable=True)
    pricing_currency: Mapped[str] = mapped_column(String(8), nullable=True)
    pricing_min: Mapped[float] = mapped_column(Float, nullable=True)
    pricing_max: Mapped[float] = mapped_column(Float, nullable=True)
    boarding_included: Mapped[bool] = mapped_column(Boolean, nullable=True)
    overnight_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=True)
    active_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), nullable=True)
    operator_name: Mapped[str] = mapped_column(String(512), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(512), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(64), nullable=True)
    draft_status: Mapped[str] = mapped_column(String(32), nullable=True)
    description_md: Mapped[str] = mapped_column(Text, nullable=True)
    last_verified: Mapped[str] = mapped_column(String(32), nullable=True)
    source: Mapped[CampSource] = mapped_column(
        Enum(CampSource), nullable=False, default=CampSource.discovery_pipeline
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    favorites: Mapped[list["Favorite"]] = relationship("Favorite", back_populates="camp", cascade="all, delete-orphan")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "camp_id", name="uq_user_camp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    camp_id: Mapped[int] = mapped_column(Integer, ForeignKey("camps.id"), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship("User")
    camp: Mapped["Camp"] = relationship("Camp", back_populates="favorites")
