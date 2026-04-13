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

## Core Rules

1. One final record per **physical venue or session location**.
2. Do not mark a program as qualifying without evidence of **overnight** or **residential** participation.
3. Do not create a final record without evidence of activity in the **last 24 months**.
4. Preserve ambiguity instead of inventing facts.
5. Preserve non-English sources during discovery.
6. Do not collapse multi-venue operators into a fake single-venue record.

## Raw Discovery Policy

Raw discovery and evidence capture should be **code-first and deterministic**.

Use scripts for:

- seed search
- evidence capture
- normalization
- follow-up queue generation
- split-task generation
- staging

Do **not** rely on prompt-only discovery for raw gathering when the pipeline can do the work.

LLMs are still appropriate later for:

- validation assistance
- enrichment review
- gap analysis
- writing polished dossiers

## Main Scripts

Use these first:

- `scripts/run_discovery_pipeline.py`
- `scripts/search_duckduckgo.py`
- `scripts/html_to_markdown.py`
- `scripts/capture_to_evidence_index.py`
- `scripts/normalize_existing_discovery_report.py`
- `scripts/generate_followup_queue.py`
- `scripts/split_multi_venue_candidates.py`
- `scripts/ingest_discovery_reports.py`

## Standard Workflows

### 1. Run a live discovery pass

```bash
python scripts/run_discovery_pipeline.py \
  "site:.edu pre-college residential program" \
  --run-id us-college-precollege-seed \
  --country US \
  --region MA \
  --program-family college-pre-college
```

### 2. Ingest gathered report dumps

If new discovery data already exists in `reports/discovery/` as `.json` arrays or raw `.jsonl` search-hit files:

```bash
python scripts/ingest_discovery_reports.py
```

This will generate:

- `*_normalized.jsonl`
- `*_followup_queue.jsonl`
- `*_split_queue.jsonl`
- `*_split_stubs.jsonl`

And it will refresh aggregate staging files:

- `data/staging/discovered-candidates.jsonl`
- `data/staging/discovery-followup-queue.jsonl`
- `data/staging/discovery-split-queue.jsonl`
- `data/staging/discovery-split-stubs.jsonl`
- `data/staging/discovery-ingest-summary.json`

### 3. Rebuild the evidence index

```bash
python scripts/capture_to_evidence_index.py \
  data/raw/evidence-pages/text \
  --output data/normalized/evidence_index.jsonl
```

## Search Guidance

Current default search provider chain:

- `instant_answer`
- `lite_html`

DuckDuckGo is a **seed-discovery layer**, not an exhaustive search engine.

When Instant Answer is weak, use Lite HTML directly:

```bash
python scripts/search_duckduckgo.py \
  "Johns Hopkins Engineering Innovation residential" \
  --providers lite_html \
  --no-expand
```

## Canonical Paths

- Final venue dossiers: `camps/<country>/<region>/`
- Raw run artifacts: `data/raw/discovery-runs/<run-id>/`
- Raw evidence pages: `data/raw/evidence-pages/`
- Normalized evidence index: `data/normalized/evidence_index.jsonl`
- Discovery reports and companions: `reports/discovery/`
- Aggregate staging handoff: `data/staging/`

## When Editing Records

- Prefer updating normalized or staging artifacts through scripts rather than manual hand-edits.
- If you add a new raw report dump, ingest it through `scripts/ingest_discovery_reports.py`.
- If you add a new live discovery run, keep the run summary and companion outputs together.
- If a candidate is multi-venue, make sure the split queue reflects that.

## Validation and Enrichment Boundary

Discovery-stage records may still be ambiguous.

They should carry:

- `record_basis`
- `validation_needs`
- `priority_flags`
- `duration_guess`
- raw discovery provenance

Do not force a candidate into validated status just because it looks plausible.

## Current Pipeline Status

The repo now supports:

- deterministic search
- evidence capture to Markdown
- evidence indexing
- normalization of gathered reports
- follow-up queue generation
- multi-venue split-task generation
- aggregate staging ingestion

If behavior in docs and scripts diverges, update this file and the corresponding docs together.
