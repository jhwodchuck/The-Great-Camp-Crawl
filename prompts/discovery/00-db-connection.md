# Database Connection

The production database is the source of truth for all camp data.

## Connection

PostgreSQL on Neon. Use the non-pooled URL for scripts and direct queries:

```
RESEARCH_UI_DATABASE_URL — set in .vercel/.env.production.local
```

## Quick DB query (read-only)

```bash
cd /home/jason/gh/The-Great-Camp-Crawl
source .venv/bin/activate
source .vercel/.env.production.local
python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['RESEARCH_UI_DATABASE_URL'])
with engine.connect() as conn:
    for row in conn.execute(text('SELECT country, region, COUNT(*) FROM camps GROUP BY country, region ORDER BY country, region')):
        print(row)
"
```

## Write path

Use the import script to upsert records:

```bash
source .vercel/.env.production.local
python scripts/import_dossiers_to_db.py --db-url "$RESEARCH_UI_DATABASE_URL"
```

## Key tables

- `camps` — all venue records (4,904 as of 2026-04-17)

## Key columns for gap analysis

| Column | Use |
|--------|-----|
| `country` | US, CA, MX |
| `region` | State/province code |
| `program_family` | JSON array of program types |
| `camp_types` | JSON array of camp types |
| `draft_status` | candidate_pending, candidate, draft, multi_venue, sample |
| `triage_verdict` | likely_camp, likely_not_a_camp, unclear, NULL |
| `overnight_confirmed` | Boolean |
| `active_confirmed` | Boolean |
| `website_url` | Primary URL |
| `is_excluded` | Soft-delete flag |
