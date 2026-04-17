# AGENTS

Repository-level instructions for humans and agents working in `The-Great-Camp-Crawl`.

## Purpose

This repository tracks **overnight and residential youth programs** across:

- United States
- Canada
- Mexico

Included families:

- traditional overnight camps
- specialty camps
- sports camps
- arts camps
- music and band camps
- academic and STEM camps
- family camps
- faith-based camps and retreats
- college-run pre-college residential programs

## Source of Truth

The **production PostgreSQL database** (Neon) is the source of truth for all camp data.

- ~4,900 records as of April 2025
- Connection string: stored as `DATABASE_URL` in `.vercel/.env.production.local`
- Scripts expect `RESEARCH_UI_DATABASE_URL` — see bootstrap snippet below
- Read/write via SQLAlchemy or raw SQL
- See `prompts/discovery/00-db-connection.md` for connection details

Do **not** use JSONL staging files as long-term data stores. The DB is canonical.

## Core Rules

1. One final record per **physical venue or session location**.
2. Do not mark a program as qualifying without evidence of **overnight** or **residential** participation.
3. Do not create a final record without evidence of activity in the **last 24 months**.
4. Preserve ambiguity instead of inventing facts.
5. Preserve non-English sources during discovery.
6. Do not collapse multi-venue operators into a fake single-venue record.

## Standard Workflows

### 1. Assess coverage gaps (start here)

Before any new discovery, check what's in the DB.

**Bootstrap (run once per shell session):**

```bash
source .venv/bin/activate
source .vercel/.env.production.local
# .env.production.local exports DATABASE_URL; scripts expect RESEARCH_UI_DATABASE_URL
export RESEARCH_UI_DATABASE_URL="$DATABASE_URL"
```

Then follow `prompts/discovery/01-gap-analysis.md`.

### 2. Triage untriaged records

Most records are untriaged. Run triage before doing more discovery:

```bash
python scripts/triage_candidates_with_llm.py --db-url "$RESEARCH_UI_DATABASE_URL"
```

See `prompts/discovery/03-triage.md`.

### 3. Find new candidates (only if gaps exist)

Use script-based search (SearXNG preferred) or web search as backup:

```bash
# SearXNG (preferred)
docker start searxng
python scripts/search_searxng.py \
  "overnight residential summer camp" \
  --country US --region TX \
  --output data/staging/temp-discovery.jsonl

# Import to DB and clean up
python scripts/import_dossiers_to_db.py --db-url "$RESEARCH_UI_DATABASE_URL"
rm -f data/staging/temp-discovery.jsonl
```

See `prompts/discovery/02-find-candidates.md`.

### 4. Validate and enrich

After triage, validate overnight status and enrich with pricing/duration/contact:

- `prompts/discovery/04-enrichment-workflow.md`
- `prompts/discovery/05-validation-workflow.md`

### 5. Import dossier markdown files

If camp dossiers exist as `.md` files under `camps/`:

```bash
python scripts/import_dossiers_to_db.py --db-url "$RESEARCH_UI_DATABASE_URL"
```

## Main Scripts

- `scripts/import_dossiers_to_db.py` — upsert camps to DB from markdown + JSONL
- `scripts/triage_candidates_with_llm.py` — LLM-based triage of candidates
- `scripts/run_discovery_pipeline.py` — full discovery pipeline
- `scripts/search_searxng.py` — preferred high-recall search via local SearXNG
- `scripts/search_duckduckgo.py` — DDG fallback when SearXNG is unavailable
- `scripts/run_enrichment_pipeline.py` — batch enrichment
- `scripts/html_to_markdown.py` — convert captured HTML to markdown
- `scripts/capture_to_evidence_index.py` — index evidence pages

## Search Guidance

### Preferred provider: SearXNG

SearXNG running locally at `http://localhost:8080`. Start with `docker start searxng`.

### Fallback: DuckDuckGo

Use when SearXNG is unavailable. Default chain: `instant_answer` → `lite_html`.

## Prompt Structure

All discovery/workflow prompts are in `prompts/discovery/`:

| File | Purpose |
|------|---------|
| `00-db-connection.md` | Database connection and query reference |
| `00-save-contract.md` | How to write new records to the DB |
| `01-gap-analysis.md` | Assess current coverage gaps |
| `02-find-candidates.md` | Find new candidates via search |
| `03-triage.md` | Classify untriaged records |
| `04-enrichment-workflow.md` | Enrich records with pricing, duration, etc. |
| `05-validation-workflow.md` | Validate overnight status, venue, activity |

System rules (grounding, dedup, naming, quality bar) remain in `prompts/system/`.
Enrichment detail prompts remain in `prompts/enrichment/`.
Validation detail prompts remain in `prompts/validation/`.

## Canonical Paths

- Final venue dossiers: `camps/<country>/<region>/`
- Seed queries: `data/seed-queries/`
- Prompt templates: `prompts/`
- Backend/API: `apps/research-ui/backend/`

## When Editing Records

- Write to the DB, not to JSONL files.
- Use `scripts/import_dossiers_to_db.py` for batch imports.
- Check for duplicates before inserting (by URL, name+city+region).
- If a candidate is multi-venue, split it into separate records.

## Validation and Enrichment Boundary

Discovery-stage records may still be ambiguous. Do not force a candidate into validated status just because it looks plausible. Run triage → validation → enrichment in order.

## Current Pipeline Status

The DB contains ~4,900 records. Most are untriaged (`candidate_pending`). Priority work:

1. **Triage** — classify untriaged records as likely_camp/likely_not/unclear
2. **Validate** — confirm overnight status for likely_camp records
3. **Enrich** — add pricing, duration, age range, contact info
4. **Gap fill** — only after triage reveals actual coverage gaps

If behavior in docs and scripts diverges, update this file and the corresponding docs together.
