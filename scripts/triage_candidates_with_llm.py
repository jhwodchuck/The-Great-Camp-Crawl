#!/usr/bin/env python3
"""Generate "camp vs not a camp" triage suggestions for catalog records.

Examples:    # OpenRouter (free tier) — recommended
    OPENROUTER_API_KEY=sk-or-v1-... \\
    python scripts/triage_candidates_with_llm.py \\
      --provider openrouter \\
      --model google/gemma-4-31b-it:free \\
      --candidate-only --limit 9999 --workers 8 --delay 0
    # Local llama.cpp server (OpenAI-compatible)
    python scripts/triage_candidates_with_llm.py \
      --provider openai-compatible \
      --base-url http://127.0.0.1:8080/v1 \
      --model qwen2.5-7b-instruct \
      --limit 25

    # Cloudflare Workers AI direct REST API
    CLOUDFLARE_ACCOUNT_ID=... CLOUDFLARE_API_TOKEN=... \
    python scripts/triage_candidates_with_llm.py \
      --provider cloudflare-workers-ai \
      --model @cf/meta/llama-3.2-3b-instruct \
      --limit 25
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request

from sqlalchemy import and_, case, create_engine, func, or_
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "research-ui" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from models import Camp  # noqa: E402
from schema_runtime import ensure_runtime_schema  # noqa: E402


DEFAULT_DB_URL = (
    os.environ.get("RESEARCH_UI_DATABASE_URL")
    or os.environ.get("DATABASE_URL_UNPOOLED")
    or os.environ.get("DATABASE_URL")
    or f"sqlite:///{BACKEND_DIR / 'research.db'}"
)
SYSTEM_PROMPT = """You are triaging records for a catalog of overnight and residential youth camps,
specialty camps, sports camps, arts and music camps, academic/STEM camps, family camps,
faith-based camps and retreats, and residential pre-college programs.

Use only the record fields you are given.

Return exactly one JSON object with these keys:
- verdict: one of "likely_camp", "likely_not_a_camp", or "unclear"
- confidence: one of "low", "medium", or "high"
- reason: short explanation
- exclusion_reason: one of "not_a_camp", "not_overnight", "inactive_or_out_of_scope", "duplicate_or_wrong_venue", or "other"
- signals: array of short evidence bullets

Mark "likely_not_a_camp" when the title, URL, or description clearly point to unrelated content like
medical pages, tax pages, classifieds, news, ecommerce, generic directories, or non-youth/non-residential content.
Do not mark a record as "likely_not_a_camp" only because it is university-hosted, academic, research-oriented,
or not a "traditional camp." Residential pre-college programs, specialty resident camps, and other overnight youth
programs are in scope even when they are called academies, institutes, scholars programs, or summer programs.
If the evidence is mixed, use "unclear" rather than guessing."""

BATCH_SYSTEM_PROMPT = """You are triaging records for a catalog of overnight and residential youth camps,
specialty camps, sports camps, arts and music camps, academic/STEM camps, family camps,
faith-based camps, and residential pre-college programs.

You will receive a JSON array of records. Return ONLY a JSON array (no markdown, no prose) with one object
per input record in the same order. Each object must contain exactly these keys:
- record_id: copied verbatim from input
- verdict: "likely_camp", "likely_not_a_camp", or "unclear"
- confidence: "low", "medium", or "high"
- reason: one sentence, max 20 words
- exclusion_reason: "not_a_camp"|"not_overnight"|"inactive_or_out_of_scope"|"duplicate_or_wrong_venue"|"other" when not a camp, else null

Mark "likely_not_a_camp" (high) for: news, ecommerce, social media, dictionaries, travel sites, sports,
entertainment, adult content, government info pages, software tools, shipping, retail, or anything clearly
not a youth/family/residential program. Do not exclude a record only because it is university-hosted,
academic, research-oriented, or not a "traditional camp" if the record shows residential, overnight,
or pre-college signals. Use "unclear" only when genuine ambiguity exists."""


@dataclass
class ClientConfig:
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    cloudflare_account_id: str | None = None
    no_think: bool = False  # Ollama: disable qwen3 extended thinking


def _normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql+psycopg://"):
        return db_url
    if db_url.startswith("postgres://"):
        return "postgresql+psycopg://" + db_url[len("postgres://") :]
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url[len("postgresql://") :]
    return db_url


def _camp_query(session, args: argparse.Namespace):
    query = session.query(Camp).filter(or_(Camp.is_excluded.is_(False), Camp.is_excluded.is_(None)))

    if args.record_id:
        query = query.filter(Camp.record_id == args.record_id)
    if args.website_host:
        pattern = f"%{args.website_host}%"
        query = query.filter(Camp.website_url.ilike(pattern))
    if args.candidate_only:
        query = query.filter(
            or_(
                Camp.record_id.ilike("cand-%"),
                Camp.draft_status.in_(["candidate", "candidate_pending", "multi_venue"]),
            )
        )
    if not args.retriage:
        query = query.filter(Camp.triage_verdict.is_(None))

    has_real_city = case(
        (
            and_(
                Camp.city.is_not(None),
                func.trim(Camp.city) != "",
                func.lower(Camp.city) != "unknown-city",
            ),
            1,
        ),
        else_=0,
    )
    has_region = case(
        (
            and_(
                Camp.region.is_not(None),
                func.trim(Camp.region) != "",
            ),
            1,
        ),
        else_=0,
    )
    has_website = case(
        (
            and_(
                Camp.website_url.is_not(None),
                func.trim(Camp.website_url) != "",
            ),
            1,
        ),
        else_=0,
    )
    has_description = case(
        (
            and_(
                Camp.description_md.is_not(None),
                func.trim(Camp.description_md) != "",
            ),
            1,
        ),
        else_=0,
    )
    has_operator = case(
        (
            and_(
                Camp.operator_name.is_not(None),
                func.trim(Camp.operator_name) != "",
            ),
            1,
        ),
        else_=0,
    )
    draft_priority = case(
        (Camp.draft_status == "candidate", 2),
        (Camp.draft_status == "multi_venue", 1),
        else_=0,
    )
    description_length = func.length(func.coalesce(Camp.description_md, ""))

    return (
        query.order_by(
            has_real_city.desc(),
            has_region.desc(),
            has_website.desc(),
            has_description.desc(),
            has_operator.desc(),
            draft_priority.desc(),
            description_length.desc(),
            Camp.updated_at.desc(),
            Camp.id.desc(),
        )
        .limit(args.limit)
        .all()
    )


def _excerpt(text: str | None, max_chars: int = 2400) -> str | None:
    if not text:
        return None
    cleaned = " ".join(text.split())
    return cleaned[:max_chars] if len(cleaned) > max_chars else cleaned


def _json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    values: list[str] = []
    for item in parsed:
        text = str(item).strip().lower()
        if text:
            values.append(text)
    return values


def _camp_text_blob(camp: Camp) -> str:
    return " ".join(
        str(part or "")
        for part in (
            camp.record_id,
            camp.name,
            camp.display_name,
            camp.operator_name,
            camp.venue_name,
            camp.website_url,
            camp.description_md,
        )
    ).lower()


def _looks_like_meta_record(camp: Camp) -> bool:
    blob = _camp_text_blob(camp)
    meta_markers = (
        "lead",
        "leads",
        "ecosystem",
        "directory",
        "member network",
        "association",
        "sample seeded dossier",
        "program venue to confirm",
        "program-specific venue to confirm",
        "venue to confirm",
        "specific residence format not yet confirmed",
        "institutional lead",
    )
    return any(marker in blob for marker in meta_markers)


def _has_strong_in_scope_signals(camp: Camp) -> bool:
    families = set(_json_list(camp.program_family))
    camp_types = set(_json_list(camp.camp_types))
    blob = _camp_text_blob(camp)
    residential_markers = (
        "live in residence halls",
        "residence halls",
        "housing and meals",
        "students stay in university dormitories",
        "campers stay in dorms",
        "residential program",
        "residential camp",
        "residential college preparatory program",
        "four-week summer residential program",
        "dormitories",
        "dorms",
        "boarding",
        "campus life firsthand",
    )
    return (
        camp.overnight_confirmed is True
        or "college-pre-college" in families
        or bool({"overnight", "residential", "residential-academic"} & camp_types)
        or any(marker in blob for marker in residential_markers)
    )


def _apply_triage_guardrails(camp: Camp, result: dict[str, object]) -> dict[str, object]:
    if result.get("verdict") != "likely_not_a_camp":
        return result
    if _looks_like_meta_record(camp):
        return result
    if not _has_strong_in_scope_signals(camp):
        return result

    guarded = dict(result)
    original_reason = str(guarded.get("reason") or "").strip()
    guarded["verdict"] = "unclear"
    guarded["confidence"] = "medium"
    guarded["exclusion_reason"] = None
    guarded["reason"] = (
        f"{original_reason} Guardrail: residential/pre-college/specialty overnight signals require manual review."
        if original_reason
        else "Guardrail: residential/pre-college/specialty overnight signals require manual review."
    )
    signals = [str(signal) for signal in (guarded.get("signals") or []) if signal]
    signals.append("Guardrail triggered: structured residential or pre-college signals present.")
    guarded["signals"] = signals
    return guarded


def _record_payload(camp: Camp) -> dict[str, object]:
    return {
        "record_id": camp.record_id,
        "name": camp.display_name or camp.name,
        "website_url": camp.website_url,
        "country": camp.country,
        "region": camp.region,
        "city": camp.city,
        "operator_name": camp.operator_name,
        "venue_name": camp.venue_name,
        "draft_status": camp.draft_status,
        "confidence": camp.confidence,
        "program_family": camp.program_family,
        "camp_types": camp.camp_types,
        "overnight_confirmed": camp.overnight_confirmed,
        "active_confirmed": camp.active_confirmed,
        "description_excerpt": _excerpt(camp.description_md),
    }


def _prompt_for_camp(camp: Camp) -> str:
    return "Record to classify:\n" + json.dumps(_record_payload(camp), indent=2, ensure_ascii=False)


def _prompt_for_batch(camps: list[Camp]) -> str:
    records = [
        {
            "record_id": c.record_id,
            "name": c.display_name or c.name,
            "website_url": c.website_url,
            "country": c.country,
            "region": c.region,
            "city": c.city,
            "operator_name": c.operator_name,
            "venue_name": c.venue_name,
            "draft_status": c.draft_status,
            "program_family": c.program_family,
            "camp_types": c.camp_types,
            "overnight_confirmed": c.overnight_confirmed,
            "active_confirmed": c.active_confirmed,
            "description_excerpt": _excerpt(c.description_md, max_chars=700),
        }
        for c in camps
    ]
    return json.dumps(records, ensure_ascii=False)


_MAX_429_RETRIES = 6


def _http_json(
    url: str,
    payload: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 90,
) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(_MAX_429_RETRIES + 1):
        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                **(headers or {}),
            },
        )
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt < _MAX_429_RETRIES:
                # Parse retryDelay from the response if available, floor at 5s
                match = re.search(r'"retryDelay"\s*:\s*"([\d.]+)s"', detail)
                wait = max(float(match.group(1)), 5) if match else min(15 * (2 ** attempt), 120)
                print(f"  [429] rate-limited, retrying in {wait:.0f}s (attempt {attempt + 1}/{_MAX_429_RETRIES})…", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    raise RuntimeError(f"Exhausted {_MAX_429_RETRIES} retries for {url}")


def _extract_json_object(text: str) -> dict[str, object]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Model did not return JSON: {text[:400]}")
    return json.loads(text[start : end + 1])


def _extract_json_array(text: str) -> list[dict[str, object]]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Model did not return a JSON array: {text[:400]}")
    return json.loads(text[start : end + 1])


def _call_openai_compatible(config: ClientConfig, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    if not config.base_url:
        raise RuntimeError("--base-url is required for openai-compatible provider")

    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    payload: dict[str, object] = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    if config.no_think:
        payload["think"] = False  # Ollama extension: skip chain-of-thought for qwen3
    # Use longer timeout for local servers (localhost / 127.0.0.1)
    is_local = any(h in config.base_url for h in ("localhost", "127.0.0.1", "[::1]"))
    response = _http_json(url, payload, headers=headers, timeout=300 if is_local else 90)
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected response from {url}: {response}") from exc
    return content


def _call_llama_cpp(config: ClientConfig, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """llama.cpp server (OpenAI-compatible). Suppresses qwen3 thinking via /no_think
    in the system prompt rather than an Ollama-specific payload field."""
    if not config.base_url:
        raise RuntimeError("--base-url is required for llama-cpp provider")

    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    system_content = system_prompt
    if config.no_think:
        system_content = "/no_think\n" + system_content

    payload: dict[str, object] = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    response = _http_json(url, payload, headers=headers, timeout=300 if any(h in config.base_url for h in ("localhost", "127.0.0.1", "[::1]")) else 90)
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected response from {url}: {response}") from exc
    return content


def _call_cloudflare_workers_ai(config: ClientConfig, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    account_id = config.cloudflare_account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_key = config.api_key or os.environ.get("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_key:
        raise RuntimeError(
            "Cloudflare Workers AI requires CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN"
        )

    model_path = parse.quote(config.model, safe="@/")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_path}"
    response = _http_json(
        url,
        {
            "prompt": f"{system_prompt}\n\n{prompt}",
            "max_tokens": 512,
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        content = response["result"]["response"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected response from Cloudflare Workers AI: {response}") from exc
    return content


def _call_gemini(config: ClientConfig, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    api_key = config.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini requires GEMINI_API_KEY env var or --api-key")

    model = config.model or "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{parse.quote(model, safe='')}:generateContent"
    response = _http_json(
        url,
        {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0},
        },
        headers={"X-goog-api-key": api_key},
    )
    try:
        content = response["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected response from Gemini: {response}") from exc
    return content


def _triage_record(config: ClientConfig, camp: Camp) -> dict[str, object]:
    prompt = _prompt_for_camp(camp)
    if config.provider in ("openai-compatible", "openrouter"):
        content = _call_openai_compatible(config, prompt)
    elif config.provider == "llama-cpp":
        content = _call_llama_cpp(config, prompt)
    elif config.provider == "cloudflare-workers-ai":
        content = _call_cloudflare_workers_ai(config, prompt)
    elif config.provider == "gemini":
        content = _call_gemini(config, prompt)
    else:
        raise RuntimeError(f"Unsupported provider: {config.provider}")

    result = _apply_triage_guardrails(camp, _extract_json_object(content))
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "provider": config.provider,
        "model": config.model,
        "record_id": camp.record_id,
        "name": camp.display_name or camp.name,
        "website_url": camp.website_url,
        "verdict": result.get("verdict"),
        "confidence": result.get("confidence"),
        "reason": result.get("reason"),
        "exclusion_reason": result.get("exclusion_reason"),
        "signals": result.get("signals") or [],
    }


def _triage_batch(config: ClientConfig, camps: list[Camp]) -> list[dict[str, object]]:
    """Send N records in one request and fan the response out into per-camp result dicts."""
    prompt = _prompt_for_batch(camps)
    if config.provider in ("openai-compatible", "openrouter"):
        content = _call_openai_compatible(config, prompt, system_prompt=BATCH_SYSTEM_PROMPT)
    elif config.provider == "llama-cpp":
        content = _call_llama_cpp(config, prompt, system_prompt=BATCH_SYSTEM_PROMPT)
    elif config.provider == "cloudflare-workers-ai":
        content = _call_cloudflare_workers_ai(config, prompt, system_prompt=BATCH_SYSTEM_PROMPT)
    elif config.provider == "gemini":
        content = _call_gemini(config, prompt, system_prompt=BATCH_SYSTEM_PROMPT)
    else:
        raise RuntimeError(f"Unsupported provider: {config.provider}")

    raw_list = _extract_json_array(content)
    by_id: dict[str, dict[str, object]] = {r["record_id"]: r for r in raw_list if "record_id" in r}

    now = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, object]] = []
    for camp in camps:
        raw = by_id.get(camp.record_id)
        if not raw:
            print(f"  [batch] model skipped {camp.record_id!r} — will retry next run", file=sys.stderr)
            continue
        raw = _apply_triage_guardrails(camp, raw)
        results.append({
            "evaluated_at": now,
            "provider": config.provider,
            "model": config.model,
            "record_id": camp.record_id,
            "name": camp.display_name or camp.name,
            "website_url": camp.website_url,
            "verdict": raw.get("verdict"),
            "confidence": raw.get("confidence"),
            "reason": raw.get("reason"),
            "exclusion_reason": raw.get("exclusion_reason"),
            "signals": raw.get("signals") or [],
        })
    return results


def _emit_jsonl(rows: Iterable[dict[str, object]], output_path: str) -> None:
    if output_path == "-":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Triage catalog records with a local or remote LLM")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="SQLAlchemy database URL")
    parser.add_argument(
        "--provider",
        choices=["openai-compatible", "openrouter", "llama-cpp", "cloudflare-workers-ai", "gemini"],
        default="openai-compatible",
        help="Inference provider. 'openrouter' uses https://openrouter.ai/api/v1 with OPENROUTER_API_KEY env var. 'gemini' uses Google Generative AI REST API with GEMINI_API_KEY.",
    )
    parser.add_argument("--model", required=True, help="Model name for the selected provider")
    parser.add_argument("--base-url", help="Base URL for an OpenAI-compatible server, e.g. http://127.0.0.1:8080/v1")
    parser.add_argument("--api-key", help="API key for the selected provider")
    parser.add_argument("--cloudflare-account-id", help="Cloudflare account ID override")
    parser.add_argument("--no-think", action="store_true", help="Pass think=false to Ollama (disables qwen3 extended thinking for faster results)")
    parser.add_argument("--no-flag", dest="flag_excluded", action="store_false", help="Skip writing is_excluded=True back to DB (flagging is on by default)")
    parser.set_defaults(flag_excluded=True)
    parser.add_argument("--retriage", action="store_true", help="Re-run triage on records that already have a triage_verdict (default: skip already-triaged)")
    parser.add_argument("--record-id", help="Single record_id to evaluate")
    parser.add_argument("--website-host", help="Only evaluate records whose website contains this host")
    parser.add_argument("--candidate-only", action="store_true", help="Limit to likely candidate-style records")
    parser.add_argument("--limit", type=int, default=25, help="Maximum records to evaluate")
    parser.add_argument("--delay", type=float, default=1.0, metavar="SECONDS", help="Seconds to sleep between requests to avoid overloading the local inference server (default: 1.0, set 0 to disable)")
    parser.add_argument("--workers", type=int, default=1, metavar="N", help="Number of parallel worker threads (default: 1; use 4-8 for Cloudflare Workers AI)")
    parser.add_argument("--batch-size", type=int, default=1, metavar="N", help="Records per LLM request (default: 1). Use 10-20 for faster throughput; model must support JSON array output.")
    parser.add_argument(
        "--output",
        default="-",
        help="Output JSONL path, or - for stdout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    engine = create_engine(_normalize_db_url(args.db_url))
    Session = sessionmaker(bind=engine)
    ensure_runtime_schema(engine)

    # --- Phase 1: load records then immediately release the DB connection ---
    with Session() as read_session:
        camps = _camp_query(read_session, args)
        if not camps:
            print("No matching camps found.", file=sys.stderr)
            return 1
        # Detach objects so they remain accessible after the session closes
        read_session.expunge_all()
    # DB connection is released here; no idle-in-transaction while inference runs

    ordered_ids = [c.record_id for c in camps]

    if args.provider == "openrouter":
        resolved_base_url = args.base_url or "https://openrouter.ai/api/v1"
        resolved_api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY")
        if not resolved_api_key:
            print("ERROR: --provider openrouter requires OPENROUTER_API_KEY env var or --api-key", file=sys.stderr)
            return 1
    elif args.provider == "gemini":
        resolved_base_url = None
        resolved_api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_api_key:
            print("ERROR: --provider gemini requires GEMINI_API_KEY env var or --api-key", file=sys.stderr)
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
        no_think=getattr(args, "no_think", False),
    )

    # --- Phase 2 + 3: inference with incremental persist ---
    # Each result is written to JSONL and DB immediately so nothing is lost on crash.
    import threading

    _persist_lock = threading.Lock()
    written_count = 0
    flagged_count = 0
    error_count = 0
    total = len(camps)

    def _persist_result(result: dict[str, object]) -> None:
        nonlocal written_count, flagged_count
        record_id = result["record_id"]
        now = datetime.now(timezone.utc)
        should_flag = (
            args.flag_excluded
            and result.get("verdict") == "likely_not_a_camp"
            and result.get("confidence") in ("high", "medium")
        )

        with _persist_lock:
            # Append to JSONL immediately
            _emit_jsonl([result], args.output)

            # Write to DB immediately
            with Session() as ws:
                camp = ws.query(Camp).filter_by(record_id=record_id).one_or_none()
                if camp:
                    camp.triage_verdict = result.get("verdict")
                    camp.triage_confidence = result.get("confidence")
                    camp.triage_reason = result.get("reason")
                    camp.triaged_at = now
                    camp.triage_model = config.model
                    if should_flag:
                        camp.is_excluded = True
                        camp.exclusion_reason = (result.get("exclusion_reason") or "not_a_camp")[:128]
                        flagged_count += 1
                    written_count += 1
                ws.commit()

    batch_size = args.batch_size
    batches = [camps[i : i + batch_size] for i in range(0, len(camps), batch_size)]

    def _process_batch(batch: list[Camp]) -> list[dict[str, object]]:
        if batch_size == 1:
            return [_triage_record(config, batch[0])]
        results = _triage_batch(config, batch)
        # Retry unclear results individually with full context
        by_id = {r["record_id"]: r for r in results}
        camp_by_id = {c.record_id: c for c in batch}
        final = []
        for r in results:
            if r.get("verdict") == "unclear":
                camp = camp_by_id[r["record_id"]]
                print(f"  [retry-unclear] {camp.record_id!r} — retrying with full context", file=sys.stderr)
                r = _triage_record(config, camp)
            final.append(r)
        return final

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(_process_batch, batch): batch for batch in batches}
            for future in as_completed(futures):
                batch = futures[future]
                try:
                    results = future.result()
                except Exception as exc:
                    error_count += len(batch)
                    for camp in batch:
                        print(f"{camp.record_id}: ERROR - {exc}", file=sys.stderr)
                    continue
                for result in results:
                    _persist_result(result)
                    print(
                        f"[{written_count}/{total}] {result['record_id']}: "
                        f"{result.get('verdict')} ({result.get('confidence')}) - {result.get('reason')}",
                        file=sys.stderr,
                    )
    else:
        for i, batch in enumerate(batches):
            if i > 0 and args.delay > 0:
                time.sleep(args.delay)
            try:
                results = _process_batch(batch)
            except Exception as exc:
                error_count += len(batch)
                for camp in batch:
                    print(f"{camp.record_id}: ERROR - {exc}", file=sys.stderr)
                continue
            for result in results:
                _persist_result(result)
                print(
                    f"[{written_count}/{total}] {result['record_id']}: "
                    f"{result.get('verdict')} ({result.get('confidence')}) - {result.get('reason')}",
                    file=sys.stderr,
                )

    print(f"\n[done] {written_count} written, {error_count} errors, {flagged_count} flagged excluded.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
