#!/usr/bin/env python3
"""Fetch HTML/Markdown evidence pages for camps triaged as likely_camp.

Reads Camp records from the DB where triage_verdict = 'likely_camp', then
fetches each website_url through the standard capture pipeline (same
output layout as capture_candidate_evidence.py).

Examples:
    # Default: 2s delay between requests, skip already-captured pages
    python scripts/capture_triaged_camps.py --run-id triaged-camps-2026-04

    # Faster with a shorter delay, limit to first 100
    python scripts/capture_triaged_camps.py \\
      --run-id triaged-camps-us --delay 1.0 --limit 100

    # Include unclear verdicts too
    python scripts/capture_triaged_camps.py \\
      --run-id triaged-camps-full --verdict likely_camp --verdict unclear

    # Re-capture already-captured pages
    python scripts/capture_triaged_camps.py \\
      --run-id triaged-recapture --no-skip-existing
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "research-ui" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from models import Camp  # noqa: E402
from schema_runtime import ensure_runtime_schema  # noqa: E402

from lib.capture_pipeline import capture_urls  # noqa: E402
from lib.url_utils import normalize_url  # noqa: E402

DEFAULT_TEXT_DIR = Path("data/raw/evidence-pages/text")
DEFAULT_HTML_DIR = Path("data/raw/evidence-pages/html")
DEFAULT_MANIFEST_DIR = Path("data/raw/evidence-pages/manifests")

DEFAULT_DB_URL = (
    os.environ.get("RESEARCH_UI_DATABASE_URL")
    or os.environ.get("DATABASE_URL_UNPOOLED")
    or os.environ.get("DATABASE_URL")
    or f"sqlite:///{BACKEND_DIR / 'research.db'}"
)


def _normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql+psycopg://"):
        return db_url
    if db_url.startswith("postgres://"):
        return "postgresql+psycopg://" + db_url[len("postgres://"):]
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url[len("postgresql://"):]
    return db_url


def _load_covered_urls(manifest_dir: Path) -> set[str]:
    """Return all source_url / resolved_url values already in any manifest."""
    covered: set[str] = set()
    for manifest_path in manifest_dir.glob("*.jsonl"):
        try:
            for line in manifest_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for key in ("source_url", "resolved_url"):
                    val = normalize_url(str(row.get(key) or ""))
                    if val:
                        covered.add(val)
        except OSError:
            continue
    return covered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture HTML/Markdown evidence for camps triaged as likely_camp"
    )
    parser.add_argument("--run-id", required=True, help="Stable run id for manifest filename")
    parser.add_argument(
        "--verdict",
        action="append",
        default=[],
        dest="verdicts",
        help="Triage verdict(s) to include (default: likely_camp). Repeat to add more.",
    )
    parser.add_argument(
        "--include-untriaged",
        action="store_true",
        help="Also include records with no triage verdict (e.g. pre-existing dossier imports).",
    )
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--text-dir", default=str(DEFAULT_TEXT_DIR))
    parser.add_argument("--html-dir", default=str(DEFAULT_HTML_DIR))
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--country", action="append", default=[], help="Filter by country code (e.g. US)")
    parser.add_argument("--region", action="append", default=[], help="Filter by region/state code (e.g. TX)")
    parser.add_argument("--limit", type=int, help="Stop after N URLs fetched")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds to sleep between requests (default: 2.0)")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout per request in seconds")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=2.0)
    parser.add_argument("--no-skip-existing", action="store_true", help="Re-fetch already-captured pages")
    parser.add_argument("--dry-run", action="store_true", help="Print selected URLs without fetching")
    args = parser.parse_args()

    verdicts = args.verdicts or ["likely_camp"]

    db_url = _normalize_db_url(args.db_url)
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
    ensure_runtime_schema(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with Session() as session:
        verdict_filter = Camp.triage_verdict.in_(verdicts)
        if args.include_untriaged:
            verdict_filter = or_(verdict_filter, Camp.triage_verdict.is_(None))

        query = (
            session.query(Camp)
            .filter(
                verdict_filter,
                or_(Camp.is_excluded.is_(False), Camp.is_excluded.is_(None)),
                Camp.website_url.isnot(None),
                Camp.website_url != "",
            )
        )
        if args.country:
            query = query.filter(Camp.country.in_([c.upper() for c in args.country]))
        if args.region:
            query = query.filter(Camp.region.in_([r.upper() for r in args.region]))

        camps: list[Camp] = query.order_by(Camp.record_id).all()

    print(f"Found {len(camps)} triaged camp records with verdicts: {verdicts}")

    manifest_dir = Path(args.manifest_dir)
    manifest_path = manifest_dir / f"{args.run_id}.jsonl"

    covered_urls: set[str] = set()
    if not args.no_skip_existing:
        covered_urls = _load_covered_urls(manifest_dir)
        print(f"Already captured: {len(covered_urls)} URLs (will skip)")

    # Deduplicate by normalized URL
    seen: set[str] = set()
    selected: list[dict[str, Any]] = []
    for camp in camps:
        url = normalize_url(camp.website_url or "")
        if not url:
            continue
        if url in seen:
            continue
        if not args.no_skip_existing and url in covered_urls:
            continue
        seen.add(url)
        selected.append({"record_id": camp.record_id, "name": camp.name, "url": url})
        if args.limit and len(selected) >= args.limit:
            break

    print(f"Selected {len(selected)} URLs to fetch")

    if args.dry_run:
        for row in selected:
            print(f"  {row['url']}  ({row['record_id']})")
        return 0

    if not selected:
        print("Nothing to fetch.")
        return 0

    result = capture_urls(
        urls=[row["url"] for row in selected],
        text_dir=Path(args.text_dir),
        html_dir=Path(args.html_dir),
        manifest_path=manifest_path,
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        sleep_seconds=args.delay,
        skip_existing=not args.no_skip_existing,
    )

    counts = result.get("counts", {})
    print(
        f"\nDone. captured={counts.get('captured', '?')}  "
        f"unchanged={counts.get('unchanged', '?')}  "
        f"skipped={counts.get('skipped_existing', '?')}  "
        f"failed={counts.get('failed', '?')}"
    )
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
