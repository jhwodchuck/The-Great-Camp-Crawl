# Enrichment Workflow — DB-First

Use this prompt to find records that need enrichment and run enrichment tasks.

## Step 1: Find records needing enrichment

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 << 'PYEOF'
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["RESEARCH_UI_DATABASE_URL"])

with engine.connect() as conn:
    print("=== Records missing pricing ===")
    no_price = conn.execute(text("""
        SELECT COUNT(*) FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND (pricing_min IS NULL AND pricing_max IS NULL)
        AND (is_excluded IS NULL OR is_excluded = false)
    """)).scalar()
    print(f"  {no_price} records missing pricing")

    print("\n=== Records missing duration ===")
    no_dur = conn.execute(text("""
        SELECT COUNT(*) FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND (duration_min_days IS NULL AND duration_max_days IS NULL)
        AND (is_excluded IS NULL OR is_excluded = false)
    """)).scalar()
    print(f"  {no_dur} records missing duration")

    print("\n=== Records missing age range ===")
    no_age = conn.execute(text("""
        SELECT COUNT(*) FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND (ages_min IS NULL AND ages_max IS NULL)
        AND (is_excluded IS NULL OR is_excluded = false)
    """)).scalar()
    print(f"  {no_age} records missing age range")

    print("\n=== Records missing contact info ===")
    no_contact = conn.execute(text("""
        SELECT COUNT(*) FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND (contact_email IS NULL AND contact_phone IS NULL)
        AND (is_excluded IS NULL OR is_excluded = false)
    """)).scalar()
    print(f"  {no_contact} records missing contact info")

    print("\n=== Records with no overnight confirmation ===")
    no_overnight = conn.execute(text("""
        SELECT COUNT(*) FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND overnight_confirmed IS NULL
        AND (is_excluded IS NULL OR is_excluded = false)
    """)).scalar()
    print(f"  {no_overnight} records not yet validated for overnight")

    print("\n=== Sample records needing enrichment ===")
    for row in conn.execute(text("""
        SELECT record_id, name, website_url, country, region FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND (pricing_min IS NULL AND pricing_max IS NULL)
        AND website_url IS NOT NULL
        AND (is_excluded IS NULL OR is_excluded = false)
        LIMIT 10
    """)):
        print(f"  {row[0]}: {row[1]} ({row[4]}) — {row[2]}")
PYEOF
```

## Step 2: Enrich a record

For each record, visit its `website_url` and gather the data described in the enrichment prompts:

- `prompts/enrichment/01-pricing-enricher.md`
- `prompts/enrichment/02-duration-enricher.md`
- `prompts/enrichment/03-age-grade-enricher.md`
- `prompts/enrichment/04-contact-enricher.md`
- `prompts/enrichment/05-program-taxonomy-enricher.md`

## Step 3: Write enrichment data to DB

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 << 'EOF'
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["RESEARCH_UI_DATABASE_URL"])
with engine.begin() as conn:
    conn.execute(text("""
        UPDATE camps SET
            pricing_currency = :currency,
            pricing_min = :price_min,
            pricing_max = :price_max,
            boarding_included = :boarding,
            duration_min_days = :dur_min,
            duration_max_days = :dur_max,
            ages_min = :age_min,
            ages_max = :age_max,
            contact_email = :email,
            contact_phone = :phone,
            overnight_confirmed = :overnight,
            updated_at = NOW()
        WHERE record_id = :rid
    """), {
        "currency": "USD",
        "price_min": 500,
        "price_max": 3000,
        "boarding": True,
        "dur_min": 7,
        "dur_max": 14,
        "age_min": 8,
        "age_max": 17,
        "email": "info@example.com",
        "phone": "555-123-4567",
        "overnight": True,
        "rid": "the-record-id-here",
    })
    print("Updated")
EOF
```

## Batch enrichment scripts

For larger runs, use the existing enrichment scripts:

```bash
source .vercel/.env.production.local
python scripts/run_enrichment_pipeline.py --db-url "$RESEARCH_UI_DATABASE_URL"
```

## Do not

- Write enrichment JSON files to disk as permanent artifacts
- Enrich records that haven't been triaged yet (triage first)
- Guess values — use `null` for anything not found on the official site
