# Triage: Classify Untriaged Candidates

Most of the DB is untriaged. Before doing more discovery, run triage on existing records.

## Check untriaged count

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['RESEARCH_UI_DATABASE_URL'])
with engine.connect() as conn:
    total = conn.execute(text('SELECT COUNT(*) FROM camps WHERE triage_verdict IS NULL')).scalar()
    print(f'{total} untriaged records')
    for row in conn.execute(text('''
        SELECT country, region, COUNT(*) FROM camps
        WHERE triage_verdict IS NULL
        GROUP BY country, region ORDER BY COUNT(*) DESC LIMIT 20
    ''')):
        print(f'  {row[0]}-{row[1]}: {row[2]}')
"
```

## Run batch triage

Use the existing triage script:

```bash
source .vercel/.env.production.local
python scripts/triage_candidates_with_llm.py --db-url "$RESEARCH_UI_DATABASE_URL"
```

## Manual triage (single records)

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 << 'EOF'
import os
from sqlalchemy import create_engine, text
from datetime import datetime, timezone

engine = create_engine(os.environ["RESEARCH_UI_DATABASE_URL"])
with engine.begin() as conn:
    conn.execute(text("""
        UPDATE camps SET
            triage_verdict = :verdict,
            triage_confidence = :confidence,
            triage_reason = :reason,
            triage_model = 'human',
            triaged_at = :now
        WHERE record_id = :rid
    """), {
        "verdict": "likely_camp",       # likely_camp | likely_not_a_camp | unclear
        "confidence": 0.9,              # 0.0–1.0
        "reason": "Official website confirms overnight summer camp with cabins",
        "rid": "the-record-id-here",
        "now": datetime.now(timezone.utc),
    })
    print("Updated")
EOF
```

## Triage verdicts

| Verdict | Meaning |
|---------|---------|
| `likely_camp` | Evidence supports overnight/residential program |
| `likely_not_a_camp` | Day camp, non-camp, or defunct |
| `unclear` | Insufficient evidence to decide |

## Priority for triage

1. Records with `draft_status = 'candidate'` or `'draft'` — already promoted, need verdict
2. Records with a website_url — easiest to check
3. Records in under-covered regions — highest impact
