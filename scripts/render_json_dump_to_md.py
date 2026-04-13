from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def slugify(value: str | None) -> str:
    if value is None:
        return "unknown"
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def country_folder(country: str | None) -> str:
    mapping = {
        "US": "us",
        "CA": "canada",
        "MX": "mexico",
    }
    return mapping.get((country or "").upper(), slugify(country))


def safe_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def yaml_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def yaml_list_block(key: str, values: list[str], indent: int = 0) -> str:
    pad = " " * indent
    if not values:
        return f"{pad}{key}: []"
    lines = [f"{pad}{key}:"]
    for item in values:
        lines.append(f"{pad}  - {item}")
    return "\n".join(lines)


def build_output_path(base_dir: Path, record: dict[str, Any]) -> Path:
    country = country_folder(record.get("country"))
    region = slugify(record.get("region") or "unk")
    name_slug = slugify(record.get("name"))
    city_slug = slugify(record.get("city") or "unknown-city")
    venue_slug = slugify(record.get("venue_name") or "unknown-venue")
    record_id = slugify(record.get("candidate_id") or f"{name_slug}-{city_slug}-{venue_slug}")
    filename = f"{name_slug}--{country}-{region}-{city_slug}-{venue_slug}--{record_id}.md"
    return base_dir / country / region / filename


def render_markdown(record: dict[str, Any]) -> str:
    record_id = slugify(record.get("candidate_id"))
    camp_id = slugify(record.get("name"))
    venue_id = slugify(
        f"{record.get('country', '')}-{record.get('region', '')}-{record.get('city', '')}-{record.get('venue_name', '')}"
    )

    program_family = safe_list(record.get("program_family"))
    camp_types = safe_list(record.get("camp_types"))
    notes = safe_list(record.get("notes"))
    validation_needs = safe_list(record.get("validation_needs"))

    priority_flags = record.get("priority_flags", {}) or {}
    duration_guess = record.get("duration_guess", {}) or {}

    lines = [
        "---",
        f"record_id: {record_id}",
        f"camp_id: {camp_id}",
        f"venue_id: {venue_id}",
        f"name: {record.get('name', '')}",
        f"display_name: {record.get('name', '')} at {record.get('venue_name', '')}",
        f"country: {record.get('country', '')}",
        f"region: {record.get('region', '') or ''}",
        f"city: {record.get('city', '') or ''}",
        f"venue_name: {record.get('venue_name', '')}",
        yaml_list_block("program_family", program_family),
        yaml_list_block("camp_types", camp_types),
        "priority_flags:",
        f"  college_precollege: {yaml_scalar(priority_flags.get('college_precollege'))}",
        f"  one_week_plus: {yaml_scalar(priority_flags.get('one_week_plus'))}",
        f"  high_iq_fit: {yaml_scalar(priority_flags.get('high_iq_fit'))}",
        f"  gt_core_program: {yaml_scalar(priority_flags.get('gt_core_program'))}",
        f"source_language_primary: {record.get('source_language', '') or ''}",
        f"activity_status: {record.get('activity_status_guess', '') or record.get('verification_state', '')}",
        "duration:",
        f"  label: {duration_guess.get('label', '') or ''}",
        f"  min_days: {yaml_scalar(duration_guess.get('min_days'))}",
        f"  max_days: {yaml_scalar(duration_guess.get('max_days'))}",
        "operator:",
        f"  name: {record.get('operator_name', '') or ''}",
        "website:",
        f"  canonical_url: {record.get('canonical_url', '') or ''}",
        "verification:",
        f"  verification_state: {record.get('verification_state', record.get('status', ''))}",
        "evidence:",
        f"  source_url: {record.get('canonical_url', '') or ''}",
        f"status: {record.get('status', '') or ''}",
        f"record_basis: {record.get('record_basis', '') or ''}",
        "---",
        "",
        f"# {record.get('name', '')}",
        "",
        "## Quick Take",
        f"{record.get('name', '')} is represented here as a starter record for further validation and enrichment.",
        "",
        "## Verified Facts",
        f"- Operator: {record.get('operator_name', '') or 'Unknown'}",
        f"- Venue: {record.get('venue_name', '') or 'Unknown'}",
        f"- Location: {record.get('city', '') or 'Unknown'}, {record.get('region', '') or ''}",
        f"- Canonical URL: {record.get('canonical_url', '') or ''}",
        "",
        "## Overnight Evidence",
        record.get("overnight_evidence_snippet", "") or record.get("evidence_summary", "") or "Not yet captured.",
        "",
        "## Recent Activity Evidence",
        record.get("recent_activity_evidence_snippet", "") or "Not yet captured.",
        "",
        "## Program Overview",
        f"Program family tags: {', '.join(program_family) if program_family else 'None yet'}",
        "",
        "## Session Length and Structure",
        f"Duration guess: {duration_guess.get('label', 'unknown')}",
        "",
        "## Pricing",
        record.get("pricing_summary", "") or "Pricing not yet captured.",
        "",
        "## Eligibility",
        record.get("eligibility_summary", "") or "Eligibility not yet captured.",
        "",
        "## Validation Needs",
    ]

    if validation_needs:
        for item in validation_needs:
            lines.append(f"- {item}")
    else:
        lines.append("- none listed")

    lines.extend(["", "## Notes"])
    if notes:
        for item in notes:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Sources",
        f"- {record.get('canonical_url', '') or ''}",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a JSON dump of camp/program records into Markdown files.")
    parser.add_argument("input_json", help="Path to JSON array input")
    parser.add_argument("--output-dir", default="camps", help="Base output directory for Markdown files")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_dir = Path(args.output_dir)

    records = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Input JSON must be a list of objects.")

    written = 0
    for record in records:
        out_path = build_output_path(output_dir, record)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_markdown(record), encoding="utf-8")
        written += 1

    print(f"Wrote {written} Markdown files to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
