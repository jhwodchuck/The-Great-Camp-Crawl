#!/usr/bin/env python3
"""Enrich remaining camps locally without writing to the DB.

This script reads a list of record_ids from a checkpoint file, looks up their
Camp rows (read-only), loads cached evidence pages, calls the local LLM via
the same client plumbing, and appends raw enrichment JSON to an output JSONL.
"""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import json
import os
import sys
import time

BASE = Path(__file__).resolve().parent
ENRICH_PATH = BASE / "enrich_camps_with_llm.py"

enrich = SourceFileLoader("enrich_mod", str(ENRICH_PATH)).load_module()

from triage_candidates_with_llm import ClientConfig  # type: ignore
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker

CHECKPOINT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/enrich-checkpoint.txt")
OUTPATH = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/enrichment-append.jsonl")
DB_URL = os.environ.get("RESEARCH_UI_DATABASE_URL") or os.environ.get("DATABASE_URL")
MODEL = os.environ.get("ENRICH_MODEL") or "qwen2.5-coder:7b"
BASE_URL = os.environ.get("ENRICH_BASE_URL") or "http://127.0.0.1:11434/v1"

if not DB_URL:
    print("ERROR: DB URL required via env RESEARCH_UI_DATABASE_URL or DATABASE_URL", file=sys.stderr)
    sys.exit(1)

engine = create_engine(enrich._normalize_db_url(DB_URL), poolclass=NullPool)
Session = sessionmaker(bind=engine)

record_ids = [l.strip() for l in CHECKPOINT.read_text(encoding="utf-8").splitlines() if l.strip()]
if not record_ids:
    print("No record_ids found in checkpoint", file=sys.stderr)
    sys.exit(0)

config = ClientConfig(provider="openai-compatible", model=MODEL, base_url=BASE_URL, api_key=None)

out_path = OUTPATH
out_path.parent.mkdir(parents=True, exist_ok=True)

with out_path.open("a", encoding="utf-8") as out_f:
    for rid in record_ids:
        # Open a fresh session per record to avoid long-running idle transactions
        with Session() as sess:
            camp = sess.query(enrich.Camp).filter_by(record_id=rid).one_or_none()
            if not camp:
                print(f"Skipping {rid}: not found in DB", file=sys.stderr)
                continue

            evidence_text, source_file = enrich._find_evidence_text(camp, Path(enrich.DEFAULT_TEXT_DIR), Path(enrich.DEFAULT_HTML_DIR))
            if not evidence_text:
                print(f"Skipping {rid}: no cached evidence", file=sys.stderr)
                continue

        # Call LLM outside of DB session
        enrichment = None
        max_retries = int(os.environ.get("ENRICH_MAX_RETRIES", "5"))
        for attempt in range(1, max_retries + 1):
            try:
                enrichment = enrich._enrich_one(config, camp, evidence_text, source_file)
                break
            except Exception as e:
                print(f"{rid}: LLM error (attempt {attempt}) — {e}", file=sys.stderr)
                if attempt < max_retries:
                    backoff = min(60, 2 ** attempt)
                    time.sleep(backoff)
                    continue
                enrichment = None

        if enrichment is None:
            print(f"{rid}: failed after {max_retries} attempts", file=sys.stderr)
            continue

        out_f.write(json.dumps(enrichment, ensure_ascii=False) + "\n")
        out_f.flush()
        print(f"WROTE {rid}")

print("Done")
