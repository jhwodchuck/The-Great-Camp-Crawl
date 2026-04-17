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

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Allow importing from the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "research-ui" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from models import Base, Camp, CampSource  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPS_DIR = REPO_ROOT / "camps"
CANDIDATES_FILE = REPO_ROOT / "data" / "staging" / "discovered-candidates.jsonl"

# Regex to split YAML frontmatter from markdown body
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


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


def import_dossiers(db_url: str) -> dict:
    """Import all dossiers and return counts."""
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

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

        existing = db.query(Camp).filter(Camp.record_id == rid).first()
        if existing:
            for key, val in data.items():
                if key != "record_id":
                    setattr(existing, key, val)
            counts["updated"] += 1
        else:
            db.add(Camp(**data))
            counts["inserted"] += 1

    # Phase 2: Import candidates not yet rendered as dossiers
    if CANDIDATES_FILE.exists():
        cand_count = 0
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
                rid = cand.get("record_id")
                if not rid or rid in seen_record_ids:
                    continue
                seen_record_ids.add(rid)

                existing = db.query(Camp).filter(Camp.record_id == rid).first()
                if existing:
                    continue

                name = cand.get("name") or cand.get("display_name") or cand.get("camp_name")
                if not name:
                    continue

                program_family = cand.get("program_family")
                camp_types = cand.get("camp_types")
                pricing = cand.get("pricing", {}) or {}
                ages = cand.get("ages", {}) or {}
                duration = cand.get("duration", {}) or {}
                contact = cand.get("contact", {}) or {}
                website = cand.get("website", {}) or {}

                camp = Camp(
                    record_id=rid,
                    name=name,
                    display_name=cand.get("display_name"),
                    country=cand.get("country"),
                    region=cand.get("region"),
                    city=cand.get("city"),
                    venue_name=cand.get("venue_name"),
                    program_family=json.dumps(program_family) if isinstance(program_family, list) else None,
                    camp_types=json.dumps(camp_types) if isinstance(camp_types, list) else None,
                    website_url=website.get("canonical_url") or cand.get("website_url"),
                    ages_min=_safe_int(ages.get("min")),
                    ages_max=_safe_int(ages.get("max")),
                    pricing_currency=pricing.get("currency"),
                    pricing_min=_safe_float(pricing.get("amount_min")),
                    pricing_max=_safe_float(pricing.get("amount_max")),
                    overnight_confirmed=cand.get("overnight_confirmed"),
                    draft_status="candidate",
                    source=CampSource.discovery_pipeline,
                )
                db.add(camp)
                cand_count += 1

        counts["inserted"] += cand_count
        print(f"Imported {cand_count} additional candidates from {CANDIDATES_FILE}")

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
