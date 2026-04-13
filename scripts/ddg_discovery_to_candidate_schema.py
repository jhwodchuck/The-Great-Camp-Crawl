from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PROGRAM_FAMILY_RULES: list[tuple[str, str]] = [
    ("pre-college", "college-pre-college"),
    ("precollege", "college-pre-college"),
    ("academic", "academic"),
    ("engineering", "stem"),
    ("robotics", "stem"),
    ("coding", "stem"),
    ("music", "music"),
    ("band", "music"),
    ("arts", "arts"),
    ("sport", "sports"),
    ("wilderness", "wilderness"),
    ("family", "family"),
    ("church", "faith-based"),
    ("faith", "faith-based"),
]


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def infer_program_family(text: str) -> list[str]:
    tags: list[str] = []
    haystack = text.lower()
    for needle, tag in PROGRAM_FAMILY_RULES:
        if needle in haystack and tag not in tags:
            tags.append(tag)
    if not tags:
        tags.append("unspecified")
    return tags


def infer_camp_types(text: str) -> list[str]:
    haystack = text.lower()
    out: list[str] = []
    if "overnight" in haystack:
        out.append("overnight")
    if "residential" in haystack:
        out.append("residential")
    if "on campus" in haystack or "dorm" in haystack or "boarding" in haystack:
        out.append("residential-academic")
    if not out:
        out.append("unknown")
    return list(dict.fromkeys(out))


def infer_duration(text: str) -> dict[str, Any]:
    haystack = text.lower()
    patterns = [
        (r"(one|1)[- ]week", "one-week", 7, 7),
        (r"(two|2)[- ]week", "two-week", 14, 14),
        (r"(three|3)[- ]week", "three-week", 21, 21),
        (r"(four|4)[- ]week", "four-week", 28, 28),
        (r"(five|5)[- ]week", "five-week", 35, 35),
    ]
    for pattern, label, min_days, max_days in patterns:
        if re.search(pattern, haystack):
            return {"label": label, "min_days": min_days, "max_days": max_days}
    if "week" in haystack:
        return {"label": "week-based", "min_days": 7, "max_days": None}
    return {"label": "unknown", "min_days": None, "max_days": None}


def infer_priority(program_family: list[str], duration_guess: dict[str, Any]) -> dict[str, bool]:
    return {
        "college_precollege": "college-pre-college" in program_family,
        "one_week_plus": (duration_guess.get("min_days") or 0) >= 7,
    }


def build_candidate_id(country: str, region: str, title: str, url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return slugify(f"cand-{country}-{region}-{title}-{host}")


def normalize_record(record: dict[str, Any], country: str, region: str, city: str | None, venue_name: str | None) -> dict[str, Any]:
    text = " ".join(
        str(record.get(key, ""))
        for key in ("title", "snippet", "query")
    )
    program_family = infer_program_family(text)
    camp_types = infer_camp_types(text)
    duration_guess = infer_duration(text)
    title = record.get("title") or record.get("url") or "unknown-candidate"
    return {
        "candidate_id": build_candidate_id(country, region, title, record.get("url", "")),
        "record_basis": "venue_candidate_pending_confirmation",
        "name": title,
        "operator_name": None,
        "venue_name": venue_name or "venue to be confirmed",
        "city": city,
        "region": region,
        "country": country,
        "canonical_url": record.get("url"),
        "source_language": None,
        "program_family": program_family,
        "camp_types": camp_types,
        "priority_flags": infer_priority(program_family, duration_guess),
        "activity_status_guess": "unknown",
        "duration_guess": duration_guess,
        "overnight_evidence_snippet": record.get("snippet"),
        "recent_activity_evidence_snippet": None,
        "validation_needs": ["confirm_overnight", "confirm_recent_activity", "confirm_exact_venue", "pricing", "ages_or_grades", "contact"],
        "notes": [f"Normalized from DuckDuckGo discovery query: {record.get('query', '')}"],
        "status": "discovered",
        "raw_discovery_source": record,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize DDG discovery JSONL into repo candidate schema")
    parser.add_argument("input_jsonl")
    parser.add_argument("--output", required=True)
    parser.add_argument("--country", default="US")
    parser.add_argument("--region", default="UNK")
    parser.add_argument("--city")
    parser.add_argument("--venue-name")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input_jsonl))
    normalized = [normalize_record(r, args.country, args.region, args.city, args.venue_name) for r in rows]
    write_jsonl(Path(args.output), normalized)
    print(f"Wrote {len(normalized)} normalized candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
