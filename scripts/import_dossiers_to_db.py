#!/usr/bin/env python3
"""Import camp dossiers from camps/**/*.md into the research-ui database.

Usage:
    python scripts/import_dossiers_to_db.py [--db-url DATABASE_URL]

Reads all camps/**/*.md files with YAML frontmatter and upserts them
into the Camp table. Optionally also imports unresolved candidates
from data/staging/discovered-candidates.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Allow importing from the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "research-ui" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from models import Base, Camp, CampSource  # noqa: E402
from schema_runtime import ensure_runtime_schema  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPS_DIR = REPO_ROOT / "camps"
CANDIDATES_FILE = REPO_ROOT / "data" / "staging" / "discovered-candidates.jsonl"

# Regex to split YAML frontmatter from markdown body
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)

COUNTRY_ALIASES = {
    "US": "US",
    "USA": "US",
    "UNITED STATES": "US",
    "UNITED STATES OF AMERICA": "US",
    "CA": "CA",
    "CAN": "CA",
    "CANADA": "CA",
    "MX": "MX",
    "MEX": "MX",
    "MEXICO": "MX",
}


def parse_dossier(path: Path) -> dict | None:
    """Parse a camp dossier .md file and return a dict for the Camp model."""
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return None
    fm_text, body = m.groups()
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None

    record_id = fm.get("record_id")
    name = fm.get("name")
    if not record_id or not name:
        return None

    # Flatten nested structures
    pricing = fm.get("pricing", {}) or {}
    ages = fm.get("ages", {}) or {}
    grades = fm.get("grades", {}) or {}
    duration = fm.get("duration", {}) or {}
    contact = fm.get("contact", {}) or {}
    website = fm.get("website", {}) or {}
    verification = fm.get("verification", {}) or {}
    operator = fm.get("operator", {}) or {}

    program_family = fm.get("program_family")
    camp_types = fm.get("camp_types")

    return {
        "record_id": record_id,
        "name": name,
        "display_name": fm.get("display_name"),
        "country": fm.get("country"),
        "region": fm.get("region"),
        "city": fm.get("city"),
        "venue_name": fm.get("venue_name"),
        "program_family": json.dumps(program_family) if isinstance(program_family, list) else None,
        "camp_types": json.dumps(camp_types) if isinstance(camp_types, list) else None,
        "website_url": website.get("canonical_url"),
        "ages_min": _safe_int(ages.get("min")),
        "ages_max": _safe_int(ages.get("max")),
        "grades_min": _safe_int(grades.get("min")),
        "grades_max": _safe_int(grades.get("max")),
        "duration_min_days": _safe_int(duration.get("min_days")),
        "duration_max_days": _safe_int(duration.get("max_days")),
        "pricing_currency": pricing.get("currency"),
        "pricing_min": _safe_float(pricing.get("amount_min")),
        "pricing_max": _safe_float(pricing.get("amount_max")),
        "boarding_included": pricing.get("boarding_included"),
        "overnight_confirmed": verification.get("overnight_confirmed"),
        "active_confirmed": verification.get("active_past_2_years_confirmed"),
        "confidence": verification.get("confidence"),
        "operator_name": operator.get("name") or None,
        "contact_email": contact.get("email"),
        "contact_phone": contact.get("phone"),
        "draft_status": fm.get("draft_status"),
        "description_md": body.strip() if body.strip() else None,
        "last_verified": verification.get("last_verified"),
        "source": CampSource.discovery_pipeline,
    }


def _safe_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _safe_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_country(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return COUNTRY_ALIASES.get(text.upper(), text.upper() if len(text) <= 3 else text)


def _normalize_region(value: Any) -> str | None:
    text = str(value or "").strip()
    return text.upper() or None


def _normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql+psycopg://"):
        return db_url
    if db_url.startswith("postgres://"):
        return "postgresql+psycopg://" + db_url[len("postgres://") :]
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url[len("postgresql://") :]
    return db_url


def _candidate_duration(cand: dict[str, Any]) -> dict[str, Any]:
    for value in (cand.get("duration"), cand.get("duration_guess")):
        if isinstance(value, dict):
            return value
    raw_source = _as_dict(cand.get("raw_discovery_source"))
    for value in (raw_source.get("duration"), raw_source.get("duration_guess")):
        if isinstance(value, dict):
            return value
    return {}


def _candidate_website_url(cand: dict[str, Any]) -> str | None:
    website = _as_dict(cand.get("website"))
    raw_source = _as_dict(cand.get("raw_discovery_source"))
    raw_website = _as_dict(raw_source.get("website"))
    return (
        website.get("canonical_url")
        or cand.get("canonical_url")
        or raw_website.get("canonical_url")
        or raw_source.get("canonical_url")
        or cand.get("website_url")
    )


def _candidate_description(cand: dict[str, Any]) -> str | None:
    title = cand.get("display_name") or cand.get("name") or cand.get("candidate_id")
    if not title:
        return None

    lines: list[str] = [f"# {title}"]
    summary_bits: list[str] = []

    operator_name = cand.get("operator_name")
    venue_name = cand.get("venue_name")
    location = ", ".join(part for part in [cand.get("city"), cand.get("region"), cand.get("country")] if part)
    record_basis = cand.get("record_basis")
    activity_status = cand.get("activity_status_guess")

    if operator_name:
        summary_bits.append(f"Operator: {operator_name}.")
    if venue_name:
        summary_bits.append(f"Venue: {venue_name}.")
    if location:
        summary_bits.append(f"Location: {location}.")
    if record_basis:
        summary_bits.append(f"Discovery basis: {record_basis}.")
    if activity_status:
        summary_bits.append(f"Activity status guess: {activity_status}.")

    if summary_bits:
        lines.append("## Discovery Summary\n" + " ".join(summary_bits))

    overnight = str(cand.get("overnight_evidence_snippet") or "").strip()
    if overnight:
        lines.append("## Overnight Evidence\n" + overnight)

    recent = str(cand.get("recent_activity_evidence_snippet") or "").strip()
    if recent:
        lines.append("## Recent Activity Evidence\n" + recent)

    notes = cand.get("notes")
    if isinstance(notes, list):
        note_items = [str(item).strip() for item in notes if str(item).strip()]
    elif notes:
        note_items = [str(notes).strip()]
    else:
        note_items = []
    if note_items:
        lines.append("## Notes\n" + "\n".join(f"- {item}" for item in note_items))

    validation_needs = cand.get("validation_needs")
    if isinstance(validation_needs, list):
        validation_items = [str(item).strip() for item in validation_needs if str(item).strip()]
    elif validation_needs:
        validation_items = [str(validation_needs).strip()]
    else:
        validation_items = []
    if validation_items:
        lines.append("## Validation Needs\n" + "\n".join(f"- {item}" for item in validation_items))

    return "\n\n".join(lines)


def _candidate_draft_status(record_basis: Any) -> str:
    value = str(record_basis or "").strip()
    if value == "venue_candidate":
        return "candidate"
    if value == "venue_candidate_pending_confirmation":
        return "candidate_pending"
    if value == "multi_venue_candidate":
        return "multi_venue"
    return value or "candidate"


def import_dossiers(db_url: str) -> dict:
    """Import all dossiers and return counts."""
    engine = create_engine(_normalize_db_url(db_url))
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    existing_by_id = {camp.record_id: camp for camp in db.query(Camp).all()}

    counts = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
    seen_record_ids: set[str] = set()

    # Phase 1: Import from camps/**/*.md
    dossier_files = sorted(CAMPS_DIR.rglob("*.md"))
    print(f"Found {len(dossier_files)} dossier files in {CAMPS_DIR}")

    for path in dossier_files:
        data = parse_dossier(path)
        if not data:
            counts["skipped"] += 1
            continue

        rid = data["record_id"]
        seen_record_ids.add(rid)

        existing = existing_by_id.get(rid)
        if existing:
            for key, val in data.items():
                if key != "record_id":
                    setattr(existing, key, val)
            counts["updated"] += 1
        else:
            camp = Camp(**data)
            db.add(camp)
            existing_by_id[rid] = camp
            counts["inserted"] += 1

    # Phase 2: Import candidates not yet rendered as dossiers
    if CANDIDATES_FILE.exists():
        cand_inserted = 0
        cand_updated = 0
        with open(CANDIDATES_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    cand = json.loads(line)
                except json.JSONDecodeError:
                    counts["errors"] += 1
                    continue
                rid = cand.get("record_id") or cand.get("candidate_id")
                if not rid or rid in seen_record_ids:
                    continue
                seen_record_ids.add(rid)

                existing = existing_by_id.get(rid)

                name = cand.get("name") or cand.get("display_name") or cand.get("camp_name")
                if not name:
                    continue

                program_family = cand.get("program_family")
                camp_types = cand.get("camp_types")
                pricing = cand.get("pricing", {}) or {}
                ages = cand.get("ages", {}) or {}
                duration = _candidate_duration(cand)
                contact = cand.get("contact", {}) or {}
                website_url = _candidate_website_url(cand)
                record_basis = cand.get("record_basis")
                overnight_snippet = str(cand.get("overnight_evidence_snippet") or "").strip()
                recent_snippet = str(cand.get("recent_activity_evidence_snippet") or "").strip()
                active_recent = cand.get("activity_status_guess") == "active_recent"

                candidate_payload = {
                    "record_id": rid,
                    "name": name,
                    "display_name": cand.get("display_name"),
                    "country": _normalize_country(cand.get("country")),
                    "region": _normalize_region(cand.get("region")),
                    "city": cand.get("city"),
                    "venue_name": cand.get("venue_name"),
                    "program_family": json.dumps(program_family) if isinstance(program_family, list) else None,
                    "camp_types": json.dumps(camp_types) if isinstance(camp_types, list) else None,
                    "website_url": website_url,
                    "ages_min": _safe_int(ages.get("min")),
                    "ages_max": _safe_int(ages.get("max")),
                    "duration_min_days": _safe_int(duration.get("min_days")),
                    "duration_max_days": _safe_int(duration.get("max_days")),
                    "pricing_currency": pricing.get("currency"),
                    "pricing_min": _safe_float(pricing.get("amount_min")),
                    "pricing_max": _safe_float(pricing.get("amount_max")),
                    "overnight_confirmed": True if record_basis == "venue_candidate" and overnight_snippet else None,
                    "active_confirmed": True if active_recent and recent_snippet else None,
                    "confidence": "medium" if record_basis == "venue_candidate" else "low",
                    "operator_name": cand.get("operator_name"),
                    "contact_email": contact.get("email"),
                    "contact_phone": contact.get("phone"),
                    "draft_status": _candidate_draft_status(record_basis),
                    "description_md": _candidate_description(cand),
                    "source": CampSource.discovery_pipeline,
                }

                if existing:
                    for key, val in candidate_payload.items():
                        if key != "record_id":
                            setattr(existing, key, val)
                    cand_updated += 1
                else:
                    camp = Camp(**candidate_payload)
                    db.add(camp)
                    existing_by_id[rid] = camp
                    cand_inserted += 1

        counts["inserted"] += cand_inserted
        counts["updated"] += cand_updated
        print(
            f"Imported {cand_inserted} and updated {cand_updated} additional candidates from {CANDIDATES_FILE}"
        )

    db.commit()
    db.close()
    return counts


def main():
    parser = argparse.ArgumentParser(description="Import camp dossiers into the research-ui database")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'research.db'}"),
        help="SQLAlchemy database URL (default: local SQLite)",
    )
    args = parser.parse_args()

    print(f"Importing dossiers to: {args.db_url.split('@')[-1] if '@' in args.db_url else args.db_url}")
    counts = import_dossiers(args.db_url)
    print(f"\nDone! Inserted: {counts['inserted']}, Updated: {counts['updated']}, "
          f"Skipped: {counts['skipped']}, Errors: {counts['errors']}")


if __name__ == "__main__":
    main()
