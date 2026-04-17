#!/usr/bin/env python3
"""Dump the full enrichment chat payload for a single record to a JSON file.

Usage: dump_enrichment_payload.py <record_id> [output.json]
"""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import json
import os
import sys

BASE = Path(__file__).resolve().parent
ENRICH_PATH = BASE / "enrich_camps_with_llm.py"
enrich = SourceFileLoader("enrich_mod", str(ENRICH_PATH)).load_module()

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get("RESEARCH_UI_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not DB_URL:
    print("ERROR: DB URL required via env RESEARCH_UI_DATABASE_URL or DATABASE_URL", file=sys.stderr)
    sys.exit(1)

engine = create_engine(enrich._normalize_db_url(DB_URL), poolclass=NullPool)
Session = sessionmaker(bind=engine)

record_id = sys.argv[1] if len(sys.argv) > 1 else None
out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/ollama_enrich_payload.json")

if not record_id:
    print("Usage: dump_enrichment_payload.py <record_id> [output.json]", file=sys.stderr)
    sys.exit(2)

with Session() as sess:
    Camp = enrich.Camp
    camp = sess.query(Camp).filter_by(record_id=record_id).one_or_none()
    if not camp:
        print(f"Record not found: {record_id}", file=sys.stderr)
        sys.exit(1)

    evidence_text, source_file = enrich._find_evidence_text(camp, Path(enrich.DEFAULT_TEXT_DIR), Path(enrich.DEFAULT_HTML_DIR))
    if not evidence_text:
        print(f"No cached evidence for: {record_id}", file=sys.stderr)
        sys.exit(1)

    user_prompt = enrich._build_enrichment_prompt(camp, evidence_text)
    payload = {
        "model": os.environ.get("ENRICH_MODEL", "qwen2.5-coder:7b"),
        "messages": [
            {"role": "system", "content": enrich.ENRICHMENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {out_path}")
