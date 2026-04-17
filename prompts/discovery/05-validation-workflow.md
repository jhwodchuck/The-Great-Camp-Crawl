# Validation Workflow — DB-First

Use this to validate records in the database.

## What needs validation

Only records with `triage_verdict = 'likely_camp'` should be validated.
Validation checks:

1. **Overnight confirmation** — does the program actually include overnight stays?
2. **Venue specificity** — is this tied to a specific physical location?
3. **Recent activity** — has this program operated in the last 24 months?
4. **Duplicate check** — is this a duplicate of another record?

See the detailed validation prompts:

- `prompts/validation/01-overnight-validator.md`
- `prompts/validation/02-venue-validator.md`
- `prompts/validation/03-recent-activity-validator.md`
- `prompts/validation/04-duplicate-reviewer.md`

## Find records needing validation

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['RESEARCH_UI_DATABASE_URL'])
with engine.connect() as conn:
    print('Records triaged as likely_camp but not yet validated:')
    cnt = conn.execute(text('''
        SELECT COUNT(*) FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND overnight_confirmed IS NULL
        AND (is_excluded IS NULL OR is_excluded = false)
    ''')).scalar()
    print(f'  {cnt} need overnight validation')

    cnt = conn.execute(text('''
        SELECT COUNT(*) FROM camps
        WHERE triage_verdict = 'likely_camp'
        AND active_confirmed IS NULL
        AND (is_excluded IS NULL OR is_excluded = false)
    ''')).scalar()
    print(f'  {cnt} need recent-activity validation')
"
```

## Write validation results to DB

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
            overnight_confirmed = :overnight,
            active_confirmed = :active,
            draft_status = :status,
            updated_at = NOW()
        WHERE record_id = :rid
    """), {
        "overnight": True,
        "active": True,
        "status": "draft",  # promote from candidate_pending to draft
        "rid": "the-record-id-here",
    })
    print("Updated")
EOF
```

## Draft status progression

| Status | Meaning |
|--------|---------|
| `candidate_pending` | Discovered, not yet reviewed |
| `candidate` | Reviewed, plausible but unvalidated |
| `draft` | Validated, needs enrichment |
| `multi_venue` | Needs splitting into separate venue records |
| `sample` | Fully complete sample record |
