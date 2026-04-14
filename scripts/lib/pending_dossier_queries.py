from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from lib.common import compact_whitespace
from lib.url_utils import extract_host, normalize_url


DEFAULT_INCLUDE_REASONS = (
    "pending_venue_confirmation",
    "unknown_venue",
    "unknown_city",
)

DEFAULT_EXCLUDE_RECORD_BASES = ("multi_venue_candidate",)

UNKNOWN_TOKENS = (
    "unknown",
    "pending",
    "to be confirmed",
    "tbd",
    "venue to be confirmed",
    "city to be confirmed",
)


def is_placeholder(value: str | None) -> bool:
    text = compact_whitespace(value or "").lower()
    if not text:
        return True
    return any(token in text for token in UNKNOWN_TOKENS)


def normalize_host(url: str | None) -> str | None:
    if not url:
        return None
    normalized = normalize_url(url)
    host = extract_host(normalized)
    return host or None


def build_queries_for_record(record: dict[str, Any], current_year: int | None = None) -> list[str]:
    year = current_year or datetime.now(timezone.utc).year
    name = compact_whitespace(str(record.get("name") or ""))
    city = compact_whitespace(str(record.get("city") or ""))
    region = compact_whitespace(str(record.get("region") or ""))
    host = normalize_host(str(record.get("canonical_url") or ""))
    scope_terms = [f'"{name}"']
    if not is_placeholder(city):
        scope_terms.append(city)
    if not is_placeholder(region):
        scope_terms.append(region)

    queries: list[str] = []
    for trailing in ["location", "address", f"summer {year}"]:
        parts = [*scope_terms, trailing]
        if host:
            parts.insert(0, f"site:{host}")
        query = compact_whitespace(" ".join(part for part in parts if part))
        if query and query not in queries:
            queries.append(query)
    return queries


def build_pending_query_pack(
    rows: list[dict[str, Any]],
    include_reasons: tuple[str, ...] = DEFAULT_INCLUDE_REASONS,
    exclude_record_bases: tuple[str, ...] = DEFAULT_EXCLUDE_RECORD_BASES,
    current_year: int | None = None,
) -> dict[str, Any]:
    manifest_rows: list[dict[str, Any]] = []
    query_map: dict[str, dict[str, Any]] = {}
    reason_counts: Counter[str] = Counter()
    record_basis_counts: Counter[str] = Counter()

    include_set = set(include_reasons)
    exclude_bases = set(exclude_record_bases)
    for record in sorted(rows, key=lambda item: str(item.get("candidate_id") or "")):
        record_basis = str(record.get("record_basis") or "")
        if record_basis in exclude_bases:
            continue
        reasons = [str(reason) for reason in (record.get("reasons") or [])]
        matched_reasons = [reason for reason in reasons if reason in include_set]
        if not matched_reasons:
            continue
        queries = build_queries_for_record(record, current_year=current_year)
        if not queries:
            continue
        candidate_id = str(record.get("candidate_id") or "")
        name = compact_whitespace(str(record.get("name") or ""))
        host = normalize_host(str(record.get("canonical_url") or ""))
        manifest_rows.append(
            {
                "candidate_id": candidate_id,
                "name": name,
                "city": record.get("city"),
                "region": record.get("region"),
                "country": record.get("country"),
                "canonical_url": record.get("canonical_url"),
                "host": host,
                "record_basis": record_basis,
                "matched_reasons": matched_reasons,
                "queries": queries,
            }
        )
        reason_counts.update(matched_reasons)
        record_basis_counts[record_basis or "unknown"] += 1
        for query in queries:
            entry = query_map.setdefault(
                query,
                {
                    "query": query,
                    "candidate_ids": [],
                    "candidate_names": [],
                    "hosts": [],
                },
            )
            if candidate_id and candidate_id not in entry["candidate_ids"]:
                entry["candidate_ids"].append(candidate_id)
            if name and name not in entry["candidate_names"]:
                entry["candidate_names"].append(name)
            if host and host not in entry["hosts"]:
                entry["hosts"].append(host)

    query_rows = list(query_map.values())
    return {
        "manifest_rows": manifest_rows,
        "query_rows": query_rows,
        "query_lines": [row["query"] for row in query_rows],
        "summary": {
            "selected_records": len(manifest_rows),
            "selected_queries": len(query_rows),
            "reason_counts": dict(reason_counts),
            "record_basis_counts": dict(record_basis_counts),
            "included_reasons": list(include_reasons),
            "excluded_record_bases": list(exclude_record_bases),
        },
    }
