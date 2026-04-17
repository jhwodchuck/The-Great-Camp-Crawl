"""Pragmatic runtime schema patching for deployed databases without migrations."""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


_CAMP_COLUMN_PATCHES = {
    "is_excluded": "ALTER TABLE camps ADD COLUMN is_excluded BOOLEAN",
    "exclusion_reason": "ALTER TABLE camps ADD COLUMN exclusion_reason VARCHAR(128)",
    "exclusion_notes": "ALTER TABLE camps ADD COLUMN exclusion_notes TEXT",
    "excluded_at": "ALTER TABLE camps ADD COLUMN excluded_at TIMESTAMP",
    "excluded_by_user_id": "ALTER TABLE camps ADD COLUMN excluded_by_user_id INTEGER",
    "triage_verdict": "ALTER TABLE camps ADD COLUMN triage_verdict VARCHAR(32)",
    "triage_confidence": "ALTER TABLE camps ADD COLUMN triage_confidence VARCHAR(16)",
    "triage_reason": "ALTER TABLE camps ADD COLUMN triage_reason TEXT",
    "triaged_at": "ALTER TABLE camps ADD COLUMN triaged_at TIMESTAMPTZ",
    "triage_model": "ALTER TABLE camps ADD COLUMN triage_model VARCHAR(128)",
    "enriched_at": "ALTER TABLE camps ADD COLUMN enriched_at TIMESTAMPTZ",
    "enrichment_model": "ALTER TABLE camps ADD COLUMN enrichment_model VARCHAR(128)",
    "enrichment_source_file": "ALTER TABLE camps ADD COLUMN enrichment_source_file VARCHAR(512)",
}


def ensure_runtime_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "camps" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("camps")}
    missing = [
        statement
        for column_name, statement in _CAMP_COLUMN_PATCHES.items()
        if column_name not in existing_columns
    ]
    if not missing:
        return

    with engine.begin() as conn:
        for statement in missing:
            conn.execute(text(statement))
