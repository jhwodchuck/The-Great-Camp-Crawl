#!/usr/bin/env python3
"""Enrichment pipeline: extract structured enrichment from discovered candidates.

Reads data/staging/discovered-candidates.jsonl and produces per-type enrichment
JSONL files in data/enrichment/ following the schemas defined in
prompts/enrichment/01-05.

This is Phase 1 — deterministic extraction from existing discovery data.
No web fetching; all data comes from fields already captured during discovery.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Allow running from repo root or scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import read_jsonl, write_jsonl, ensure_parent, utc_now_iso


# ---------------------------------------------------------------------------
# Pricing enrichment
# ---------------------------------------------------------------------------

_CURRENCY_PATTERNS = [
    (r"(?:CAD|CA?\$)\s*[\d,]+", "CAD"),
    (r"(?:MXN|MX?\$)\s*[\d,]+", "MXN"),
    (r"(?:USD|US?\$)\s*[\d,]+", "USD"),
    (r"\$\s*[\d,]+", "USD"),  # bare $ defaults to USD
]

_PRICE_RE = re.compile(
    r"(?:CAD|CA\$|MXN|MX\$|USD|US\$|\$)\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_YEAR_RANGE = range(2020, 2035)


def _parse_amounts(text: str) -> list[float]:
    """Extract numeric amounts that appear next to currency symbols."""
    amounts: list[float] = []
    for m in _PRICE_RE.finditer(text):
        try:
            val = float(m.group(1).replace(",", ""))
            if val > 0 and int(val) not in _YEAR_RANGE:
                amounts.append(val)
        except ValueError:
            continue
    return sorted(set(amounts))


def _detect_currency(text: str) -> str | None:
    for pattern, currency in _CURRENCY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return currency
    return None


def enrich_pricing(candidate: dict) -> dict:
    cid = candidate.get("candidate_id", "")
    raw = candidate.get("raw_discovery_source", {})
    pricing_text = raw.get("pricing_summary") or ""
    evidence_snippet = pricing_text or None

    fields = {
        "currency": None,
        "amount_min": None,
        "amount_max": None,
        "boarding_included": None,
        "deposit_amount": None,
        "fees_text": None,
        "pricing_url": None,
    }

    if not pricing_text:
        return _enrichment_result(cid, "pricing", "missing", "low", fields, evidence_snippet)

    currency = _detect_currency(pricing_text)
    amounts = _parse_amounts(pricing_text)

    # Filter out unreasonably small amounts (likely deposits or fees, not tuition)
    tuition_amounts = [a for a in amounts if a >= 50]

    if not tuition_amounts:
        return _enrichment_result(cid, "pricing", "partial", "low", {
            **fields, "currency": currency
        }, evidence_snippet, notes="Amounts found but could not confidently identify tuition range.")

    fields["currency"] = currency
    fields["amount_min"] = min(tuition_amounts)
    fields["amount_max"] = max(tuition_amounts)
    fields["pricing_url"] = candidate.get("canonical_url")

    # Check for boarding-included signals
    boarding_keywords = ["all-inclusive", "including", "includes", "boarding", "accommodation", "meals", "housing", "lodging"]
    if any(kw in pricing_text.lower() for kw in boarding_keywords):
        fields["boarding_included"] = True

    # Check for fully funded
    if "fully funded" in pricing_text.lower() or "scholarship" in pricing_text.lower():
        fields["fees_text"] = pricing_text

    status = "found" if currency and tuition_amounts else "partial"
    confidence = "high" if currency and len(tuition_amounts) >= 1 else "medium"

    return _enrichment_result(cid, "pricing", status, confidence, fields, evidence_snippet)


# ---------------------------------------------------------------------------
# Duration enrichment
# ---------------------------------------------------------------------------

def enrich_duration(candidate: dict) -> dict:
    cid = candidate.get("candidate_id", "")
    raw = candidate.get("raw_discovery_source", {})
    duration_guess = candidate.get("duration_guess") or raw.get("duration_guess") or {}
    priority_flags = candidate.get("priority_flags") or raw.get("priority_flags") or {}

    label = duration_guess.get("label") or ""
    min_days = duration_guess.get("min_days")
    max_days = duration_guess.get("max_days")
    one_week_plus = priority_flags.get("one_week_plus", False)

    fields = {
        "min_days": min_days,
        "max_days": max_days,
        "session_model": None,
        "one_week_plus": one_week_plus if one_week_plus else None,
        "duration_text": label if label else None,
    }

    # Try to derive one_week_plus from min_days
    if min_days is not None and min_days >= 7:
        fields["one_week_plus"] = True
    elif max_days is not None and max_days >= 7:
        fields["one_week_plus"] = True

    # Infer session model from label
    label_lower = label.lower()
    if any(kw in label_lower for kw in ["varies", "multiple", "session length varies"]):
        fields["session_model"] = "multiple_sessions"
    elif any(kw in label_lower for kw in ["1 week", "one week", "7 days", "8 days"]):
        fields["session_model"] = "weekly"
    elif any(kw in label_lower for kw in ["2 week", "two week", "14 days"]):
        fields["session_model"] = "two_week"
    elif any(kw in label_lower for kw in ["3 week", "three week", "21 days"]):
        fields["session_model"] = "three_week"
    elif any(kw in label_lower for kw in ["4 week", "four week", "28 days", "~27 days", "month"]):
        fields["session_model"] = "month"
    elif any(kw in label_lower for kw in ["6 week", "six week", "42 days"]):
        fields["session_model"] = "six_week"
    elif "boarding" in label_lower or "course-based" in label_lower:
        fields["session_model"] = "course_based"

    # Determine status
    if min_days is not None or max_days is not None:
        status = "found"
        confidence = "high" if min_days and max_days else "medium"
    elif label and label not in ("unknown", "not applicable", "session length not extracted in this pass",
                                  "session length varies", "residential college preparatory experience",
                                  "boarding summer program", "summer program length not captured in this pass"):
        status = "partial"
        confidence = "low"
    else:
        status = "missing"
        confidence = "low"

    evidence = label if label else None
    return _enrichment_result(cid, "duration", status, confidence, fields, evidence)


# ---------------------------------------------------------------------------
# Age/Grade enrichment
# ---------------------------------------------------------------------------

_AGE_RANGE_RE = re.compile(r"ages?\s*(\d{1,2})\s*[-–to]+\s*(\d{1,2})", re.IGNORECASE)
_GRADE_RANGE_RE = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:[-–]|through|to)\s*(\d{1,2})(?:st|nd|rd|th)?\s*grade",
    re.IGNORECASE,
)
_GRADE_SINGLE_RE = re.compile(
    r"(?:grade|gr\.?)\s*(\d{1,2})", re.IGNORECASE,
)
_AUDIENCE_AGE_MAP = {
    "elementary": (5, 11),
    "middle-school": (11, 14),
    "high-school": (14, 18),
    "elementary-middle-school": (5, 14),
    "middle-school-high-school": (11, 18),
    "elementary-middle-school-high-school": (5, 18),
    "gifted-middle-school": (11, 14),
}


def enrich_age_grade(candidate: dict) -> dict:
    cid = candidate.get("candidate_id", "")
    raw = candidate.get("raw_discovery_source", {})
    eligibility = raw.get("eligibility_summary") or ""
    audience = raw.get("audience_type") or ""

    fields = {
        "age_min": None,
        "age_max": None,
        "grade_min": None,
        "grade_max": None,
        "eligibility_text": eligibility if eligibility else None,
    }

    # Try to extract age range
    age_match = _AGE_RANGE_RE.search(eligibility)
    if age_match:
        fields["age_min"] = int(age_match.group(1))
        fields["age_max"] = int(age_match.group(2))

    # Try to extract grade range
    grade_match = _GRADE_RANGE_RE.search(eligibility)
    if grade_match:
        fields["grade_min"] = int(grade_match.group(1))
        fields["grade_max"] = int(grade_match.group(2))
    else:
        # Look for individual grade mentions
        grade_singles = _GRADE_SINGLE_RE.findall(eligibility)
        if grade_singles:
            grades = sorted(int(g) for g in grade_singles)
            fields["grade_min"] = grades[0]
            fields["grade_max"] = grades[-1]
        else:
            # Look for patterns like "7th- and 8th-grade"
            ordinal_match = re.search(
                r"(\d{1,2})(?:st|nd|rd|th)?[-\s]+(?:and\s+)?(\d{1,2})(?:st|nd|rd|th)?[-\s]*grade",
                eligibility, re.IGNORECASE,
            )
            if ordinal_match:
                fields["grade_min"] = int(ordinal_match.group(1))
                fields["grade_max"] = int(ordinal_match.group(2))

    # Fall back to audience_type mapping if no age found
    if fields["age_min"] is None and audience:
        age_range = _AUDIENCE_AGE_MAP.get(audience)
        if age_range:
            fields["age_min"], fields["age_max"] = age_range

    # Check for "rising seniors", "entering junior or senior year" style text
    if eligibility:
        if re.search(r"rising\s+senior|entering\s+(?:their\s+)?senior\s+year", eligibility, re.IGNORECASE):
            if fields["grade_min"] is None:
                fields["grade_min"] = 12
                fields["grade_max"] = 12
        elif re.search(r"entering\s+(?:their\s+)?junior\s+or\s+senior\s+year", eligibility, re.IGNORECASE):
            if fields["grade_min"] is None:
                fields["grade_min"] = 11
                fields["grade_max"] = 12
        elif re.search(r"finishing\s+10th\s+or\s+11th\s+grade", eligibility, re.IGNORECASE):
            if fields["grade_min"] is None:
                fields["grade_min"] = 10
                fields["grade_max"] = 11

    # Determine status
    has_age = fields["age_min"] is not None
    has_grade = fields["grade_min"] is not None
    has_text = bool(eligibility)

    if has_age or has_grade:
        status = "found"
        confidence = "high" if has_age else "medium"
    elif has_text:
        status = "partial"
        confidence = "low"
    else:
        status = "missing"
        confidence = "low"

    return _enrichment_result(cid, "age_grade", status, confidence, fields,
                              eligibility if eligibility else None)


# ---------------------------------------------------------------------------
# Contact enrichment
# ---------------------------------------------------------------------------

def enrich_contact(candidate: dict) -> dict:
    cid = candidate.get("candidate_id", "")
    raw = candidate.get("raw_discovery_source", {})
    canonical_url = candidate.get("canonical_url") or raw.get("canonical_url")
    operator_name = candidate.get("operator_name") or raw.get("operator_name")

    fields = {
        "contact_email": None,
        "contact_phone": None,
        "inquiry_url": canonical_url,
        "operator_name": operator_name,
    }

    # For Phase 1 we can only populate inquiry_url and operator_name
    # Email and phone require web fetching (Phase 2)
    if canonical_url and operator_name:
        status = "partial"
        confidence = "medium"
    elif canonical_url or operator_name:
        status = "partial"
        confidence = "low"
    else:
        status = "missing"
        confidence = "low"

    return _enrichment_result(cid, "contact", status, confidence, fields,
                              None, notes="Email and phone require web fetch in Phase 2.")


# ---------------------------------------------------------------------------
# Taxonomy enrichment
# ---------------------------------------------------------------------------

_STANDARD_PROGRAM_FAMILIES = {
    "college-pre-college", "academic", "stem", "sports", "arts", "music",
    "wilderness", "faith-based", "family", "adventure", "leadership",
    "humanities", "science", "engineering", "research", "computing",
    "math", "debate", "gifted-talented",
}

_STANDARD_CAMP_TYPES = {
    "overnight", "residential", "residential-academic", "retreat",
    "research-program", "program-dependent",
}


def enrich_taxonomy(candidate: dict) -> dict:
    cid = candidate.get("candidate_id", "")
    raw = candidate.get("raw_discovery_source", {})

    program_family_raw = candidate.get("program_family") or raw.get("program_family") or []
    camp_types_raw = candidate.get("camp_types") or raw.get("camp_types") or []

    # Normalize tags — keep only recognized standard tags
    program_family_tags = sorted(set(
        tag for tag in program_family_raw
        if tag in _STANDARD_PROGRAM_FAMILIES
    ))
    camp_type_tags = sorted(set(
        tag for tag in camp_types_raw
        if tag in _STANDARD_CAMP_TYPES
    ))

    # Also include unrecognized tags as-is (they may be valid specialties)
    extra_program = sorted(set(
        tag for tag in program_family_raw
        if tag not in _STANDARD_PROGRAM_FAMILIES and tag != "institutional-lead" and tag != "unspecified"
    ))
    program_family_tags.extend(extra_program)

    fields = {
        "program_family_tags": program_family_tags,
        "camp_type_tags": camp_type_tags,
    }

    if program_family_tags or camp_type_tags:
        status = "found"
        confidence = "high" if program_family_tags and camp_type_tags else "medium"
    else:
        status = "missing"
        confidence = "low"

    return _enrichment_result(cid, "taxonomy", status, confidence, fields, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enrichment_result(
    candidate_id: str,
    enrichment_type: str,
    status: str,
    confidence: str,
    fields: dict,
    evidence_snippet: str | None,
    notes: str | None = None,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "enrichment_type": enrichment_type,
        "status": status,
        "confidence": confidence,
        "fields": fields,
        "evidence": {
            "snippet": evidence_snippet,
            "url": None,
            "date_text": None,
        },
        "notes": notes,
        "validation_needs": [],
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

ENRICHERS = [
    ("pricing", enrich_pricing),
    ("duration", enrich_duration),
    ("age_grade", enrich_age_grade),
    ("contact", enrich_contact),
    ("taxonomy", enrich_taxonomy),
]


def run_pipeline(input_path: Path, output_dir: Path, limit: int | None = None) -> dict:
    candidates = read_jsonl(input_path)
    if limit:
        candidates = candidates[:limit]

    print(f"Loaded {len(candidates)} candidates from {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {
        "run_timestamp": utc_now_iso(),
        "input_file": str(input_path),
        "total_candidates": len(candidates),
        "enrichment_types": {},
    }

    for etype, enricher_fn in ENRICHERS:
        results = []
        status_counts: dict[str, int] = {}
        confidence_counts: dict[str, int] = {}

        for candidate in candidates:
            result = enricher_fn(candidate)
            results.append(result)

            s = result["status"]
            c = result["confidence"]
            status_counts[s] = status_counts.get(s, 0) + 1
            confidence_counts[c] = confidence_counts.get(c, 0) + 1

        out_path = output_dir / f"{etype}_enrichment.jsonl"
        write_jsonl(out_path, results)
        print(f"  {etype}: {len(results)} results → {out_path}")
        print(f"    Status: {json.dumps(status_counts)}")
        print(f"    Confidence: {json.dumps(confidence_counts)}")

        summary["enrichment_types"][etype] = {
            "total": len(results),
            "output_file": str(out_path),
            "status_counts": status_counts,
            "confidence_counts": confidence_counts,
        }

    # Write summary
    summary_path = output_dir / "enrichment_summary.json"
    ensure_parent(summary_path)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSummary → {summary_path}")

    # Generate follow-up queue for candidates needing web fetch
    followup = _build_followup_queue(candidates, output_dir)
    followup_path = output_dir / "enrichment_followup_queue.jsonl"
    write_jsonl(followup_path, followup)
    print(f"Follow-up queue: {len(followup)} candidates need web-fetched enrichment → {followup_path}")

    summary["followup_count"] = len(followup)
    # Re-write summary with followup count
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def _build_followup_queue(candidates: list[dict], output_dir: Path) -> list[dict]:
    """Identify candidates that need web-fetched enrichment."""
    # Read all enrichment results by candidate_id
    enrichment_by_cid: dict[str, dict[str, dict]] = {}
    for etype, _ in ENRICHERS:
        path = output_dir / f"{etype}_enrichment.jsonl"
        for row in read_jsonl(path):
            cid = row["candidate_id"]
            if cid not in enrichment_by_cid:
                enrichment_by_cid[cid] = {}
            enrichment_by_cid[cid][etype] = row

    followup: list[dict] = []
    for candidate in candidates:
        cid = candidate.get("candidate_id", "")
        cid_enrichments = enrichment_by_cid.get(cid, {})

        missing_types = []
        for etype in ["pricing", "duration", "age_grade", "contact"]:
            result = cid_enrichments.get(etype, {})
            if result.get("status") in ("missing", None):
                missing_types.append(etype)

        if missing_types:
            followup.append({
                "candidate_id": cid,
                "canonical_url": candidate.get("canonical_url"),
                "name": candidate.get("name"),
                "missing_enrichment_types": missing_types,
                "status": "enrichment_followup_needed",
            })

    return followup


def main():
    parser = argparse.ArgumentParser(description="Run enrichment pipeline on discovered candidates")
    parser.add_argument(
        "--input", "-i",
        default="data/staging/discovered-candidates.jsonl",
        help="Path to discovered candidates JSONL (default: data/staging/discovered-candidates.jsonl)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="data/enrichment",
        help="Output directory for enrichment results (default: data/enrichment)",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        help="Limit number of candidates to process (for testing)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    summary = run_pipeline(input_path, output_dir, limit=args.limit)
    print(f"\nDone. Processed {summary['total_candidates']} candidates across {len(summary['enrichment_types'])} enrichment types.")


if __name__ == "__main__":
    main()
