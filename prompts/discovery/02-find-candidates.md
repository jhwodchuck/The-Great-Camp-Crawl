# Discovery: Find New Candidates

Use this prompt when the gap analysis shows a region or program family is under-covered.

## Prerequisites

1. Run the gap analysis (01-gap-analysis.md) first
2. Confirm the gap is real (not just untriaged records)
3. Know the target: country, region, and/or program family

## Method 1: Script-based discovery (preferred)

Use SearXNG for deterministic, high-recall search:

```bash
source .venv/bin/activate

# Start SearXNG if not running
docker start searxng

# Run a targeted search
python scripts/search_searxng.py \
  "overnight residential summer camp" \
  --country US --region TX \
  --output data/staging/temp-discovery.jsonl

# Or use the full pipeline
python scripts/run_discovery_pipeline.py \
  "site:.edu pre-college residential program" \
  --run-id us-tx-precollege-fill \
  --country US \
  --region TX \
  --program-family college-pre-college
```

After script-based discovery, import results and clean up:

```bash
source .vercel/.env.production.local
python scripts/import_dossiers_to_db.py --db-url "$RESEARCH_UI_DATABASE_URL"
rm -f data/staging/temp-discovery.jsonl
```

## Method 2: Web search (backup)

When SearXNG is unavailable or you need to fill specific gaps manually:

1. Use web search to find candidates
2. Check each against the DB before adding (avoid duplicates)
3. Write directly to the DB using the save contract (00-save-contract.md)

### Effective search queries by program type

| Program Family | Search Queries |
|---------------|---------------|
| Traditional overnight | `"overnight camp" OR "sleepaway camp" [state]` |
| College pre-college | `site:.edu "pre-college" OR "summer residential" [state]` |
| Sports | `"residential sports camp" OR "overnight sports camp" [state]` |
| Arts/music | `"residential arts program" OR "overnight music camp" [state]` |
| STEM/academic | `"residential STEM camp" OR "overnight science camp" [state]` |
| Faith-based | `"church camp" OR "faith camp" overnight residential [state]` |
| Family camp | `"family camp" overnight residential [state]` |
| Canada (French) | `"camp résidentiel" OR "camp d'été avec hébergement" [province]` |
| Mexico (Spanish) | `"campamento residencial" OR "campamento de verano con hospedaje" [state]` |

### Dedup check before adding

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['RESEARCH_UI_DATABASE_URL'])
with engine.connect() as conn:
    # Check by URL
    rows = list(conn.execute(text(\"SELECT record_id, name FROM camps WHERE website_url ILIKE :url\"), {'url': '%example.com%'}))
    for r in rows: print(r)
    # Check by name
    rows = list(conn.execute(text(\"SELECT record_id, name FROM camps WHERE name ILIKE :name\"), {'name': '%Camp Happy%'}))
    for r in rows: print(r)
"
```

## Candidate record shape

New candidates written to the DB should have at minimum:

| Field | Required | Notes |
|-------|----------|-------|
| `record_id` | Yes | Slug: `cand-{country}-{region}-{city}-{name-slug}` |
| `name` | Yes | Full program name |
| `country` | Yes | US, CA, or MX |
| `region` | Yes | State/province code |
| `website_url` | Yes | Official URL |
| `source` | Yes | `discovery_pipeline` |
| `draft_status` | Yes | `candidate_pending` |
| `program_family` | Recommended | JSON array |
| `city` | Recommended | |
| `operator_name` | If known | |
| `overnight_confirmed` | If known | Boolean |

## Hard rules

- Do not add a record without a usable URL
- Do not add a record you cannot verify has overnight/residential participation
- Check the DB for duplicates before inserting
- One record = one physical venue or session location
- Use `null` for unknown fields, not guesses
