from __future__ import annotations

from lib.common import parse_frontmatter_document
from render_json_dump_to_md import dedupe_records, normalize_record, render_markdown, renderability_reasons


def sample_record() -> dict:
    return normalize_record(
        {
            "activity_status_guess": "active_recent",
            "camp_types": ["residential-academic", "residential"],
            "candidate_id": "harvard-pre-college-cambridge-ma",
            "canonical_url": "https://precollege.summer.harvard.edu/",
            "city": "Cambridge",
            "country": "United States",
            "duration_guess": {"label": "2 weeks", "min_days": 14, "max_days": 14},
            "name": "Harvard Pre-College Program",
            "operator_name": "Harvard Summer School",
            "overnight_evidence_snippet": "Official materials describe an intensive two-week residential experience where students live on Harvard's campus.",
            "priority_flags": {"college_precollege": True, "one_week_plus": True},
            "program_family": ["college-pre-college", "academic"],
            "recent_activity_evidence_snippet": "Current page lists 2026 session dates and pricing.",
            "record_basis": "venue_candidate",
            "region": "MA",
            "source_language": "en",
            "status": "discovered",
            "tags": ["united-states", "ma", "cambridge", "college-pre-college"],
            "validation_needs": ["contact"],
            "venue_name": "Harvard University",
            "raw_discovery_source": {
                "pricing_summary": "Official 2026 page shows $6,100 tuition plus a $75 application fee.",
                "eligibility_summary": "Official program targets high school students in grades 10-11.",
                "evidence_summary": "Harvard offers a two-week immersive on-campus pre-college experience with residential housing.",
            },
        }
    )


def test_render_markdown_outputs_schema_sections() -> None:
    rendered = render_markdown(sample_record())
    frontmatter, body = parse_frontmatter_document(rendered)

    assert frontmatter["record_id"] == "harvard-pre-college-cambridge-ma"
    assert frontmatter["camp_id"] == "harvard-pre-college-program"
    assert frontmatter["venue_id"] == "us-ma-cambridge-harvard-university"
    assert frontmatter["country"] == "US"
    assert frontmatter["country_name"] == "United States"
    assert frontmatter["region_name"] == "Massachusetts"
    assert frontmatter["verification"]["overnight_confirmed"] is True
    assert frontmatter["verification"]["active_past_2_years_confirmed"] is True
    assert frontmatter["draft_status"] == "draft"

    assert "## Quick Take" in body
    assert "## Verified Facts" in body
    assert "## Overnight Evidence" in body
    assert "## Recent Activity Evidence" in body
    assert "## Program Overview" in body
    assert "## Ages and Grades" in body
    assert "## Session Length and Structure" in body
    assert "## Pricing" in body
    assert "## Location and Venue Notes" in body
    assert "## Contact and Enrollment" in body
    assert "## Open Questions" in body
    assert "## Sources" in body


def test_renderability_reasons_flags_ambiguous_records() -> None:
    record = sample_record()
    record["record_basis"] = "multi_venue_candidate"
    record["venue_name"] = "venue to be confirmed"
    record["city"] = ""

    reasons = renderability_reasons(record)

    assert "multi_venue_candidate" in reasons
    assert "unknown_venue" in reasons
    assert "unknown_city" in reasons


def test_renderability_reasons_skip_pending_confirmation_records() -> None:
    record = sample_record()
    record["record_basis"] = "venue_candidate_pending_confirmation"
    record["venue_name"] = "JHU campus residential location to be confirmed"

    reasons = renderability_reasons(record)

    assert "pending_venue_confirmation" in reasons
    assert "unknown_venue" in reasons


def test_dedupe_records_prefers_more_specific_record() -> None:
    specific = sample_record()
    generic = sample_record()
    generic["record_basis"] = "venue_candidate_pending_confirmation"
    generic["city"] = ""
    generic["venue_name"] = "venue to be confirmed"

    deduped = dedupe_records([generic, specific])

    assert len(deduped) == 1
    assert deduped[0]["venue_name"] == "Harvard University"
