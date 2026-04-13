from __future__ import annotations

from lib.candidate_normalization import (
    build_candidate_id,
    infer_duration,
    infer_program_family,
    normalize_candidate_record,
)
from lib.common import slugify


def test_slugify_normalizes_ascii_text() -> None:
    assert slugify("Johns Hopkins / Homewood Campus") == "johns-hopkins-homewood-campus"


def test_candidate_id_stays_stable_for_same_core_identity() -> None:
    first = build_candidate_id(
        country="US",
        region="MD",
        name="Engineering Innovation",
        city="Baltimore",
        venue_name="venue to be confirmed",
        canonical_url="https://ei.jhu.edu/?utm_source=test",
        record_basis="venue_candidate_pending_confirmation",
    )
    second = build_candidate_id(
        country="US",
        region="MD",
        name="Engineering Innovation",
        city="Baltimore",
        venue_name="venue to be confirmed",
        canonical_url="https://ei.jhu.edu/",
        record_basis="venue_candidate_pending_confirmation",
    )
    assert first == second


def test_duration_inference_detects_one_week_plus() -> None:
    result = infer_duration("Residential offerings include one week or longer programs for teens.")
    assert result["label"] == "one-week-plus"
    assert result["min_days"] == 7


def test_program_family_inference_is_conservative() -> None:
    families = infer_program_family("Pre-college engineering residential summer camp")
    assert "college-pre-college" in families
    assert "stem" in families


def test_normalize_candidate_record_supports_existing_discovery_style() -> None:
    normalized = normalize_candidate_record(
        {
            "candidate_name": "Johns Hopkins Engineering Innovation",
            "operator_name": "Johns Hopkins University",
            "city": "Baltimore",
            "region": "MD",
            "country": "US",
            "venue_name": "JHU campus (residential locations to be confirmed)",
            "canonical_url": "https://ei.jhu.edu/",
            "provisional_program_family_tags": ["college-pre-college", "residential", "four-week"],
            "overnight_evidence_snippet": "Live on campus in our immersive four-week programs.",
            "recent_activity_evidence_snippet": "Applications for Summer 2026 are open.",
            "uncertainty": "Exact residential venue needs confirmation.",
        }
    )
    assert normalized["record_basis"] == "venue_candidate_pending_confirmation"
    assert normalized["priority_flags"]["college_precollege"] is True
    assert normalized["priority_flags"]["one_week_plus"] is True
    assert "confirm_exact_venue" in normalized["validation_needs"]
