"""Pydantic schemas for request/response validation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from models import ContributionStatus, ReviewAction, UserRole


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    username: str
    display_name: str
    password: str
    role: UserRole = UserRole.child
    parent_invite_code: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RegisterOptions(BaseModel):
    child_self_signup_enabled: bool = True
    parent_self_signup_enabled: bool
    parent_invite_required: bool
    bootstrap_parent_configured: bool
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------


class MissionCreate(BaseModel):
    title: str
    description: str = ""
    region: Optional[str] = None
    country: Optional[str] = "US"
    program_family: Optional[str] = None


class MissionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    program_family: Optional[str] = None
    is_active: Optional[int] = None


class MissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    region: Optional[str]
    country: Optional[str]
    program_family: Optional[str]
    created_by: int
    created_at: datetime
    is_active: int


# ---------------------------------------------------------------------------
# Contribution
# ---------------------------------------------------------------------------


class ContributionCreate(BaseModel):
    mission_id: int
    camp_name: str
    website_url: Optional[str] = None
    country: Optional[str] = "US"
    region: Optional[str] = None
    city: Optional[str] = None
    venue_name: Optional[str] = None
    overnight_confirmed: Optional[str] = "unknown"
    notes: Optional[str] = ""


class ContributionUpdate(BaseModel):
    camp_name: Optional[str] = None
    website_url: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    venue_name: Optional[str] = None
    overnight_confirmed: Optional[str] = None
    notes: Optional[str] = None


class ContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    contributor_id: int
    camp_name: str
    website_url: Optional[str]
    country: Optional[str]
    region: Optional[str]
    city: Optional[str]
    venue_name: Optional[str]
    overnight_confirmed: Optional[str]
    notes: Optional[str]
    status: ContributionStatus
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


class EvidenceCreate(BaseModel):
    url: Optional[str] = None
    snippet: str
    capture_notes: Optional[str] = ""


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contribution_id: int
    url: Optional[str]
    snippet: str
    capture_notes: Optional[str]
    captured_at: datetime


# ---------------------------------------------------------------------------
# Answer (guided questions)
# ---------------------------------------------------------------------------


class AnswerUpsert(BaseModel):
    question_key: str
    answer_text: str


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contribution_id: int
    question_key: str
    answer_text: str
    answered_at: datetime


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewCreate(BaseModel):
    action: ReviewAction
    notes: Optional[str] = ""


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contribution_id: int
    reviewer_id: int
    action: ReviewAction
    notes: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Export / Promote
# ---------------------------------------------------------------------------


class ExportResult(BaseModel):
    contribution_id: int
    artifact_path: str
    storage_kind: str
    exported_at: datetime
    message: str


# ---------------------------------------------------------------------------
# Camp Catalog
# ---------------------------------------------------------------------------


class CampOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: str
    name: str
    display_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    venue_name: Optional[str] = None
    program_family: Optional[str] = None
    camp_types: Optional[str] = None
    website_url: Optional[str] = None
    ages_min: Optional[int] = None
    ages_max: Optional[int] = None
    grades_min: Optional[int] = None
    grades_max: Optional[int] = None
    duration_min_days: Optional[int] = None
    duration_max_days: Optional[int] = None
    pricing_currency: Optional[str] = None
    pricing_min: Optional[float] = None
    pricing_max: Optional[float] = None
    boarding_included: Optional[bool] = None
    overnight_confirmed: Optional[bool] = None
    active_confirmed: Optional[bool] = None
    confidence: Optional[str] = None
    operator_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    draft_status: Optional[str] = None
    is_excluded: Optional[bool] = None
    exclusion_reason: Optional[str] = None
    exclusion_notes: Optional[str] = None
    excluded_at: Optional[datetime] = None
    excluded_by_user_id: Optional[int] = None
    description_md: Optional[str] = None
    last_verified: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime


class CampListOut(BaseModel):
    items: list[CampOut]
    total: int
    page: int
    page_size: int


class CampStatsOut(BaseModel):
    total: int
    by_country: dict[str, int]
    by_region: dict[str, int]
    by_program_family: dict[str, int]


class CampModerationUpdate(BaseModel):
    is_excluded: bool
    reason: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------


class FavoriteCreate(BaseModel):
    camp_id: int
    notes: Optional[str] = ""


class FavoriteUpdate(BaseModel):
    notes: Optional[str] = None


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    camp_id: int
    notes: Optional[str]
    created_at: datetime
    camp: CampOut


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------


class ScrapeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 4096:
            raise ValueError("URL too long")
        return v


class ScrapeResult(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    pricing: Optional[dict] = None
    ages: Optional[dict] = None
    duration: Optional[dict] = None
    contact: Optional[dict] = None
    overnight_signals: list[str] = []
    evidence_snippets: list[str] = []
