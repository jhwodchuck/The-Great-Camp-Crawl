#!/usr/bin/env python3
"""Export camp records from the DB back to Markdown dossier files.

For each DB record:
- Creates the dossier file if it doesn't exist.
- Updates existing files where the DB has richer data (non-null vs null fields
  in the frontmatter). The markdown body is preserved for existing files.

Usage:
    python scripts/export_db_to_dossiers.py [--db-url URL] [--region TX] [--country US] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "apps" / "research-ui" / "backend"
CAMPS_DIR = REPO_ROOT / "camps"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from models import Base, Camp  # noqa: E402
from lib.common import build_frontmatter_document, slugify  # noqa: E402
from lib.region_prompt_pack import CA_REGION_ROWS, MX_REGION_ROWS, US_REGION_ROWS  # noqa: E402

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)

COUNTRY_FOLDERS: dict[str, str] = {"US": "us", "CA": "canada", "MX": "mexico"}
COUNTRY_NAMES: dict[str, str] = {"US": "United States", "CA": "Canada", "MX": "Mexico"}
REGION_NAMES: dict[str, dict[str, str]] = {
    "US": dict(US_REGION_ROWS),
    "CA": dict(CA_REGION_ROWS),
    "MX": dict(MX_REGION_ROWS),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql+psycopg://"):
        return db_url
    if db_url.startswith("postgres://"):
        return "postgresql+psycopg://" + db_url[len("postgres://"):]
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url[len("postgresql://"):]
    return db_url


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return [str(item) for item in result]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _country_folder(country: str) -> str:
    return COUNTRY_FOLDERS.get(country.upper(), country.lower())


def _country_name(country: str) -> str:
    return COUNTRY_NAMES.get(country.upper(), country)


def _region_name(country: str, region: str) -> str:
    return REGION_NAMES.get(country.upper(), {}).get(region.upper(), region)


def _default_currency(country: str) -> str:
    return {"US": "USD", "CA": "CAD", "MX": "MXN"}.get(country.upper(), "USD")


# ---------------------------------------------------------------------------
# File index
# ---------------------------------------------------------------------------

def scan_existing_files() -> dict[str, Path]:
    """Return a map of record_id → file path for every .md in camps/."""
    index: dict[str, Path] = {}
    for path in CAMPS_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        m = _FM_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict):
            continue
        rid = fm.get("record_id")
        if rid:
            index[str(rid)] = path
    return index


# ---------------------------------------------------------------------------
# Path computation
# ---------------------------------------------------------------------------

def compute_file_path(camp: Camp) -> Path:
    """Compute the canonical output path for a Camp record."""
    country = (camp.country or "US").upper()
    region = (camp.region or "UNK").upper()
    camp_id = slugify(camp.name or "unknown")
    venue_id = slugify(f"{country}-{region}-{camp.city or ''}-{camp.venue_name or ''}")
    record_id = camp.record_id
    filename = f"{camp_id}--{venue_id}--{record_id}.md"
    return CAMPS_DIR / _country_folder(country) / region.lower() / filename


# ---------------------------------------------------------------------------
# Frontmatter builder from DB record
# ---------------------------------------------------------------------------

def camp_to_frontmatter(camp: Camp) -> dict[str, Any]:
    """Build a full frontmatter dict from a Camp DB record."""
    country = (camp.country or "US").upper()
    region = (camp.region or "UNK").upper()
    canonical_url = camp.website_url or ""
    program_family = _json_list(camp.program_family)
    camp_types = _json_list(camp.camp_types)

    tags: list[str] = list({
        country.lower(),
        *([region.lower()] if region != "UNK" else []),
        *([slugify(camp.city)] if camp.city else []),
        *program_family,
    })

    return {
        "record_id": camp.record_id,
        "camp_id": slugify(camp.name or "unknown"),
        "venue_id": slugify(f"{country}-{region}-{camp.city or ''}-{camp.venue_name or ''}"),
        "name": camp.name,
        "display_name": camp.display_name or f"{camp.name} at {camp.venue_name or 'Unknown'}",
        "country": country,
        "country_name": _country_name(country),
        "region": region,
        "region_name": _region_name(country, region),
        "city": camp.city,
        "venue_name": camp.venue_name,
        "program_family": program_family,
        "camp_types": camp_types,
        "priority_flags": {
            "college_precollege": False,
            "one_week_plus": False,
        },
        "languages_found": ["en"],
        "source_language_primary": "en",
        "activity_status": "active" if camp.active_confirmed else "unknown",
        "activity_evidence_window_months": 24,
        "duration": {
            "min_days": camp.duration_min_days,
            "max_days": camp.duration_max_days,
        },
        "pricing": {
            "currency": camp.pricing_currency or _default_currency(country),
            "amount_min": camp.pricing_min,
            "amount_max": camp.pricing_max,
            "boarding_included": camp.boarding_included,
        },
        "ages": {
            "min": camp.ages_min,
            "max": camp.ages_max,
        },
        "grades": {
            "min": camp.grades_min,
            "max": camp.grades_max,
        },
        "operator": {
            "name": camp.operator_name,
            "type": None,
        },
        "website": {
            "canonical_url": canonical_url or None,
            "admissions_url": None,
            "session_dates_url": canonical_url if camp.active_confirmed else None,
            "pricing_url": None,
        },
        "contact": {
            "email": camp.contact_email,
            "phone": camp.contact_phone,
        },
        "location": {
            "address": None,
            "postal_code": None,
            "latitude": None,
            "longitude": None,
        },
        "verification": {
            "overnight_confirmed": camp.overnight_confirmed,
            "active_past_2_years_confirmed": camp.active_confirmed,
            "confidence": camp.confidence or "low",
            "last_verified": camp.last_verified or date.today().isoformat(),
        },
        "evidence": {
            "overnight_source_url": canonical_url if camp.overnight_confirmed else None,
            "recent_activity_source_url": canonical_url if camp.active_confirmed else None,
            "duration_source_url": None,
            "pricing_source_url": None,
        },
        "tags": tags,
        "draft_status": camp.draft_status or "draft",
    }


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def _has_value(v: Any) -> bool:
    """Return True if v is a meaningful (non-null, non-empty) value."""
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return bool(v)
    return True  # numbers, bools


def _is_better(db_val: Any, existing_val: Any) -> bool:
    """True if db_val should replace existing_val."""
    return _has_value(db_val) and not _has_value(existing_val)


def merge_frontmatter(existing_fm: dict[str, Any], db_fm: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Merge db_fm into existing_fm where DB is richer. Returns (merged_fm, change_count)."""
    merged = dict(existing_fm)
    changes = 0

    flat_keys = [
        "name", "display_name", "country", "country_name", "region", "region_name",
        "city", "venue_name", "program_family", "camp_types", "activity_status",
        "draft_status", "source_language_primary",
    ]
    for key in flat_keys:
        if _is_better(db_fm.get(key), existing_fm.get(key)):
            merged[key] = db_fm[key]
            changes += 1

    nested_sections: dict[str, list[str]] = {
        "duration": ["min_days", "max_days"],
        "pricing": ["currency", "amount_min", "amount_max", "boarding_included"],
        "ages": ["min", "max"],
        "grades": ["min", "max"],
        "operator": ["name", "type"],
        "website": ["canonical_url", "admissions_url", "session_dates_url", "pricing_url"],
        "contact": ["email", "phone"],
        "location": ["address", "postal_code", "latitude", "longitude"],
        "verification": ["overnight_confirmed", "active_past_2_years_confirmed", "confidence", "last_verified"],
        "evidence": ["overnight_source_url", "recent_activity_source_url", "duration_source_url", "pricing_source_url"],
    }
    for section, fields in nested_sections.items():
        existing_section = existing_fm.get(section) or {}
        db_section = db_fm.get(section) or {}
        merged_section = dict(existing_section)
        for field in fields:
            if _is_better(db_section.get(field), existing_section.get(field)):
                merged_section[field] = db_section[field]
                changes += 1
        merged[section] = merged_section

    return merged, changes


# ---------------------------------------------------------------------------
# Body builder for new records
# ---------------------------------------------------------------------------

def build_new_body(camp: Camp, fm: dict[str, Any]) -> str:
    """Build a markdown body for a brand-new dossier, or reuse description_md."""
    # If description_md was stored (e.g. from a previous import), use it.
    if camp.description_md and camp.description_md.strip():
        # Ensure it starts with an H1 header
        body = camp.description_md.strip()
        display_name = fm.get("display_name") or camp.name or "Unknown"
        if not body.startswith("#"):
            body = f"# {display_name}\n\n{body}"
        return body

    # Generate a minimal template.
    name = camp.name or "Unknown"
    display_name = fm.get("display_name") or name
    city = camp.city or "Unknown"
    region = fm.get("region", "")
    family = ", ".join(fm.get("program_family") or []) or "overnight/residential"
    operator = camp.operator_name or "Unknown"
    canonical_url = camp.website_url or ""

    lines: list[str] = [
        f"# {display_name}",
        "",
        "## Quick Take",
        f"{name} is a draft venue dossier for a {family} program in {city}, {region}.",
        "",
        "## Verified Facts",
        f"- Operator: {operator}",
        f"- Venue: {camp.venue_name or 'Unknown'}",
        f"- Location: {city}, {region}",
    ]
    if canonical_url:
        lines.append(f"- Canonical URL: {canonical_url}")
    if family:
        lines.append(f"- Program family: {family}")

    lines += ["", "## Overnight Evidence", "Not yet captured.", "", "## Recent Activity Evidence", "Not yet captured.", ""]

    if camp.ages_min is not None or camp.ages_max is not None:
        ages_str = f"Ages {camp.ages_min or '?'}-{camp.ages_max or '?'}."
    else:
        ages_str = "Ages and grades not yet captured."
    lines += ["## Ages and Grades", ages_str, ""]

    if camp.duration_min_days is not None or camp.duration_max_days is not None:
        dur_str = f"Min days: {camp.duration_min_days or '?'}; max days: {camp.duration_max_days or '?'}."
    else:
        dur_str = "Duration not yet captured."
    lines += ["## Session Length and Structure", dur_str, ""]

    if camp.pricing_min is not None or camp.pricing_max is not None:
        currency = camp.pricing_currency or "USD"
        pricing_str = f"{currency} {camp.pricing_min or '?'}-{camp.pricing_max or '?'}."
    else:
        pricing_str = "Pricing not yet captured."
    lines += ["## Pricing", pricing_str, ""]

    lines += ["## Location and Venue Notes", f"Venue anchor: {camp.venue_name or 'Unknown'}.", f"City/region anchor: {city}, {region}.", ""]

    lines += ["## Contact and Enrollment"]
    if canonical_url:
        lines.append(f"Official site: {canonical_url}")
    if camp.contact_email:
        lines.append(f"Email: {camp.contact_email}")
    if camp.contact_phone:
        lines.append(f"Phone: {camp.contact_phone}")
    if not canonical_url and not camp.contact_email:
        lines.append("Contact details not yet captured.")

    if canonical_url:
        lines += ["", "## Sources", f"- {canonical_url}"]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main export
# ---------------------------------------------------------------------------

def export_dossiers(db_url: str, country_filter: str | None, region_filter: str | None, dry_run: bool) -> dict[str, int]:
    engine = create_engine(_normalize_db_url(db_url))
    Session = sessionmaker(bind=engine)
    db = Session()

    query = db.query(Camp)
    if country_filter:
        query = query.filter(Camp.country == country_filter.upper())
    if region_filter:
        query = query.filter(Camp.region == region_filter.upper())

    camps = query.all()
    print(f"Loaded {len(camps)} records from DB" + (f" (country={country_filter}, region={region_filter})" if country_filter or region_filter else ""))

    existing_index = scan_existing_files()
    print(f"Indexed {len(existing_index)} existing dossier files")

    counts: dict[str, int] = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}

    for camp in camps:
        if not camp.record_id or not camp.name:
            counts["skipped"] += 1
            continue

        existing_path = existing_index.get(camp.record_id)

        if existing_path is None:
            # Create new file
            out_path = compute_file_path(camp)
            fm = camp_to_frontmatter(camp)
            body = build_new_body(camp, fm)
            content = build_frontmatter_document(fm, body)
            if not dry_run:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")
            print(f"  CREATE {out_path.relative_to(REPO_ROOT)}")
            counts["created"] += 1

        else:
            # Merge into existing file
            text = existing_path.read_text(encoding="utf-8")
            m = _FM_RE.match(text)
            if not m:
                counts["skipped"] += 1
                continue
            try:
                existing_fm = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                counts["skipped"] += 1
                continue
            body = m.group(2).strip()

            db_fm = camp_to_frontmatter(camp)
            merged_fm, changes = merge_frontmatter(existing_fm, db_fm)

            if changes == 0:
                counts["unchanged"] += 1
                continue

            content = build_frontmatter_document(merged_fm, body)
            if not dry_run:
                existing_path.write_text(content, encoding="utf-8")
            print(f"  UPDATE {existing_path.relative_to(REPO_ROOT)} ({changes} field(s))")
            counts["updated"] += 1

    db.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Export DB camp records to Markdown dossier files")
    parser.add_argument("--db-url", default=os.environ.get("RESEARCH_UI_DATABASE_URL") or os.environ.get("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'research.db'}"), help="Database URL")
    parser.add_argument("--country", help="Filter by country code, e.g. US")
    parser.add_argument("--region", help="Filter by region code, e.g. TX")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] No files will be written.")

    counts = export_dossiers(args.db_url, args.country, args.region, args.dry_run)
    action = "Would create/update" if args.dry_run else "Done."
    print(f"\n{action} Created: {counts['created']}, Updated: {counts['updated']}, Unchanged: {counts['unchanged']}, Skipped: {counts['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
