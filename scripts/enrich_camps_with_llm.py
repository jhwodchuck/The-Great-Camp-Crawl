#!/usr/bin/env python3
"""Enrich camp records using cached evidence pages and an LLM.

Reads `likely_camp` records from the DB that are still missing enrichment
fields, loads cached markdown (preferred) or HTML evidence pages, sends
structured enrichment prompts to the configured LLM provider, and writes
normalised results back to the database.

Examples:
    # OpenRouter — enrich 50 camps, 4 workers
    OPENROUTER_API_KEY=sk-or-v1-... \\
    python scripts/enrich_camps_with_llm.py \\
      --provider openrouter \\
      --model google/gemma-3-27b-it:free \\
      --limit 50 --workers 4 --delay 0

    # Local llama.cpp server
    python scripts/enrich_camps_with_llm.py \\
      --provider openai-compatible \\
      --base-url http://127.0.0.1:8080/v1 \\
      --model qwen2.5-7b-instruct \\
      --limit 10

    # Gemini
    GEMINI_API_KEY=... python scripts/enrich_camps_with_llm.py \\
      --provider gemini --model gemini-2.0-flash \\
      --limit 25

    # Debug a single camp
    python scripts/enrich_camps_with_llm.py \\
      --provider openrouter --model google/gemma-3-27b-it:free \\
      --camp-id cand-us-tx-campchampions --verbose

    # Dry run — show what would be enriched
    python scripts/enrich_camps_with_llm.py --dry-run --limit 100
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, create_engine, or_
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Path setup — mirror triage script
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "research-ui" / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from models import Camp  # noqa: E402
from schema_runtime import ensure_runtime_schema  # noqa: E402
from lib.url_utils import normalize_url, stable_capture_stem  # noqa: E402
from lib.common import utc_now_iso  # noqa: E402

# ---------------------------------------------------------------------------
# Reuse LLM plumbing from triage script
# ---------------------------------------------------------------------------
from triage_candidates_with_llm import (  # noqa: E402
    ClientConfig,
    _call_cloudflare_workers_ai,
    _call_gemini,
    _call_llama_cpp,
    _call_openai_compatible,
    _extract_json_object,
    _normalize_db_url,
)

log = logging.getLogger("enrich_camps")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DB_URL = (
    os.environ.get("RESEARCH_UI_DATABASE_URL")
    or os.environ.get("DATABASE_URL_UNPOOLED")
    or os.environ.get("DATABASE_URL")
    or f"sqlite:///{BACKEND_DIR / 'research.db'}"
)
DEFAULT_TEXT_DIR = Path("data/raw/evidence-pages/text")
DEFAULT_HTML_DIR = Path("data/raw/evidence-pages/html")
MAX_EVIDENCE_CHARS = 12_000  # keep context bounded

# ---------------------------------------------------------------------------
# Enrichment schema columns added at runtime (mirrors schema_runtime pattern)
# ---------------------------------------------------------------------------
_ENRICHMENT_COLUMN_PATCHES = {
    "enriched_at": "ALTER TABLE camps ADD COLUMN enriched_at TIMESTAMPTZ",
    "enrichment_model": "ALTER TABLE camps ADD COLUMN enrichment_model VARCHAR(128)",
    "enrichment_source_file": "ALTER TABLE camps ADD COLUMN enrichment_source_file VARCHAR(512)",
}


def _ensure_enrichment_columns(engine) -> None:
    """Add enrichment-tracking columns if missing (safe, idempotent)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "camps" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("camps")}
    missing = [
        stmt for col, stmt in _ENRICHMENT_COLUMN_PATCHES.items() if col not in existing
    ]
    if not missing:
        return
    with engine.begin() as conn:
        for stmt in missing:
            conn.execute(text(stmt))


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

# Combined enrichment prompt: asks the LLM to extract all enrichment facets
# in a single call to reduce round-trips.
ENRICHMENT_SYSTEM_PROMPT = """\
You are an enrichment agent for a catalog of overnight and residential youth camps,
family camps, faith-based camps, and residential pre-college programs.

HARD RULES (from grounding rules):
- Do NOT mark a program as overnight/residential without explicit evidence of
  overnight, residential, boarding, lodging, or housing tied to the program.
- Do NOT infer overnight status from photos, cabins, the word "camp", or branding.
- Use null for unknown values. Prefer null over guessing.
- Copy short evidence snippets exactly from the source text.
- If evidence is ambiguous, set confidence to "low" and note the ambiguity.
- Do NOT fabricate pricing, ages, duration, or contact info.

Return ONLY a single JSON object (no markdown, no prose) with exactly these keys:

{
  "pricing": {
    "status": "found|partial|missing|uncertain",
    "confidence": "low|medium|high",
    "currency": null,
    "amount_min": null,
    "amount_max": null,
    "boarding_included": null,
    "evidence_snippet": null,
    "notes": null
  },
  "duration": {
    "status": "found|partial|missing|uncertain",
    "confidence": "low|medium|high",
    "min_days": null,
    "max_days": null,
    "session_model": null,
    "evidence_snippet": null,
    "notes": null
  },
  "age_grade": {
    "status": "found|partial|missing|uncertain",
    "confidence": "low|medium|high",
    "age_min": null,
    "age_max": null,
    "grade_min": null,
    "grade_max": null,
    "evidence_snippet": null,
    "notes": null
  },
  "contact": {
    "status": "found|partial|missing|uncertain",
    "confidence": "low|medium|high",
    "contact_email": null,
    "contact_phone": null,
    "operator_name": null,
    "evidence_snippet": null,
    "notes": null
  },
  "taxonomy": {
    "status": "found|partial|missing|uncertain",
    "confidence": "low|medium|high",
    "program_family_tags": [],
    "camp_type_tags": [],
    "evidence_snippet": null,
    "notes": null
  },
  "overnight": {
    "status": "found|partial|missing|uncertain",
    "confidence": "low|medium|high",
    "overnight_confirmed": null,
    "evidence_snippet": null,
    "notes": null
  },
  "activity": {
    "status": "found|partial|missing|uncertain",
    "confidence": "low|medium|high",
    "active_confirmed": null,
    "activity_status": "active_recent|possibly_active|stale|closed_or_inactive|null",
    "evidence_snippet": null,
    "notes": null
  }
}

Rules for each section:
- pricing: Look for tuition, fees, costs, rates. Capture currency, min/max amounts.
  Ignore amounts < $50 or amounts that look like years.
- duration: Look for session length in days or weeks. Capture min/max days.
- age_grade: Look for age ranges or grade eligibility. Do not translate grade↔age.
- contact: Look for official email addresses, phone numbers, operator/organization name.
- taxonomy: Assign program_family_tags from: college-pre-college, academic, stem, sports,
  arts, music, wilderness, faith-based, family, therapeutic, military, special-needs.
  Assign camp_type_tags from: overnight, residential, boarding, day-optional, weekend.
  Only assign tags supported by the evidence.
- overnight: Confirm overnight/residential status ONLY with explicit evidence.
- activity: Look for recent dates (2025-2026), registration deadlines, or current content
  indicating the program is still active.

If no evidence exists for a section, set status to "missing" and all fields to null."""

REPAIR_SUFFIX = """
Your previous response was not valid JSON. Return ONLY a single JSON object with
the exact schema described above. No markdown fences. No prose before or after."""


def _build_enrichment_prompt(camp: Camp, evidence_text: str) -> str:
    """Build user prompt with camp metadata + evidence page text."""
    meta = {
        "record_id": camp.record_id,
        "name": camp.display_name or camp.name,
        "website_url": camp.website_url,
        "country": camp.country,
        "region": camp.region,
        "city": camp.city,
    }
    parts = [
        "Camp record to enrich:",
        json.dumps(meta, indent=2, ensure_ascii=False),
        "",
        "--- EVIDENCE PAGE TEXT (from cached capture) ---",
        evidence_text,
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Evidence lookup
# ---------------------------------------------------------------------------

def _find_evidence_text(
    camp: Camp,
    text_dir: Path,
    html_dir: Path,
) -> tuple[str | None, str | None]:
    """Return (evidence_text, source_file) or (None, None).

    Prefer markdown (.md) over raw HTML.
    """
    url = normalize_url(camp.website_url or "")
    if not url:
        return None, None

    stem = stable_capture_stem(url)

    # Try markdown first
    md_path = text_dir / f"{stem}.md"
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8", errors="replace")
        if text.strip():
            return _truncate_evidence(text), str(md_path)

    # Fall back to HTML
    html_path = html_dir / f"{stem}.html"
    if html_path.exists():
        raw_html = html_path.read_text(encoding="utf-8", errors="replace")
        if raw_html.strip():
            # Strip tags crudely for context — full HTML would waste tokens
            text = _strip_html_tags(raw_html)
            return _truncate_evidence(text), str(html_path)

    return None, None


def _truncate_evidence(text: str) -> str:
    """Keep evidence bounded to MAX_EVIDENCE_CHARS."""
    if len(text) <= MAX_EVIDENCE_CHARS:
        return text
    # Keep first and last portions for context
    head = MAX_EVIDENCE_CHARS * 3 // 4
    tail = MAX_EVIDENCE_CHARS - head - 30
    return text[:head] + "\n\n[...truncated...]\n\n" + text[-tail:]


def _strip_html_tags(html: str) -> str:
    """Quick HTML→text fallback (no dependency on bs4 at import time)."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Needs-enrichment check
# ---------------------------------------------------------------------------

# Fields that indicate enrichment has been done
_ENRICHMENT_INDICATORS = [
    "pricing_min",
    "pricing_max",
    "duration_min_days",
    "duration_max_days",
    "ages_min",
    "ages_max",
    "contact_email",
    "contact_phone",
    "overnight_confirmed",
    "active_confirmed",
]


def _needs_enrichment(camp: Camp) -> bool:
    """Return True if the camp is missing one or more enrichment fields."""
    for field in _ENRICHMENT_INDICATORS:
        val = getattr(camp, field, None)
        if val is not None:
            continue
        return True
    return True  # always true if at least one field is None


# ---------------------------------------------------------------------------
# LLM call routing (mirrors triage pattern)
# ---------------------------------------------------------------------------

def _call_llm(config: ClientConfig, prompt: str, system_prompt: str = ENRICHMENT_SYSTEM_PROMPT) -> str:
    if config.provider in ("openai-compatible", "openrouter"):
        return _call_openai_compatible(config, prompt, system_prompt)
    elif config.provider == "llama-cpp":
        return _call_llama_cpp(config, prompt, system_prompt)
    elif config.provider == "cloudflare-workers-ai":
        return _call_cloudflare_workers_ai(config, prompt, system_prompt)
    elif config.provider == "gemini":
        return _call_gemini(config, prompt, system_prompt)
    else:
        raise RuntimeError(f"Unsupported provider: {config.provider}")


def _enrich_one(
    config: ClientConfig,
    camp: Camp,
    evidence_text: str,
    source_file: str,
) -> dict[str, Any]:
    """Call the LLM and return a structured enrichment result dict."""
    prompt = _build_enrichment_prompt(camp, evidence_text)
    content = _call_llm(config, prompt)

    try:
        result = _extract_json_object(content)
    except (ValueError, json.JSONDecodeError):
        # Retry with repair instructions
        log.warning("%s: malformed JSON from LLM, retrying with repair prompt", camp.record_id)
        content = _call_llm(config, prompt + "\n\n" + REPAIR_SUFFIX)
        result = _extract_json_object(content)

    return {
        "record_id": camp.record_id,
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "model": config.model,
        "source_file": source_file,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_DIGITS_RE = re.compile(r"\d")


def _normalise_email(val: Any) -> str | None:
    if not val or not isinstance(val, str):
        return None
    val = val.strip().lower()
    if _EMAIL_RE.match(val):
        return val
    return None


def _normalise_phone(val: Any) -> str | None:
    if not val or not isinstance(val, str):
        return None
    digits = _PHONE_DIGITS_RE.findall(val)
    if len(digits) < 7:
        return None
    # Return the original string cleaned of excess whitespace
    return re.sub(r"\s+", " ", val).strip()


def _safe_int(val: Any, lo: int = 0, hi: int = 999) -> int | None:
    if val is None:
        return None
    try:
        v = int(val)
        return v if lo <= v <= hi else None
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any, lo: float = 0, hi: float = 999_999) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        return v if lo <= v <= hi else None
    except (ValueError, TypeError):
        return None


def _safe_bool(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        low = val.lower().strip()
        if low in ("true", "yes", "1"):
            return True
        if low in ("false", "no", "0"):
            return False
    return None


def _safe_json_array(val: Any) -> str | None:
    """Normalise a list of strings to a JSON array text column."""
    if not val:
        return None
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except json.JSONDecodeError:
            return None
    if isinstance(val, list):
        cleaned = [str(v).strip() for v in val if v]
        if cleaned:
            return json.dumps(cleaned, ensure_ascii=False)
    return None


# ---------------------------------------------------------------------------
# DB persist
# ---------------------------------------------------------------------------

def _apply_enrichment(camp: Camp, result: dict[str, Any], enrichment_meta: dict[str, Any]) -> list[str]:
    """Apply parsed enrichment results to a Camp ORM object.

    Returns a list of field names that were updated.
    """
    updated: list[str] = []

    # --- pricing ---
    pricing = result.get("pricing") or {}
    if pricing.get("status") in ("found", "partial"):
        amt_min = _safe_float(pricing.get("amount_min"), lo=10)
        amt_max = _safe_float(pricing.get("amount_max"), lo=10)
        currency = pricing.get("currency")
        if amt_min is not None or amt_max is not None:
            if camp.pricing_min is None and amt_min is not None:
                camp.pricing_min = amt_min
                updated.append("pricing_min")
            if camp.pricing_max is None and amt_max is not None:
                camp.pricing_max = amt_max
                updated.append("pricing_max")
            if camp.pricing_currency is None and currency:
                camp.pricing_currency = str(currency)[:8]
                updated.append("pricing_currency")
        boarding = _safe_bool(pricing.get("boarding_included"))
        if camp.boarding_included is None and boarding is not None:
            camp.boarding_included = boarding
            updated.append("boarding_included")

    # --- duration ---
    duration = result.get("duration") or {}
    if duration.get("status") in ("found", "partial"):
        dmin = _safe_int(duration.get("min_days"), lo=1, hi=365)
        dmax = _safe_int(duration.get("max_days"), lo=1, hi=365)
        if camp.duration_min_days is None and dmin is not None:
            camp.duration_min_days = dmin
            updated.append("duration_min_days")
        if camp.duration_max_days is None and dmax is not None:
            camp.duration_max_days = dmax
            updated.append("duration_max_days")

    # --- age/grade ---
    age_grade = result.get("age_grade") or {}
    if age_grade.get("status") in ("found", "partial"):
        amin = _safe_int(age_grade.get("age_min"), lo=3, hi=25)
        amax = _safe_int(age_grade.get("age_max"), lo=3, hi=25)
        gmin = _safe_int(age_grade.get("grade_min"), lo=0, hi=16)
        gmax = _safe_int(age_grade.get("grade_max"), lo=0, hi=16)
        if camp.ages_min is None and amin is not None:
            camp.ages_min = amin
            updated.append("ages_min")
        if camp.ages_max is None and amax is not None:
            camp.ages_max = amax
            updated.append("ages_max")
        if camp.grades_min is None and gmin is not None:
            camp.grades_min = gmin
            updated.append("grades_min")
        if camp.grades_max is None and gmax is not None:
            camp.grades_max = gmax
            updated.append("grades_max")

    # --- contact ---
    contact = result.get("contact") or {}
    if contact.get("status") in ("found", "partial"):
        email = _normalise_email(contact.get("contact_email"))
        phone = _normalise_phone(contact.get("contact_phone"))
        operator = contact.get("operator_name")
        if camp.contact_email is None and email:
            camp.contact_email = email
            updated.append("contact_email")
        if camp.contact_phone is None and phone:
            camp.contact_phone = phone
            updated.append("contact_phone")
        if camp.operator_name is None and operator and isinstance(operator, str) and operator.strip():
            camp.operator_name = operator.strip()[:512]
            updated.append("operator_name")

    # --- taxonomy ---
    taxonomy = result.get("taxonomy") or {}
    if taxonomy.get("status") in ("found", "partial"):
        pf = _safe_json_array(taxonomy.get("program_family_tags"))
        ct = _safe_json_array(taxonomy.get("camp_type_tags"))
        if camp.program_family is None and pf:
            camp.program_family = pf
            updated.append("program_family")
        if camp.camp_types is None and ct:
            camp.camp_types = ct
            updated.append("camp_types")

    # --- overnight confirmation ---
    overnight = result.get("overnight") or {}
    if overnight.get("status") == "found" and overnight.get("confidence") in ("medium", "high"):
        confirmed = _safe_bool(overnight.get("overnight_confirmed"))
        if camp.overnight_confirmed is None and confirmed is not None:
            camp.overnight_confirmed = confirmed
            updated.append("overnight_confirmed")

    # --- activity status ---
    activity = result.get("activity") or {}
    if activity.get("status") == "found" and activity.get("confidence") in ("medium", "high"):
        active = _safe_bool(activity.get("active_confirmed"))
        if camp.active_confirmed is None and active is not None:
            camp.active_confirmed = active
            updated.append("active_confirmed")

    # --- enrichment metadata ---
    now = datetime.now(timezone.utc)
    camp.enriched_at = now  # type: ignore[attr-defined]
    camp.enrichment_model = enrichment_meta.get("model", "")[:128]  # type: ignore[attr-defined]
    camp.enrichment_source_file = enrichment_meta.get("source_file", "")[:512]  # type: ignore[attr-defined]

    return updated


# ---------------------------------------------------------------------------
# Checkpoint (file-based, optional)
# ---------------------------------------------------------------------------

def _load_checkpoint(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    return set(path.read_text(encoding="utf-8").splitlines())


def _append_checkpoint(path: Path | None, record_id: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(record_id + "\n")


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

def _enrichment_query(session, args: argparse.Namespace):
    """Select camps that are likely_camp and missing enrichment data."""
    query = session.query(Camp).filter(
        or_(
            Camp.triage_verdict == "likely_camp",
            Camp.triage_verdict.is_(None),
        ),
        or_(Camp.is_excluded.is_(False), Camp.is_excluded.is_(None)),
    )

    if args.camp_id:
        query = query.filter(Camp.record_id == args.camp_id)

    if not args.force:
        # Skip already-enriched records: enriched_at IS NULL
        # Use raw text filter since column may not exist in ORM yet
        try:
            enriched_at_col = getattr(Camp, "enriched_at", None)
            if enriched_at_col is not None:
                query = query.filter(Camp.enriched_at.is_(None))  # type: ignore[attr-defined]
        except Exception:
            pass  # column may not exist yet

    query = query.order_by(Camp.updated_at.desc(), Camp.id.desc())

    if args.offset:
        query = query.offset(args.offset)

    return query.limit(args.limit).all()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Enrich camp records using cached evidence pages and an LLM"
    )
    p.add_argument("--db-url", default=DEFAULT_DB_URL, help="SQLAlchemy database URL")
    p.add_argument(
        "--provider",
        choices=["openai-compatible", "openrouter", "llama-cpp", "cloudflare-workers-ai", "gemini"],
        default="openai-compatible",
    )
    p.add_argument("--model", required=True, help="Model name for the selected provider")
    p.add_argument("--base-url", help="Base URL for OpenAI-compatible server")
    p.add_argument("--api-key", help="API key override")
    p.add_argument("--cloudflare-account-id", help="Cloudflare account ID override")
    p.add_argument("--no-think", action="store_true", help="Disable extended thinking (Ollama qwen3)")

    p.add_argument("--limit", type=int, default=25, help="Max records to process (default: 25)")
    p.add_argument("--offset", type=int, default=0, help="Skip first N matching records")
    p.add_argument("--batch-size", type=int, default=1, help="Records per worker batch (kept 1 for enrichment)")
    p.add_argument("--camp-id", help="Enrich a single camp by record_id")
    p.add_argument("--force", action="store_true", help="Re-enrich already-enriched records")
    p.add_argument("--dry-run", action="store_true", help="Show what would be enriched without calling LLM")
    p.add_argument("--workers", type=int, default=1, help="Parallel worker threads (default: 1)")
    p.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (default: 1.0)")
    p.add_argument("--checkpoint-file", type=str, default=None, help="File to track completed record_ids for resume")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")

    p.add_argument("--text-dir", default=str(DEFAULT_TEXT_DIR), help="Directory with cached markdown evidence pages")
    p.add_argument("--html-dir", default=str(DEFAULT_HTML_DIR), help="Directory with cached HTML evidence pages")
    p.add_argument("--output", default=None, help="Optional JSONL output path for raw LLM results")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    engine = create_engine(_normalize_db_url(args.db_url))
    Session = sessionmaker(bind=engine)
    ensure_runtime_schema(engine)
    _ensure_enrichment_columns(engine)

    # --- Load records ---
    with Session() as read_session:
        camps = _enrichment_query(read_session, args)
        if not camps:
            log.info("No camps matching enrichment criteria.")
            return 0
        read_session.expunge_all()

    log.info("Loaded %d camp(s) for enrichment", len(camps))

    # --- Filter by checkpoint ---
    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else None
    completed_ids = _load_checkpoint(checkpoint_path)
    if completed_ids:
        before = len(camps)
        camps = [c for c in camps if c.record_id not in completed_ids]
        log.info("Checkpoint: skipped %d already-completed, %d remaining", before - len(camps), len(camps))

    if not camps:
        log.info("All camps already completed (per checkpoint).")
        return 0

    # --- Resolve evidence ---
    text_dir = Path(args.text_dir)
    html_dir = Path(args.html_dir)

    camps_with_evidence: list[tuple[Camp, str, str]] = []
    skipped_no_evidence = 0
    for camp in camps:
        evidence_text, source_file = _find_evidence_text(camp, text_dir, html_dir)
        if evidence_text is None:
            log.debug("SKIP %s — no cached evidence page (url: %s)", camp.record_id, camp.website_url)
            skipped_no_evidence += 1
            continue
        camps_with_evidence.append((camp, evidence_text, source_file))

    log.info(
        "Evidence resolved: %d with evidence, %d skipped (no cache)",
        len(camps_with_evidence),
        skipped_no_evidence,
    )

    if not camps_with_evidence:
        log.info("No camps have cached evidence pages. Run capture_triaged_camps.py first.")
        return 0

    # --- Dry run ---
    if args.dry_run:
        for camp, _, source_file in camps_with_evidence:
            print(f"  {camp.record_id:40s}  {camp.website_url or '':<60s}  evidence={source_file}")
        print(f"\nWould enrich {len(camps_with_evidence)} camps.")
        return 0

    # --- Build provider config ---
    if args.provider == "openrouter":
        resolved_base_url = args.base_url or "https://openrouter.ai/api/v1"
        resolved_api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY")
        if not resolved_api_key:
            log.error("--provider openrouter requires OPENROUTER_API_KEY env var or --api-key")
            return 1
    elif args.provider == "gemini":
        resolved_base_url = None
        resolved_api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_api_key:
            log.error("--provider gemini requires GEMINI_API_KEY env var or --api-key")
            return 1
    else:
        resolved_base_url = args.base_url
        resolved_api_key = args.api_key

    config = ClientConfig(
        provider=args.provider,
        model=args.model,
        base_url=resolved_base_url,
        api_key=resolved_api_key,
        cloudflare_account_id=args.cloudflare_account_id,
        no_think=args.no_think,
    )

    # --- Phase: LLM enrichment with incremental persist ---
    persist_lock = threading.Lock()
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0, "fields_updated": 0}
    total = len(camps_with_evidence)

    def _process_and_persist(camp: Camp, evidence_text: str, source_file: str) -> None:
        try:
            enrichment = _enrich_one(config, camp, evidence_text, source_file)
        except Exception as exc:
            log.error("%s: LLM error — %s", camp.record_id, exc)
            stats["failed"] += 1
            return

        result = enrichment.get("result", {})
        meta = {"model": config.model, "source_file": source_file}

        with persist_lock:
            # Optional JSONL output
            if args.output:
                out_path = Path(args.output)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with out_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(enrichment, ensure_ascii=False) + "\n")

            # Write to DB
            with Session() as ws:
                db_camp = ws.query(Camp).filter_by(record_id=camp.record_id).one_or_none()
                if not db_camp:
                    log.warning("%s: record disappeared from DB", camp.record_id)
                    stats["skipped"] += 1
                    return

                updated_fields = _apply_enrichment(db_camp, result, meta)
                ws.commit()

                stats["succeeded"] += 1
                stats["fields_updated"] += len(updated_fields)
                stats["processed"] += 1

                _append_checkpoint(checkpoint_path, camp.record_id)

                field_summary = ", ".join(updated_fields) if updated_fields else "(no new fields)"
                log.info(
                    "[%d/%d] %s: %d fields updated (%s)",
                    stats["processed"],
                    total,
                    camp.record_id,
                    len(updated_fields),
                    field_summary,
                )

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {}
            for camp, evidence_text, source_file in camps_with_evidence:
                fut = pool.submit(_process_and_persist, camp, evidence_text, source_file)
                futures[fut] = camp.record_id
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    log.error("%s: unhandled error — %s", futures[future], exc)
                    stats["failed"] += 1
    else:
        for i, (camp, evidence_text, source_file) in enumerate(camps_with_evidence):
            if i > 0 and args.delay > 0:
                time.sleep(args.delay)
            _process_and_persist(camp, evidence_text, source_file)

    log.info(
        "\n[done] processed=%d succeeded=%d failed=%d skipped_no_evidence=%d fields_updated=%d",
        stats["processed"],
        stats["succeeded"],
        stats["failed"],
        skipped_no_evidence,
        stats["fields_updated"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
