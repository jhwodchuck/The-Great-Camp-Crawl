# Discovery Save Contract

## Source of truth

The production PostgreSQL database on Neon is the source of truth.
Do not write JSONL staging files. Write directly to the database.

## How to write new candidates to the DB

### Option A: Use the import script with a staging file (batch)

```bash
source .venv/bin/activate
source .vercel/.env.production.local

# Write candidates to a temp staging file
python3 -c "
import json, sys
candidates = [...]  # your candidate list
with open('data/staging/discovered-candidates.jsonl', 'w') as f:
    for c in candidates:
        f.write(json.dumps(c) + '\n')
"

# Import to DB
python scripts/import_dossiers_to_db.py --db-url "$RESEARCH_UI_DATABASE_URL"

# Clean up
rm data/staging/discovered-candidates.jsonl
```

### Option B: Direct DB insert (single records)

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 << 'EOF'
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path("apps/research-ui/backend")))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Camp, CampSource
from schema_runtime import ensure_runtime_schema

engine = create_engine(os.environ["RESEARCH_UI_DATABASE_URL"])
ensure_runtime_schema(engine)
Session = sessionmaker(bind=engine)
session = Session()

camp = Camp(
    record_id="my-new-record-id",
    name="Camp Name",
    country="US",
    region="TX",
    city="Austin",
    website_url="https://example.com",
    source=CampSource.discovery_pipeline,
    draft_status="candidate_pending",
)
existing = session.query(Camp).filter_by(record_id=camp.record_id).first()
if not existing:
    session.add(camp)
    session.commit()
    print(f"Inserted: {camp.record_id}")
else:
    print(f"Already exists: {camp.record_id}")
session.close()
EOF
```

## Deduplication

Before inserting, always check if a record already exists by:
1. `record_id` exact match
2. `website_url` match (normalized, lowercase, trailing slash stripped)
3. Name + city + region fuzzy match

## Do not

- Save JSONL files as permanent artifacts
- Create reports/discovery/ files
- Leave staging files behind after import
