#!/usr/bin/env python3
"""Apply enrichment JSONL to the DB per-record with short transactions.

Usage: apply_enrichment_jsonl.py /path/to/enrichment.jsonl
"""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import json
import os
import sys

BASE = Path(__file__).resolve().parent
ENRICH_PATH = BASE / "enrich_camps_with_llm.py"
enrich = SourceFileLoader("enrich_mod", str(ENRICH_PATH)).load_module()

from triage_candidates_with_llm import ClientConfig  # type: ignore
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker

JSONL = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/enrichment-append.jsonl")
DB_URL = os.environ.get("RESEARCH_UI_DATABASE_URL") or os.environ.get("DATABASE_URL")

if not DB_URL:
    print("ERROR: DB URL required via env RESEARCH_UI_DATABASE_URL or DATABASE_URL", file=sys.stderr)
    sys.exit(1)

engine = create_engine(enrich._normalize_db_url(DB_URL), poolclass=NullPool)
Session = sessionmaker(bind=engine)

if not JSONL.exists():
    print("No JSONL file found:", JSONL, file=sys.stderr)
    sys.exit(1)

applied = 0
skipped = 0
with JSONL.open(encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            print("Skipping invalid JSON line:", e, file=sys.stderr)
            skipped += 1
            continue

        rid = obj.get("record_id")
        if not rid:
            print("No record_id in enrichment object, skipping", file=sys.stderr)
            skipped += 1
            continue

        meta = {
            "enriched_at": obj.get("enriched_at"),
            "model": obj.get("model"),
            "source_file": obj.get("source_file"),
        }
        result = obj.get("result")
        if result is None:
            print(f"{rid}: no result payload, skipping", file=sys.stderr)
            skipped += 1
            continue

        with Session() as sess:
            camp = sess.query(enrich.Camp).filter_by(record_id=rid).one_or_none()
            if not camp:
                print(f"{rid}: not found in DB, skipping", file=sys.stderr)
                skipped += 1
                continue

            try:
                enrich._apply_enrichment(camp, result, meta)
                sess.commit()
                applied += 1
                print(f"APPLIED {rid}")
            except Exception as e:
                sess.rollback()
                print(f"{rid}: error applying enrichment: {e}", file=sys.stderr)
                skipped += 1

print(f"Done. Applied={applied} Skipped={skipped}")
