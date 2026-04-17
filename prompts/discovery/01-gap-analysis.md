# Gap Analysis — DB-First

Run this before any new discovery work to understand what's actually missing.

## Step 1: Query current coverage

```bash
source .venv/bin/activate
source .vercel/.env.production.local

python3 << 'PYEOF'
import os, json
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["RESEARCH_UI_DATABASE_URL"])

with engine.connect() as conn:
    print("=== Coverage by country ===")
    for row in conn.execute(text("""
        SELECT country, COUNT(*) as total,
               SUM(CASE WHEN triage_verdict = 'likely_camp' THEN 1 ELSE 0 END) as triaged_camp,
               SUM(CASE WHEN overnight_confirmed = true THEN 1 ELSE 0 END) as overnight_yes,
               SUM(CASE WHEN is_excluded = true THEN 1 ELSE 0 END) as excluded
        FROM camps GROUP BY country ORDER BY total DESC
    """)):
        print(f"  {row[0]}: {row[1]} total, {row[2]} triaged as camp, {row[3]} overnight confirmed, {row[4]} excluded")

    print("\n=== US states with fewest candidates ===")
    for row in conn.execute(text("""
        SELECT region, COUNT(*) as cnt FROM camps
        WHERE country = 'US' AND (is_excluded IS NULL OR is_excluded = false)
        GROUP BY region ORDER BY cnt ASC LIMIT 20
    """)):
        print(f"  {row[0]}: {row[1]}")

    print("\n=== CA provinces with fewest candidates ===")
    for row in conn.execute(text("""
        SELECT region, COUNT(*) as cnt FROM camps
        WHERE country = 'CA' AND (is_excluded IS NULL OR is_excluded = false)
        GROUP BY region ORDER BY cnt ASC LIMIT 15
    """)):
        print(f"  {row[0]}: {row[1]}")

    print("\n=== MX states with fewest candidates ===")
    for row in conn.execute(text("""
        SELECT region, COUNT(*) as cnt FROM camps
        WHERE country = 'MX' AND (is_excluded IS NULL OR is_excluded = false)
        GROUP BY region ORDER BY cnt ASC LIMIT 15
    """)):
        print(f"  {row[0]}: {row[1]}")

    print("\n=== Program family distribution ===")
    pf_counts = {}
    for (pf_raw,) in conn.execute(text("SELECT program_family FROM camps WHERE program_family IS NOT NULL")):
        try:
            for fam in json.loads(pf_raw):
                pf_counts[fam] = pf_counts.get(fam, 0) + 1
        except: pass
    for fam, cnt in sorted(pf_counts.items(), key=lambda x: -x[1]):
        print(f"  {fam}: {cnt}")

    print("\n=== Draft status distribution ===")
    for row in conn.execute(text("SELECT draft_status, COUNT(*) FROM camps GROUP BY draft_status ORDER BY COUNT(*) DESC")):
        print(f"  {row[0]}: {row[1]}")

    print("\n=== Triage verdict distribution ===")
    for row in conn.execute(text("SELECT triage_verdict, COUNT(*) FROM camps GROUP BY triage_verdict ORDER BY COUNT(*) DESC")):
        print(f"  {row[0] or 'NULL (untriaged)'}: {row[1]}")

    print("\n=== Regions with NULL region code ===")
    null_region = conn.execute(text("SELECT COUNT(*) FROM camps WHERE region IS NULL OR region = ''")).scalar()
    print(f"  {null_region} records with no region")

    print("\n=== Records with no website_url ===")
    no_url = conn.execute(text("SELECT COUNT(*) FROM camps WHERE website_url IS NULL OR website_url = ''")).scalar()
    print(f"  {no_url} records with no URL")
PYEOF
```

## Step 2: Interpret the gaps

After running the query, look for:

1. **Under-covered US states** — large-population states with suspiciously few results (expect 50+ for CA, TX, NY, PA, FL, OH)
2. **Under-covered CA provinces** — ON, QC, BC should have the most
3. **MX coverage** — most Mexican states will legitimately have few overnight camps; focus on populous states (JAL, NLE, CMX, MEX, PUE)
4. **Program family gaps** — check for missing categories: traditional, specialty, sports, arts, music, academic, STEM, family, faith-based, college-pre-college
5. **Untriaged records** — if most records are untriaged, run triage before discovery
6. **Excluded records** — high exclusion rates may indicate noise in a region

## Step 3: Decide whether to do more discovery

Only do additional discovery if:
- A populous region has fewer candidates than expected
- An entire program family is missing or under-represented
- Canada/Mexico coverage is clearly incomplete

Do NOT do more discovery if:
- The issue is untriaged records (run triage instead)
- The issue is unvalidated records (run validation instead)
- Coverage looks reasonable but enrichment is missing (run enrichment instead)
