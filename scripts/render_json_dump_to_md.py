from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from lib.common import build_frontmatter_document, read_jsonl, slugify, write_jsonl
from lib.region_prompt_pack import CA_REGION_ROWS, MX_REGION_ROWS, US_REGION_ROWS


COUNTRY_ALIASES = {
    "US": "US",
    "UNITED STATES": "US",
    "UNITED-STATES": "US",
    "CA": "CA",
    "CANADA": "CA",
    "MX": "MX",
    "MEXICO": "MX",
}

COUNTRY_NAMES = {
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
}

COUNTRY_FOLDERS = {
    "US": "us",
    "CA": "canada",
    "MX": "mexico",
}

CURRENCY_BY_COUNTRY = {
    "US": "USD",
    "CA": "CAD",
    "MX": "MXN",
}

PLACEHOLDER_VENUES = {
    "",
    "n/a (directory)",
    "unknown",
    "venue to be confirmed",
}

PLACEHOLDER_CITIES = {
    "",
    "n/a",
    "unknown",
    "unknown city",
}

PLACEHOLDER_VENUE_PHRASES = {
    "pending",
    "to be confirmed",
    "various campus",
    "various campuses",
    "multiple locations",
    "multiple residential sites",
}

PLACEHOLDER_CITY_PHRASES = {
    "unknown",
    "to be confirmed",
}

VALIDATION_LABELS = {
    "ages_or_grades": "Exact ages or grade bands still need confirmation.",
    "confirm_duration": "The exact session duration still needs confirmation.",
    "confirm_exact_venue": "The exact physical venue still needs confirmation.",
    "confirm_overnight": "Overnight or residential status still needs stronger direct evidence.",
    "confirm_recent_activity": "Recent activity within the last 24 months still needs confirmation.",
    "contact": "Official contact details still need to be captured.",
    "pricing": "Official pricing still needs to be captured.",
    "split_into_venue_records": "This operator appears to span multiple venues and should be split before final validation.",
}

REGION_NAMES = {
    "US": dict(US_REGION_ROWS),
    "CA": dict(CA_REGION_ROWS),
    "MX": dict(MX_REGION_ROWS),
}


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return read_jsonl(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be an array of objects or a JSONL file.")
    return [row for row in payload if isinstance(row, dict)]


def safe_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def compact(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_country_code(value: Any) -> str:
    text = compact(value).upper()
    return COUNTRY_ALIASES.get(text, text or "US")


def country_folder(code: str) -> str:
    return COUNTRY_FOLDERS.get(code, slugify(code))


def country_name(code: str) -> str:
    return COUNTRY_NAMES.get(code, code)


def region_name(code: str, region: str) -> str:
    return REGION_NAMES.get(code, {}).get(region, region)


def nested(record: dict[str, Any], key: str, field: str) -> Any:
    value = record.get(key)
    if not isinstance(value, dict):
        return None
    return value.get(field)


def pick_text(record: dict[str, Any], *pairs: tuple[str, str | None]) -> str:
    for key, nested_field in pairs:
        if nested_field is None:
            value = record.get(key)
        else:
            value = nested(record, key, nested_field)
        text = compact(value)
        if text:
            return text
    return ""


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    raw = normalized.get("raw_discovery_source")
    if not isinstance(raw, dict):
        raw = {}
    normalized["raw_discovery_source"] = raw
    normalized["country"] = normalize_country_code(normalized.get("country") or raw.get("country"))
    normalized["region"] = compact(normalized.get("region") or raw.get("region")).upper() or "UNK"
    normalized["city"] = compact(normalized.get("city") or raw.get("city"))
    normalized["venue_name"] = compact(normalized.get("venue_name") or raw.get("venue_name"))
    normalized["name"] = compact(normalized.get("name") or normalized.get("candidate_name") or raw.get("name"))
    normalized["operator_name"] = compact(normalized.get("operator_name") or raw.get("operator_name"))
    normalized["canonical_url"] = compact(normalized.get("canonical_url") or raw.get("canonical_url") or normalized.get("url"))
    normalized["source_language"] = compact(normalized.get("source_language") or raw.get("source_language"))
    normalized["overnight_evidence_snippet"] = pick_text(
        normalized,
        ("overnight_evidence_snippet", None),
        ("raw_discovery_source", "overnight_evidence_snippet"),
        ("raw_discovery_source", "evidence_summary"),
    )
    normalized["recent_activity_evidence_snippet"] = pick_text(
        normalized,
        ("recent_activity_evidence_snippet", None),
        ("raw_discovery_source", "recent_activity_evidence_snippet"),
    )
    return normalized


def dedupe_key(record: dict[str, Any]) -> str:
    canonical_url = compact(record.get("canonical_url")).rstrip("/")
    if canonical_url:
        return canonical_url.lower()
    candidate_id = compact(record.get("candidate_id"))
    if candidate_id:
        return candidate_id.lower()
    return slugify(compact(record.get("name")))


def rank_key(record: dict[str, Any]) -> tuple[Any, ...]:
    validation_needs = safe_list(record.get("validation_needs"))
    return (
        0 if record.get("record_basis") == "venue_candidate" else 1,
        0 if compact(record.get("city")).lower() not in PLACEHOLDER_CITIES else 1,
        0 if compact(record.get("venue_name")).lower() not in PLACEHOLDER_VENUES else 1,
        0 if compact(record.get("activity_status_guess")) == "active_recent" else 1,
        len(validation_needs),
        compact(record.get("name")),
    )


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for record in sorted(records, key=rank_key):
        key = dedupe_key(record)
        if key not in deduped:
            deduped[key] = record
    return list(deduped.values())


def renderability_reasons(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    record_basis = compact(record.get("record_basis"))
    venue = compact(record.get("venue_name")).lower()
    city = compact(record.get("city")).lower()
    if record_basis == "multi_venue_candidate":
        reasons.append("multi_venue_candidate")
    if record_basis == "venue_candidate_pending_confirmation":
        reasons.append("pending_venue_confirmation")
    if venue in PLACEHOLDER_VENUES or any(phrase in venue for phrase in PLACEHOLDER_VENUE_PHRASES):
        reasons.append("unknown_venue")
    if city in PLACEHOLDER_CITIES or any(phrase in city for phrase in PLACEHOLDER_CITY_PHRASES):
        reasons.append("unknown_city")
    if not compact(record.get("name")):
        reasons.append("missing_name")
    if not compact(record.get("region")):
        reasons.append("missing_region")
    return reasons


def infer_operator_type(operator_name: str, program_name: str) -> str:
    haystack = f"{operator_name} {program_name}".lower()
    if any(token in haystack for token in ["university", "college", "summer school", "academy", "school of"]):
        return "university"
    if "ymca" in haystack:
        return "ymca"
    if any(token in haystack for token in ["church", "synagogue", "ministr", "faith", "christian", "jewish"]):
        return "faith-based"
    if "camp" in haystack:
        return "camp-operator"
    return "organization"


def infer_boarding_included(record: dict[str, Any]) -> bool | None:
    text = " ".join(
        [
            compact(record.get("overnight_evidence_snippet")),
            pick_text(record, ("raw_discovery_source", "pricing_summary")),
            pick_text(record, ("raw_discovery_source", "evidence_summary")),
        ]
    ).lower()
    if any(
        phrase in text
        for phrase in [
            "housing and meals included",
            "housing included",
            "room and board included",
            "board included",
            "live on campus",
            "reside in",
            "residential students live on campus",
        ]
    ):
        return True
    return None


def extract_range(text: str, label: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    patterns = [
        rf"{label}s?\s*(\d{{1,2}})\s*(?:-|to|through)\s*(\d{{1,2}})",
        rf"{label}s?\s*(\d{{1,2}})\s*[–—]\s*(\d{{1,2}})",
    ]
    lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None, None


def derive_confidence(record: dict[str, Any], overnight_confirmed: bool, active_confirmed: bool) -> str:
    validation_needs = safe_list(record.get("validation_needs"))
    if "confirm_exact_venue" in validation_needs or compact(record.get("record_basis")) == "multi_venue_candidate":
        return "low"
    if overnight_confirmed and active_confirmed and len(validation_needs) <= 1:
        return "high"
    if overnight_confirmed or active_confirmed:
        return "medium"
    return "low"


def build_identifiers(record: dict[str, Any]) -> tuple[str, str, str]:
    camp_id = slugify(compact(record.get("name")))
    venue_id = slugify(
        "-".join(
            [
                compact(record.get("country")),
                compact(record.get("region")),
                compact(record.get("city")),
                compact(record.get("venue_name")),
            ]
        )
    )
    record_id = slugify(compact(record.get("candidate_id")) or f"{venue_id}-{camp_id}")
    return record_id, camp_id, venue_id


def unique_urls(record: dict[str, Any]) -> list[str]:
    raw = record.get("raw_discovery_source")
    urls = [
        compact(record.get("canonical_url")),
        compact(record.get("url")),
    ]
    if isinstance(raw, dict):
        urls.extend(
            [
                compact(raw.get("canonical_url")),
                compact(raw.get("normalized_url")),
                compact(raw.get("url")),
            ]
        )
    ordered: list[str] = []
    seen: set[str] = set()
    for url in urls:
        normalized = url.rstrip("/")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def humanize_validation_need(value: str) -> str:
    return VALIDATION_LABELS.get(value, value.replace("_", " ").capitalize() + ".")


def build_quick_take(record: dict[str, Any]) -> str:
    evidence_summary = pick_text(record, ("raw_discovery_source", "evidence_summary"))
    if evidence_summary:
        return evidence_summary
    duration = record.get("duration_guess") or {}
    duration_label = compact(duration.get("label"))
    family = ", ".join(safe_list(record.get("program_family"))[:3]) or "overnight/residential"
    city = compact(record.get("city"))
    region = compact(record.get("region"))
    if duration_label and duration_label != "unknown":
        return f"{record['name']} is a draft venue dossier for a {duration_label} {family} program in {city}, {region}."
    return f"{record['name']} is a draft venue dossier for a {family} program in {city}, {region}."


def build_verified_facts(record: dict[str, Any]) -> list[str]:
    duration = record.get("duration_guess") or {}
    facts = [
        f"Operator: {compact(record.get('operator_name')) or 'Unknown'}",
        f"Venue: {compact(record.get('venue_name')) or 'Unknown'}",
        f"Location: {compact(record.get('city')) or 'Unknown'}, {compact(record.get('region')) or ''}".strip(", "),
        f"Canonical URL: {compact(record.get('canonical_url')) or 'Not captured'}",
    ]
    family = safe_list(record.get("program_family"))
    if family:
        facts.append(f"Program family: {', '.join(family)}")
    duration_label = compact(duration.get("label"))
    if duration_label and duration_label != "unknown":
        facts.append(f"Known duration signal: {duration_label}")
    if compact(record.get("activity_status_guess")) == "active_recent":
        facts.append("Recent activity signal: active within the repo's 24-month window heuristic")
    return facts


def build_ages_and_grades(record: dict[str, Any]) -> str:
    eligibility_summary = pick_text(record, ("raw_discovery_source", "eligibility_summary"))
    age_min, age_max = extract_range(eligibility_summary, "age")
    grade_min, grade_max = extract_range(eligibility_summary, "grade")
    lines: list[str] = []
    if eligibility_summary:
        lines.append(eligibility_summary)
    if age_min is not None and age_max is not None:
        lines.append(f"Derived age range: {age_min}-{age_max}.")
    if grade_min is not None and grade_max is not None:
        lines.append(f"Derived grade range: {grade_min}-{grade_max}.")
    if not lines:
        lines.append("Ages and grades not yet captured.")
    return "\n\n".join(lines)


def build_session_length(record: dict[str, Any]) -> str:
    duration = record.get("duration_guess") or {}
    label = compact(duration.get("label")) or "unknown"
    min_days = duration.get("min_days")
    max_days = duration.get("max_days")
    lines = [f"Duration guess: {label}."]
    if min_days is not None or max_days is not None:
        lines.append(f"Min days: {min_days if min_days is not None else 'unknown'}; max days: {max_days if max_days is not None else 'unknown'}.")
    if (record.get("priority_flags") or {}).get("one_week_plus"):
        lines.append("This record is flagged as one-week-plus priority.")
    return "\n\n".join(lines)


def build_location_notes(record: dict[str, Any]) -> str:
    notes = safe_list(record.get("notes")) + safe_list(nested(record, "raw_discovery_source", "notes"))
    lines = [
        f"Venue anchor: {compact(record.get('venue_name'))}.",
        f"City/region anchor: {compact(record.get('city'))}, {compact(record.get('region'))}.",
    ]
    if notes:
        lines.append("Notes: " + " ".join(notes))
    return "\n\n".join(lines)


def build_contact_and_enrollment(record: dict[str, Any]) -> str:
    canonical_url = compact(record.get("canonical_url"))
    validation_needs = set(safe_list(record.get("validation_needs")))
    lines = []
    if canonical_url:
        lines.append(f"Official site: {canonical_url}")
    if "contact" in validation_needs:
        lines.append("Contact details still need to be captured from the official site.")
    if not lines:
        lines.append("Contact and enrollment details not yet captured.")
    return "\n\n".join(lines)


def build_open_questions(record: dict[str, Any]) -> list[str]:
    questions = [humanize_validation_need(item) for item in safe_list(record.get("validation_needs"))]
    if compact(record.get("record_basis")) == "venue_candidate_pending_confirmation":
        questions.append("This dossier remains a draft because venue confirmation is still incomplete.")
    return questions or ["No open questions were preserved on the discovery record."]


def build_frontmatter(record: dict[str, Any]) -> dict[str, Any]:
    record_id, camp_id, venue_id = build_identifiers(record)
    country = compact(record.get("country")) or "US"
    region = compact(record.get("region")) or "UNK"
    city = compact(record.get("city"))
    venue_name = compact(record.get("venue_name"))
    operator_name = compact(record.get("operator_name"))
    source_language = compact(record.get("source_language"))
    overnight_confirmed = bool(compact(record.get("overnight_evidence_snippet")))
    active_confirmed = compact(record.get("activity_status_guess")) == "active_recent" and bool(
        compact(record.get("recent_activity_evidence_snippet"))
    )
    pricing_summary = pick_text(record, ("raw_discovery_source", "pricing_summary"))
    duration = record.get("duration_guess") or {}
    age_min, age_max = extract_range(pick_text(record, ("raw_discovery_source", "eligibility_summary")), "age")
    grade_min, grade_max = extract_range(pick_text(record, ("raw_discovery_source", "eligibility_summary")), "grade")
    source_urls = unique_urls(record)
    canonical_url = source_urls[0] if source_urls else ""
    boarding_included = infer_boarding_included(record)

    priority_flags = record.get("priority_flags") or {}
    frontmatter: dict[str, Any] = {
        "record_id": record_id,
        "camp_id": camp_id,
        "venue_id": venue_id,
        "name": compact(record.get("name")),
        "display_name": f"{compact(record.get('name'))} at {venue_name}",
        "country": country,
        "country_name": country_name(country),
        "region": region,
        "region_name": region_name(country, region),
        "city": city,
        "venue_name": venue_name,
        "program_family": safe_list(record.get("program_family")),
        "camp_types": safe_list(record.get("camp_types")),
        "priority_flags": {
            "college_precollege": priority_flags.get("college_precollege"),
            "one_week_plus": priority_flags.get("one_week_plus"),
        },
        "languages_found": [source_language] if source_language else [],
        "source_language_primary": source_language or "",
        "activity_status": compact(record.get("activity_status_guess")) or compact(record.get("status")),
        "activity_evidence_window_months": 24,
        "duration": {
            "min_days": duration.get("min_days"),
            "max_days": duration.get("max_days"),
        },
        "pricing": {
            "currency": CURRENCY_BY_COUNTRY.get(country),
            "amount_min": None,
            "amount_max": None,
            "boarding_included": boarding_included,
        },
        "ages": {
            "min": age_min,
            "max": age_max,
        },
        "grades": {
            "min": grade_min,
            "max": grade_max,
        },
        "operator": {
            "name": operator_name,
            "type": infer_operator_type(operator_name, compact(record.get("name"))),
        },
        "website": {
            "canonical_url": canonical_url,
            "admissions_url": None,
            "session_dates_url": canonical_url if compact(record.get("recent_activity_evidence_snippet")) else None,
            "pricing_url": canonical_url if pricing_summary else None,
        },
        "contact": {
            "email": None,
            "phone": None,
        },
        "location": {
            "address": None,
            "postal_code": None,
            "latitude": None,
            "longitude": None,
        },
        "verification": {
            "overnight_confirmed": overnight_confirmed,
            "active_past_2_years_confirmed": active_confirmed,
            "confidence": derive_confidence(record, overnight_confirmed, active_confirmed),
            "last_verified": date.today().isoformat(),
        },
        "evidence": {
            "overnight_source_url": canonical_url if overnight_confirmed else None,
            "recent_activity_source_url": canonical_url if active_confirmed else None,
            "duration_source_url": canonical_url if compact(duration.get("label")) and compact(duration.get("label")) != "unknown" else None,
            "pricing_source_url": canonical_url if pricing_summary else None,
        },
        "tags": safe_list(record.get("tags")),
        "draft_status": "draft",
    }
    return frontmatter


def render_markdown(record: dict[str, Any]) -> str:
    frontmatter = build_frontmatter(record)
    quick_take = build_quick_take(record)
    overnight_evidence = compact(record.get("overnight_evidence_snippet")) or "Not yet captured."
    recent_activity = compact(record.get("recent_activity_evidence_snippet")) or "Not yet captured."
    program_overview = pick_text(record, ("raw_discovery_source", "evidence_summary")) or quick_take
    pricing = pick_text(record, ("raw_discovery_source", "pricing_summary")) or "Pricing not yet captured."
    sources = unique_urls(record)

    lines = [
        f"# {frontmatter['display_name']}",
        "",
        "## Quick Take",
        quick_take,
        "",
        "## Verified Facts",
    ]
    for fact in build_verified_facts(record):
        lines.append(f"- {fact}")

    lines.extend(
        [
            "",
            "## Overnight Evidence",
            overnight_evidence,
            "",
            "## Recent Activity Evidence",
            recent_activity,
            "",
            "## Program Overview",
            program_overview,
            "",
            "## Ages and Grades",
            build_ages_and_grades(record),
            "",
            "## Session Length and Structure",
            build_session_length(record),
            "",
            "## Pricing",
            pricing,
            "",
            "## Location and Venue Notes",
            build_location_notes(record),
            "",
            "## Contact and Enrollment",
            build_contact_and_enrollment(record),
            "",
            "## Open Questions",
        ]
    )

    for item in build_open_questions(record):
        lines.append(f"- {item}")

    lines.extend(["", "## Sources"])
    if sources:
        for url in sources:
            lines.append(f"- {url}")
    else:
        lines.append("- No source URLs captured.")

    return build_frontmatter_document(frontmatter, "\n".join(lines))


def build_output_path(base_dir: Path, record: dict[str, Any]) -> Path:
    record_id, camp_id, venue_id = build_identifiers(record)
    country = country_folder(compact(record.get("country")))
    region = slugify(compact(record.get("region")) or "unk")
    filename = f"{camp_id}--{venue_id}--{record_id}.md"
    return base_dir / country / region / filename


def main() -> int:
    parser = argparse.ArgumentParser(description="Render discovered candidates into Markdown venue dossiers.")
    parser.add_argument("input_path", help="Path to JSON array or JSONL input")
    parser.add_argument("--output-dir", default="camps", help="Base output directory for Markdown files")
    parser.add_argument("--summary-output", help="Optional JSON summary path")
    parser.add_argument("--skipped-output", help="Optional JSONL path for skipped candidates")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing dossier files")
    args = parser.parse_args()

    records = [normalize_record(record) for record in load_records(Path(args.input_path))]
    deduped = dedupe_records(records)

    rendered = 0
    skipped_existing = 0
    skipped: list[dict[str, Any]] = []
    output_dir = Path(args.output_dir)

    for record in deduped:
        reasons = renderability_reasons(record)
        if reasons:
            skipped.append(
                {
                    "candidate_id": compact(record.get("candidate_id")),
                    "name": compact(record.get("name")),
                    "country": compact(record.get("country")),
                    "region": compact(record.get("region")),
                    "city": compact(record.get("city")),
                    "venue_name": compact(record.get("venue_name")),
                    "record_basis": compact(record.get("record_basis")),
                    "canonical_url": compact(record.get("canonical_url")),
                    "reasons": reasons,
                }
            )
            continue

        out_path = build_output_path(output_dir, record)
        if out_path.exists() and not args.overwrite:
            skipped_existing += 1
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_markdown(record), encoding="utf-8")
        rendered += 1

    if args.skipped_output:
        write_jsonl(Path(args.skipped_output), skipped)

    summary = {
        "input_path": args.input_path,
        "output_dir": str(output_dir),
        "input_records": len(records),
        "deduped_records": len(deduped),
        "rendered": rendered,
        "skipped_existing": skipped_existing,
        "skipped_unrenderable": len(skipped),
    }
    if args.summary_output:
        Path(args.summary_output).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
