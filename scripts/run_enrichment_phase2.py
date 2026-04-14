#!/usr/bin/env python3
"""Phase 2 enrichment: web-fetch + extract from official program pages.

Reads the follow-up queue produced by Phase 1 and fetches each candidate's
canonical URL.  Extracts pricing, duration, age/grade, and contact data from
the page content, then merges with Phase 1 results.

Uses the existing capture_pipeline infrastructure (with caching) so pages
already in data/raw/evidence-pages/ are not re-fetched.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import read_jsonl, write_jsonl, ensure_parent, utc_now_iso, parse_frontmatter_document
from lib.capture_pipeline import capture_urls
from lib.url_utils import stable_capture_stem


# ---------------------------------------------------------------------------
# Page content extractors
# ---------------------------------------------------------------------------

_PRICE_RE = re.compile(
    r"(?:CAD|CA\$|MXN|MX\$|USD|US\$|\$)\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_YEAR_RANGE = range(2020, 2035)

_CURRENCY_PATTERNS = [
    (r"(?:CAD|CA\$)\s*[\d,]+", "CAD"),
    (r"(?:MXN|MX\$)\s*[\d,]+", "MXN"),
    (r"(?:USD|US\$)\s*[\d,]+", "USD"),
    (r"\$\s*[\d,]+", "USD"),
]

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
    r"|(?:\+\d{1,3}[\s.-]?)?\d[\d\s.\-()]{7,14}\d"
)

_AGE_RANGE_RE = re.compile(r"ages?\s*(\d{1,2})\s*[-–to]+\s*(\d{1,2})", re.IGNORECASE)
_GRADE_RANGE_RE = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:[-–]|through|to)\s*(\d{1,2})(?:st|nd|rd|th)?\s*grade",
    re.IGNORECASE,
)
_GRADE_SINGLE_RE = re.compile(r"(?:grade|gr\.?)\s*(\d{1,2})", re.IGNORECASE)

_DURATION_DAYS_RE = re.compile(r"(\d{1,3})\s*(?:day|night)", re.IGNORECASE)
_DURATION_WEEKS_RE = re.compile(r"(\d{1,2})\s*[-\s]?week", re.IGNORECASE)


def _detect_currency(text: str) -> str | None:
    for pattern, currency in _CURRENCY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return currency
    return None


def _parse_price_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    for m in _PRICE_RE.finditer(text):
        try:
            val = float(m.group(1).replace(",", ""))
            if val > 0 and int(val) not in _YEAR_RANGE:
                amounts.append(val)
        except ValueError:
            continue
    return sorted(set(amounts))


def _extract_snippet(text: str, keyword: str, context: int = 200) -> str | None:
    """Extract a short snippet around a keyword occurrence."""
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return None
    start = max(0, idx - context // 2)
    end = min(len(text), idx + len(keyword) + context // 2)
    snippet = text[start:end].strip()
    # Clean up to sentence boundaries where possible
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def extract_pricing_from_text(text: str, url: str) -> dict | None:
    """Try to extract pricing data from page markdown content."""
    # Look for pricing-related sections
    pricing_keywords = ["tuition", "cost", "price", "fee", "rate", "registration",
                        "pricing", "payment", "invest", "tarifa", "costo", "precio"]

    relevant_text = text
    # Try to find pricing-specific sections
    for kw in pricing_keywords:
        if kw.lower() in text.lower():
            snippet = _extract_snippet(text, kw, context=600)
            if snippet:
                relevant_text = snippet
                break

    currency = _detect_currency(relevant_text) or _detect_currency(text)
    amounts = _parse_price_amounts(relevant_text)
    if not amounts:
        amounts = _parse_price_amounts(text)

    tuition_amounts = [a for a in amounts if a >= 50]
    if not tuition_amounts:
        return None

    boarding_keywords = ["all-inclusive", "including", "includes", "boarding",
                         "accommodation", "meals", "housing", "lodging",
                         "room and board", "room & board"]
    boarding_included = any(kw in text.lower() for kw in boarding_keywords) or None

    evidence = _extract_snippet(text, "$", context=300)

    return {
        "currency": currency,
        "amount_min": min(tuition_amounts),
        "amount_max": max(tuition_amounts),
        "boarding_included": boarding_included,
        "deposit_amount": None,
        "fees_text": None,
        "pricing_url": url,
        "_evidence_snippet": evidence,
    }


def extract_duration_from_text(text: str) -> dict | None:
    """Try to extract duration data from page markdown content."""
    weeks = _DURATION_WEEKS_RE.findall(text)
    days = _DURATION_DAYS_RE.findall(text)

    if not weeks and not days:
        return None

    week_vals = sorted(set(int(w) for w in weeks if 1 <= int(w) <= 12))
    day_vals = sorted(set(int(d) for d in days if 1 <= int(d) <= 60))

    min_days = None
    max_days = None

    if day_vals:
        min_days = min(day_vals)
        max_days = max(day_vals)

    if week_vals:
        week_min_days = min(week_vals) * 7
        week_max_days = max(week_vals) * 7
        if min_days is None or week_min_days < min_days:
            min_days = week_min_days
        if max_days is None or week_max_days > max_days:
            max_days = week_max_days

    one_week_plus = (min_days is not None and min_days >= 7) or (max_days is not None and max_days >= 7)

    duration_text_parts = []
    if week_vals:
        duration_text_parts.append(f"{min(week_vals)}-{max(week_vals)} weeks" if len(week_vals) > 1 else f"{week_vals[0]} week(s)")
    if day_vals:
        duration_text_parts.append(f"{min(day_vals)}-{max(day_vals)} days" if len(day_vals) > 1 else f"{day_vals[0]} day(s)")

    return {
        "min_days": min_days,
        "max_days": max_days,
        "session_model": None,
        "one_week_plus": one_week_plus or None,
        "duration_text": "; ".join(duration_text_parts) if duration_text_parts else None,
    }


def extract_age_grade_from_text(text: str) -> dict | None:
    """Try to extract age/grade data from page markdown content."""
    fields: dict[str, Any] = {
        "age_min": None, "age_max": None,
        "grade_min": None, "grade_max": None,
        "eligibility_text": None,
    }

    # Extract age ranges
    age_matches = _AGE_RANGE_RE.findall(text)
    if age_matches:
        ages = []
        for amin, amax in age_matches:
            a1, a2 = int(amin), int(amax)
            if 3 <= a1 <= 25 and 3 <= a2 <= 25:
                ages.extend([a1, a2])
        if ages:
            fields["age_min"] = min(ages)
            fields["age_max"] = max(ages)

    # Extract grade ranges
    grade_matches = _GRADE_RANGE_RE.findall(text)
    if grade_matches:
        grades = []
        for gmin, gmax in grade_matches:
            g1, g2 = int(gmin), int(gmax)
            if 1 <= g1 <= 12 and 1 <= g2 <= 12:
                grades.extend([g1, g2])
        if grades:
            fields["grade_min"] = min(grades)
            fields["grade_max"] = max(grades)
    else:
        grade_singles = _GRADE_SINGLE_RE.findall(text)
        if grade_singles:
            grades = sorted(int(g) for g in grade_singles if 1 <= int(g) <= 12)
            if grades:
                fields["grade_min"] = grades[0]
                fields["grade_max"] = grades[-1]

    # Check for rising senior / entering junior patterns
    if fields["grade_min"] is None:
        if re.search(r"rising\s+senior|entering\s+(?:their\s+)?senior\s+year", text, re.IGNORECASE):
            fields["grade_min"] = 12
            fields["grade_max"] = 12
        elif re.search(r"entering\s+(?:their\s+)?junior\s+or\s+senior\s+year", text, re.IGNORECASE):
            fields["grade_min"] = 11
            fields["grade_max"] = 12
        elif re.search(r"(?:9|9th).*(?:12|12th)\s*grade", text, re.IGNORECASE):
            fields["grade_min"] = 9
            fields["grade_max"] = 12

    if fields["age_min"] is None and fields["grade_min"] is None:
        return None

    # Extract a brief eligibility snippet
    age_snippet = _extract_snippet(text, "age", context=200) if "age" in text.lower() else None
    grade_snippet = _extract_snippet(text, "grade", context=200) if "grade" in text.lower() else None
    fields["eligibility_text"] = age_snippet or grade_snippet

    return fields


def extract_contact_from_text(text: str, url: str) -> dict | None:
    """Try to extract contact data from page markdown content."""
    emails = _EMAIL_RE.findall(text)
    phones = _PHONE_RE.findall(text)

    # Filter out common non-contact emails
    filtered_emails = [
        e for e in emails
        if not any(skip in e.lower() for skip in [
            "example.com", "sentry", "webpack", "schema.org",
            "noreply", "no-reply", "donotreply", ".png", ".jpg",
            "placeholder", "test@", "wixpress",
        ])
    ]

    # Filter phone numbers — keep only plausible ones
    filtered_phones = []
    for p in phones:
        digits = re.sub(r"\D", "", p)
        if 10 <= len(digits) <= 15:
            filtered_phones.append(p.strip())

    if not filtered_emails and not filtered_phones:
        return None

    return {
        "contact_email": filtered_emails[0] if filtered_emails else None,
        "contact_phone": filtered_phones[0] if filtered_phones else None,
        "inquiry_url": url,
        "operator_name": None,  # kept from Phase 1
    }


# ---------------------------------------------------------------------------
# Core enrichment result builder
# ---------------------------------------------------------------------------

def _enrichment_result(
    candidate_id: str,
    enrichment_type: str,
    status: str,
    confidence: str,
    fields: dict,
    evidence_snippet: str | None,
    evidence_url: str | None = None,
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
            "url": evidence_url,
            "date_text": None,
        },
        "notes": notes,
        "validation_needs": [],
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def fetch_and_read_page(url: str, text_dir: Path, html_dir: Path, manifest_path: Path) -> str | None:
    """Fetch a URL (or read from cache) and return its markdown text."""
    # Check if already captured
    stem = stable_capture_stem(url)
    cached_path = text_dir / f"{stem}.md"
    if cached_path.exists():
        raw = cached_path.read_text(encoding="utf-8")
        _, body = parse_frontmatter_document(raw)
        return body

    # Fetch
    result = capture_urls(
        urls=[url],
        text_dir=text_dir,
        html_dir=html_dir,
        manifest_path=manifest_path,
        timeout=20,
        retries=2,
        backoff_seconds=1.0,
        skip_existing=True,
    )
    row = result["manifest"][0]
    if row["status"] in ("captured", "unchanged", "skipped_existing") and row.get("markdown_path"):
        md_path = Path(row["markdown_path"])
        if md_path.exists():
            raw = md_path.read_text(encoding="utf-8")
            _, body = parse_frontmatter_document(raw)
            return body
    return None


def run_phase2(
    followup_path: Path,
    phase1_dir: Path,
    output_dir: Path,
    text_dir: Path,
    html_dir: Path,
    manifest_path: Path,
    limit: int | None = None,
    batch_sleep: float = 0.5,
) -> dict:
    queue = read_jsonl(followup_path)
    if limit:
        queue = queue[:limit]

    print(f"Phase 2: {len(queue)} candidates from {followup_path}")

    # Load Phase 1 results indexed by candidate_id
    phase1: dict[str, dict[str, dict]] = {}
    for etype in ["pricing", "duration", "age_grade", "contact", "taxonomy"]:
        path = phase1_dir / f"{etype}_enrichment.jsonl"
        for row in read_jsonl(path):
            cid = row["candidate_id"]
            if cid not in phase1:
                phase1[cid] = {}
            phase1[cid][etype] = row

    output_dir.mkdir(parents=True, exist_ok=True)

    # Track results
    updated: dict[str, list[dict]] = {
        "pricing": [], "duration": [], "age_grade": [], "contact": [],
    }
    fetch_stats = {"fetched": 0, "cached": 0, "failed": 0, "upgraded": 0}

    for i, item in enumerate(queue):
        cid = item["candidate_id"]
        url = item.get("canonical_url")
        missing = item.get("missing_enrichment_types", [])
        name = item.get("name", cid)

        if not url:
            print(f"  [{i+1}/{len(queue)}] {name}: no URL, skipping")
            fetch_stats["failed"] += 1
            continue

        # Check if page is already cached
        stem = stable_capture_stem(url)
        already_cached = (text_dir / f"{stem}.md").exists()

        if i > 0 and not already_cached:
            time.sleep(batch_sleep)

        page_text = fetch_and_read_page(url, text_dir, html_dir, manifest_path)

        if page_text is None:
            print(f"  [{i+1}/{len(queue)}] {name}: fetch failed")
            fetch_stats["failed"] += 1
            continue

        if already_cached:
            fetch_stats["cached"] += 1
        else:
            fetch_stats["fetched"] += 1

        candidate_upgraded = False

        # Try pricing extraction
        if "pricing" in missing:
            p1 = phase1.get(cid, {}).get("pricing", {})
            if p1.get("status") in ("missing", "partial"):
                pricing = extract_pricing_from_text(page_text, url)
                if pricing:
                    evidence_snippet = pricing.pop("_evidence_snippet", None)
                    result = _enrichment_result(
                        cid, "pricing", "found", "medium", pricing,
                        evidence_snippet, evidence_url=url,
                        notes="Extracted from web-fetched page in Phase 2.",
                    )
                    updated["pricing"].append(result)
                    candidate_upgraded = True

        # Try duration extraction
        if "duration" in missing:
            p1 = phase1.get(cid, {}).get("duration", {})
            if p1.get("status") in ("missing", "partial"):
                duration = extract_duration_from_text(page_text)
                if duration:
                    snippet = _extract_snippet(page_text, "week", context=200) or _extract_snippet(page_text, "day", context=200)
                    result = _enrichment_result(
                        cid, "duration", "found", "medium", duration,
                        snippet, evidence_url=url,
                        notes="Extracted from web-fetched page in Phase 2.",
                    )
                    updated["duration"].append(result)
                    candidate_upgraded = True

        # Try age/grade extraction
        if "age_grade" in missing:
            p1 = phase1.get(cid, {}).get("age_grade", {})
            if p1.get("status") in ("missing", "partial"):
                age_grade = extract_age_grade_from_text(page_text)
                if age_grade:
                    snippet = age_grade.pop("eligibility_text", None)
                    age_grade["eligibility_text"] = snippet
                    result = _enrichment_result(
                        cid, "age_grade", "found", "medium", age_grade,
                        snippet, evidence_url=url,
                        notes="Extracted from web-fetched page in Phase 2.",
                    )
                    updated["age_grade"].append(result)
                    candidate_upgraded = True

        # Try contact extraction
        if "contact" in missing or True:  # Always try contact since Phase 1 only has partial
            p1 = phase1.get(cid, {}).get("contact", {})
            p1_fields = p1.get("fields", {})
            # Only try if we don't already have email
            if not p1_fields.get("contact_email"):
                contact = extract_contact_from_text(page_text, url)
                if contact:
                    # Merge with Phase 1 operator_name
                    contact["operator_name"] = p1_fields.get("operator_name") or contact.get("operator_name")
                    result = _enrichment_result(
                        cid, "contact", "found" if contact.get("contact_email") else "partial",
                        "medium", contact, None, evidence_url=url,
                        notes="Extracted from web-fetched page in Phase 2.",
                    )
                    updated["contact"].append(result)
                    candidate_upgraded = True

        if candidate_upgraded:
            fetch_stats["upgraded"] += 1

        status_char = "+" if candidate_upgraded else "."
        if (i + 1) % 25 == 0 or i == len(queue) - 1:
            print(f"  [{i+1}/{len(queue)}] processed (fetched={fetch_stats['fetched']}, cached={fetch_stats['cached']}, failed={fetch_stats['failed']}, upgraded={fetch_stats['upgraded']})")

    # Write Phase 2 results
    for etype, results in updated.items():
        if results:
            out_path = output_dir / f"{etype}_enrichment_phase2.jsonl"
            write_jsonl(out_path, results)
            print(f"  {etype}: {len(results)} new results → {out_path}")

    # Merge Phase 1 + Phase 2 into combined files
    print("\nMerging Phase 1 + Phase 2 results...")
    merge_stats = _merge_phases(phase1_dir, output_dir)

    summary = {
        "run_timestamp": utc_now_iso(),
        "phase": 2,
        "candidates_processed": len(queue),
        "fetch_stats": fetch_stats,
        "phase2_extractions": {k: len(v) for k, v in updated.items()},
        "merge_stats": merge_stats,
    }

    summary_path = output_dir / "enrichment_phase2_summary.json"
    ensure_parent(summary_path)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nPhase 2 summary → {summary_path}")

    return summary


def _merge_phases(phase1_dir: Path, phase2_dir: Path) -> dict:
    """Merge Phase 2 results on top of Phase 1, keeping Phase 2 when it upgrades."""
    stats = {}
    for etype in ["pricing", "duration", "age_grade", "contact", "taxonomy"]:
        p1_path = phase1_dir / f"{etype}_enrichment.jsonl"
        p2_path = phase2_dir / f"{etype}_enrichment_phase2.jsonl"
        merged_path = phase2_dir / f"{etype}_enrichment_merged.jsonl"

        p1_rows = {r["candidate_id"]: r for r in read_jsonl(p1_path)}
        p2_rows = {r["candidate_id"]: r for r in read_jsonl(p2_path)}

        upgraded = 0
        merged = []
        for cid, p1 in p1_rows.items():
            if cid in p2_rows:
                p2 = p2_rows[cid]
                # Use Phase 2 if it found more data
                if _status_rank(p2.get("status", "missing")) > _status_rank(p1.get("status", "missing")):
                    merged.append(p2)
                    upgraded += 1
                else:
                    merged.append(p1)
            else:
                merged.append(p1)

        write_jsonl(merged_path, merged)
        stats[etype] = {"total": len(merged), "upgraded_from_phase2": upgraded}
        print(f"  {etype}: {len(merged)} total, {upgraded} upgraded from Phase 2 → {merged_path}")

    return stats


def _status_rank(status: str) -> int:
    return {"missing": 0, "uncertain": 1, "partial": 2, "found": 3}.get(status, 0)


def main():
    parser = argparse.ArgumentParser(description="Phase 2 web-fetch enrichment")
    parser.add_argument(
        "--followup-queue", "-f",
        default="data/enrichment/enrichment_followup_queue.jsonl",
        help="Path to follow-up queue JSONL",
    )
    parser.add_argument(
        "--phase1-dir",
        default="data/enrichment",
        help="Directory containing Phase 1 enrichment results",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="data/enrichment",
        help="Output directory for Phase 2 results",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        help="Limit number of candidates to process",
    )
    parser.add_argument(
        "--batch-sleep",
        type=float,
        default=0.5,
        help="Sleep between fetches (seconds)",
    )
    args = parser.parse_args()

    text_dir = Path("data/raw/evidence-pages/text")
    html_dir = Path("data/raw/evidence-pages/html")
    manifest_path = Path("data/raw/evidence-pages/manifests/enrichment_capture_manifest.jsonl")

    summary = run_phase2(
        followup_path=Path(args.followup_queue),
        phase1_dir=Path(args.phase1_dir),
        output_dir=Path(args.output_dir),
        text_dir=text_dir,
        html_dir=html_dir,
        manifest_path=manifest_path,
        limit=args.limit,
        batch_sleep=args.batch_sleep,
    )

    total_upgraded = sum(v for v in summary["phase2_extractions"].values())
    print(f"\nDone. {total_upgraded} new enrichment extractions from {summary['candidates_processed']} candidates.")


if __name__ == "__main__":
    main()
