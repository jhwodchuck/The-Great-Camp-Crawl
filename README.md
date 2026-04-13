# The Great Camp Crawl

The Great Camp Crawl is a breadth-first research project for finding, validating, enriching, and browsing **overnight child and teen programs** across the **United States, Canada, and Mexico**.

This repository is designed to support yearly research for one child while still building a reusable multi-year knowledge base.

## Scope

Included program families:
- traditional summer camps
- specialty camps
- sports camps
- arts camps
- academic camps
- band and music camps
- church and religious retreats or camps
- family camps
- college-run pre-college residential programs

Current priorities:
- **maximum breadth first**
- **one file per physical location or session venue**
- **college-run pre-college residential programs get extra focus**
- **one-week-or-longer programs get extra focus**
- only include programs with evidence of activity in the **past 24 months**

## Repository layout

```text
assets/                  Branding and UI assets
camps/                   Final Markdown dossiers, one per venue
data/raw/                Raw evidence captures, notes, and discovery-run artifacts
data/staging/            Candidate and workflow queue files
data/normalized/         Structured exported records
reports/                 Coverage, validation, and enrichment summaries
prompts/system/          Grounding, schema, naming, quality, dedupe rules
prompts/discovery/       Discovery-agent prompts
templates/               Camp dossier and index templates
docs/                    MkDocs site content
scripts/                 Validation and build helpers
mkdocs.yml               Docs configuration
```

## Canonical record policy

- One Markdown file per **physical venue or session location**.
- Keep **raw evidence** and **discovery notes** for auditability.
- Do not reject non-English camps at discovery time.
- Pricing is expected in the final knowledge base but can be added in later enrichment passes.

## Recommended workflow

1. Run the deterministic raw discovery pipeline by country, region, and program family.
2. Review normalized candidates and follow-up queues in `reports/discovery/` and `data/staging/discovery-runs/`.
3. Validate overnight status, venue identity, and recent activity.
4. Enrich pricing, duration, age ranges, contact details, and taxonomy.
5. Render a final dossier into `camps/...`.
6. Publish browsable documentation through MkDocs.

## Deterministic discovery pipeline

The repository now supports a code-first raw ingestion path for:

- seed discovery through DuckDuckGo Instant Answer
- HTML capture and Markdown evidence preservation
- evidence indexing
- candidate normalization into repo schema
- deterministic follow-up queue generation
- multi-venue split-task generation
- run summaries and staging outputs

LLMs are still useful later for validation, enrichment review, and final dossier drafting, but the raw gathering path does not require prompts.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements-discovery.txt
```

## Quick start

Run the full pipeline for a small scoped pass:

```bash
python scripts/run_discovery_pipeline.py \
  "site:.edu pre-college residential program" \
  --run-id us-college-precollege-seed \
  --country US \
  --region MA \
  --program-family college-pre-college
```

Search only:

```bash
python scripts/search_duckduckgo.py \
  "site:.edu pre-college residential program" \
  --output reports/discovery/manual_seed_raw.jsonl \
  --query-log data/raw/discovery-runs/manual_seed/queries.jsonl \
  --country US \
  --program-family college-pre-college
```

Normalize an existing discovery report and generate queues:

```bash
python scripts/normalize_existing_discovery_report.py \
  reports/discovery/us_candidates_2026-04-13.jsonl \
  --output reports/discovery/us_candidates_2026-04-13_normalized.jsonl

python scripts/generate_followup_queue.py \
  reports/discovery/us_candidates_2026-04-13_normalized.jsonl \
  --output reports/discovery/us_candidates_2026-04-13_followup_queue.jsonl

python scripts/split_multi_venue_candidates.py \
  reports/discovery/us_candidates_2026-04-13_normalized.jsonl \
  --output reports/discovery/us_candidates_2026-04-13_split_queue.jsonl \
  --skeleton-output reports/discovery/us_candidates_2026-04-13_split_stubs.jsonl
```

Run tests:

```bash
python -m pytest -q
```

## Run outputs

A pipeline run writes to:

```text
data/raw/discovery-runs/<run-id>/queries.jsonl
data/raw/discovery-runs/<run-id>/search_results.jsonl
data/raw/discovery-runs/<run-id>/capture_manifest.jsonl
data/raw/discovery-runs/<run-id>/run.json
data/raw/evidence-pages/html/*.html
data/raw/evidence-pages/text/*.md
reports/discovery/<run-id>_raw.jsonl
reports/discovery/<run-id>_normalized.jsonl
reports/discovery/<run-id>_followup_queue.jsonl
reports/discovery/<run-id>_split_queue.jsonl
reports/discovery/<run-id>_evidence_index.jsonl
reports/discovery/<run-id>_summary.json
data/staging/discovery-runs/<run-id>/discovered_candidates.jsonl
data/staging/discovery-runs/<run-id>/followup_queue.jsonl
data/staging/discovery-runs/<run-id>/split_queue.jsonl
data/normalized/evidence_index.jsonl
```

## Search-layer limitations

- DuckDuckGo Instant Answer is a seed-discovery layer, not a complete search engine.
- Expect false negatives; broad recall still needs multiple reruns, geography slices, family slices, and later supplemental sources.
- The pipeline preserves ambiguity instead of inventing venue certainty or overnight status.
- Non-English sources should still be kept when found; discovery should not discard Spanish or French material.

## Docs site

This repo is scaffolded for **MkDocs Material** so the Markdown findings can be browsed like a lightweight documentation site.

Typical local setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install mkdocs-material pyyaml
mkdocs serve
```

## Important reference files

- `prompts/system/GROUNDING_RULES.md`
- `prompts/system/OUTPUT_SCHEMA.md`
- `prompts/system/NAMING_CONVENTIONS.md`
- `templates/camp.md`

## Naming convention

Recommended filename pattern:

```text
[camp-slug]--[country]-[region]-[city]-[venue-slug]--[record-id].md
```

Example:

```text
johns-hopkins-engineering-innovation--us-md-baltimore-homewood-campus--us-md-baltimore-homewood-campus.md
```

## Build intent

This repository is intentionally set up as a research system rather than a loose notes folder. The structure should support:
- discovery-agent swarms
- multi-stage enrichment
- QA and stale-record review
- yearly reuse and filtering for a specific child later

## Near-term next steps

- expand supplemental seed sources beyond DuckDuckGo Instant Answer
- improve venue splitting against official multi-campus program pages
- deepen enrichment and validation automation on top of the deterministic raw corpus
- add more sample venue dossiers and docs browsing helpers
