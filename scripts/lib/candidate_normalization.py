from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from lib.common import compact_whitespace, slugify
from lib.url_utils import extract_host, normalize_url


PROGRAM_FAMILY_RULES: list[tuple[str, str]] = [
    ("pre-college", "college-pre-college"),
    ("precollege", "college-pre-college"),
    ("young global scholars", "college-pre-college"),
    ("summer school", "college-pre-college"),
    ("academic", "academic"),
    ("engineering", "stem"),
    ("stem", "stem"),
    ("robotics", "stem"),
    ("coding", "stem"),
    ("science", "stem"),
    ("music", "music"),
    ("band", "music"),
    ("arts", "arts"),
    ("theater", "arts"),
    ("dance", "arts"),
    ("sport", "sports"),
    ("soccer", "sports"),
    ("baseball", "sports"),
    ("basketball", "sports"),
    ("faith", "faith-based"),
    ("church", "faith-based"),
    ("retreat", "faith-based"),
    ("family camp", "family"),
    ("family retreat", "family"),
    ("adventure", "adventure"),
    ("wilderness", "wilderness"),
]


def infer_program_family(text: str) -> list[str]:
    families: list[str] = []
    haystack = text.lower()
    for needle, family in PROGRAM_FAMILY_RULES:
        if needle in haystack and family not in families:
            families.append(family)
    return families or ["unspecified"]


def infer_camp_types(text: str) -> list[str]:
    haystack = text.lower()
    camp_types: list[str] = []
    if "overnight" in haystack:
        camp_types.append("overnight")
    if "residential" in haystack:
        camp_types.append("residential")
    if any(token in haystack for token in ["on campus", "live on campus", "dorm", "residence hall"]):
        camp_types.append("residential-academic")
    return camp_types or ["unknown"]


def infer_duration(text: str) -> dict[str, Any]:
    haystack = text.lower()
    if "one-week-plus" in haystack or "one week or longer" in haystack:
        return {"label": "one-week-plus", "min_days": 7, "max_days": None}
    if "multi-week" in haystack:
        return {"label": "multi-week", "min_days": 7, "max_days": None}
    week_match = re.search(r"(\d+)[ -]?week", haystack)
    if week_match:
        weeks = int(week_match.group(1))
        return {
            "label": f"{weeks}-week",
            "min_days": weeks * 7,
            "max_days": weeks * 7,
        }
    word_weeks = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
    }
    for label, weeks in word_weeks.items():
        if re.search(rf"\b{label}[ -]?week\b", haystack):
            return {
                "label": f"{label}-week",
                "min_days": weeks * 7,
                "max_days": weeks * 7,
            }
    if "week" in haystack:
        return {"label": "week-based", "min_days": 7, "max_days": None}
    return {"label": "unknown", "min_days": None, "max_days": None}


def infer_activity_status(text: str, current_year: int | None = None) -> str:
    year = current_year or datetime.now(timezone.utc).year
    years = {str(year), str(year - 1), str(year - 2)}
    haystack = text.lower()
    if any(found in haystack for found in years):
        return "active_recent"
    if any(token in haystack for token in ["open for summer", "registration is open", "enroll now", "apply now"]):
        return "active_recent"
    return "unknown"


def build_candidate_id(
    country: str,
    region: str,
    name: str,
    city: str | None,
    venue_name: str | None,
    canonical_url: str | None,
    record_basis: str,
) -> str:
    city_slug = slugify(city or ("multi site" if record_basis == "multi_venue_candidate" else "unknown city"))
    venue_slug = slugify(venue_name or ("pending venue" if record_basis != "multi_venue_candidate" else "multi site"))
    base = f"cand-{country}-{region}-{city_slug}-{name}-{venue_slug}"
    if canonical_url and venue_slug in {"pending-venue", "unknown"}:
        base = f"{base}-{slugify(extract_host(normalize_url(canonical_url)))}"
    return slugify(base)


def detect_record_basis(venue_name: str | None, uncertainty: str | None, city: str | None) -> str:
    venue_text = compact_whitespace(venue_name or "").lower()
    uncertainty_text = compact_whitespace(uncertainty or "").lower()
    combined = f"{venue_text} {uncertainty_text}".strip()
    if any(token in combined for token in ["multiple", "various", "different campuses", "multiple residential sites", "multi-site"]):
        return "multi_venue_candidate"
    if any(token in combined for token in ["to be confirmed", "pending", "residential sites", "campus / residential sites"]):
        return "venue_candidate_pending_confirmation"
    if not venue_text or venue_text in {"venue to be confirmed", "unknown"} or not city:
        return "venue_candidate_pending_confirmation"
    return "venue_candidate"


def infer_tags(country: str, region: str, city: str | None, families: list[str], camp_types: list[str]) -> list[str]:
    tags = [slugify(country), slugify(region)]
    if city:
        tags.append(slugify(city))
    tags.extend(slugify(value) for value in [*families, *camp_types] if value and value != "unspecified")
    return list(dict.fromkeys(tags))


def derive_validation_needs(
    record_basis: str,
    camp_types: list[str],
    activity_status: str,
    duration_guess: dict[str, Any],
    has_recent_snippet: bool,
    has_contact: bool,
    has_pricing: bool,
    has_age_info: bool,
) -> list[str]:
    needs: list[str] = []
    if record_basis == "multi_venue_candidate":
        needs.append("split_into_venue_records")
    if record_basis == "venue_candidate_pending_confirmation":
        needs.append("confirm_exact_venue")
    if camp_types == ["unknown"]:
        needs.append("confirm_overnight")
    if activity_status != "active_recent" or not has_recent_snippet:
        needs.append("confirm_recent_activity")
    if duration_guess.get("label") == "unknown":
        needs.append("confirm_duration")
    if not has_pricing:
        needs.append("pricing")
    if not has_contact:
        needs.append("contact")
    if not has_age_info:
        needs.append("ages_or_grades")
    return needs


def _merge_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _parse_provisional_tags(tags: list[str]) -> tuple[list[str], list[str], dict[str, Any] | None]:
    families: list[str] = []
    camp_types: list[str] = []
    duration_guess: dict[str, Any] | None = None
    for tag in tags:
        lower = tag.lower()
        if lower in {
            "college-pre-college",
            "academic",
            "stem",
            "music",
            "arts",
            "sports",
            "faith-based",
            "family",
            "traditional",
            "adventure",
            "wilderness",
        }:
            families.append(lower)
        if lower in {"overnight", "residential", "residential-academic"}:
            camp_types.append(lower)
        if duration_guess is None and "week" in lower:
            duration_guess = infer_duration(lower)
    return _merge_unique(families), _merge_unique(camp_types), duration_guess


def extract_input_fields(record: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    title = record.get("candidate_name") or record.get("name") or record.get("title") or record.get("url") or "unknown-candidate"
    operator_name = record.get("operator_name")
    city = defaults.get("city") if defaults.get("city") is not None else record.get("city")
    region = record.get("region") or defaults.get("region") or "UNK"
    country = record.get("country") or defaults.get("country") or "US"
    venue_name = defaults.get("venue_name") or record.get("venue_name")
    canonical_url = record.get("canonical_url") or record.get("url")
    overnight_snippet = record.get("overnight_evidence_snippet") or record.get("snippet")
    recent_snippet = record.get("recent_activity_evidence_snippet")
    source_language = record.get("source_language")
    uncertainty = record.get("uncertainty")
    text = compact_whitespace(
        " ".join(
            str(record.get(key, ""))
            for key in [
                "candidate_name",
                "name",
                "title",
                "snippet",
                "query",
                "overnight_evidence_snippet",
                "recent_activity_evidence_snippet",
                "venue_name",
                "operator_name",
                "uncertainty",
            ]
        )
    )
    return {
        "name": title,
        "operator_name": operator_name,
        "city": city,
        "region": region,
        "country": country,
        "venue_name": venue_name,
        "canonical_url": canonical_url,
        "overnight_evidence_snippet": overnight_snippet,
        "recent_activity_evidence_snippet": recent_snippet,
        "source_language": source_language,
        "uncertainty": uncertainty,
        "combined_text": text,
    }


def normalize_candidate_record(record: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    extracted = extract_input_fields(record, defaults)
    text = extracted["combined_text"]
    provisional_tags = [str(tag) for tag in (record.get("provisional_program_family_tags") or [])]
    provisional_families, provisional_camp_types, provisional_duration = _parse_provisional_tags(provisional_tags)
    families = _merge_unique(list(record.get("program_family") or []) + provisional_families + infer_program_family(text))
    camp_types = _merge_unique(list(record.get("camp_types") or []) + provisional_camp_types + infer_camp_types(text))
    if len(families) > 1 and "unspecified" in families:
        families = [family for family in families if family != "unspecified"]
    if len(camp_types) > 1 and "unknown" in camp_types:
        camp_types = [camp_type for camp_type in camp_types if camp_type != "unknown"]
    duration_guess = record.get("duration_guess") or provisional_duration or infer_duration(" ".join([text, *provisional_tags]))
    record_basis = record.get("record_basis") or detect_record_basis(
        extracted["venue_name"], extracted["uncertainty"], extracted["city"]
    )
    activity_status = record.get("activity_status_guess") or infer_activity_status(text)
    candidate_id = record.get("candidate_id") or build_candidate_id(
        country=extracted["country"],
        region=extracted["region"],
        city=extracted["city"],
        name=extracted["name"],
        venue_name=extracted["venue_name"],
        canonical_url=extracted["canonical_url"],
        record_basis=record_basis,
    )

    notes = list(record.get("notes") or [])
    if extracted["uncertainty"]:
        notes.append(compact_whitespace(str(extracted["uncertainty"])))

    has_contact = bool(record.get("contact") or record.get("contact_email") or record.get("contact_phone"))
    has_pricing = bool(record.get("pricing") or record.get("price") or record.get("tuition"))
    has_age_info = bool(record.get("ages") or record.get("grades") or record.get("age_range") or record.get("grade_range"))
    validation_needs = sorted(
        set(
            record.get("validation_needs")
            or derive_validation_needs(
                record_basis=record_basis,
                camp_types=camp_types,
                activity_status=activity_status,
                duration_guess=duration_guess,
                has_recent_snippet=bool(extracted["recent_activity_evidence_snippet"]),
                has_contact=has_contact,
                has_pricing=has_pricing,
                has_age_info=has_age_info,
            )
        )
    )
    priority_flags = record.get("priority_flags") or {
        "college_precollege": "college-pre-college" in families,
        "one_week_plus": bool((duration_guess.get("min_days") or 0) >= 7),
    }

    normalized = {
        "candidate_id": candidate_id,
        "record_basis": record_basis,
        "name": extracted["name"],
        "operator_name": extracted["operator_name"],
        "venue_name": extracted["venue_name"] or "venue to be confirmed",
        "city": extracted["city"],
        "region": extracted["region"],
        "country": extracted["country"],
        "canonical_url": normalize_url(extracted["canonical_url"]) if extracted["canonical_url"] else None,
        "source_language": extracted["source_language"],
        "program_family": list(dict.fromkeys(families)),
        "camp_types": list(dict.fromkeys(camp_types)),
        "priority_flags": priority_flags,
        "activity_status_guess": activity_status,
        "duration_guess": duration_guess,
        "tags": infer_tags(extracted["country"], extracted["region"], extracted["city"], families, camp_types),
        "overnight_evidence_snippet": extracted["overnight_evidence_snippet"],
        "recent_activity_evidence_snippet": extracted["recent_activity_evidence_snippet"],
        "validation_needs": validation_needs,
        "notes": list(dict.fromkeys(note for note in notes if note)),
        "status": record.get("status") or "discovered",
        "raw_discovery_source": record,
    }
    return normalized


def normalize_candidate_rows(rows: list[dict[str, Any]], defaults: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    normalized = [normalize_candidate_record(row, defaults=defaults) for row in rows]
    normalized.sort(key=lambda row: row["candidate_id"])
    return normalized
