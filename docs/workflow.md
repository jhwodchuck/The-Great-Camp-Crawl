# Workflow

## 1. Discovery
Run the deterministic code-first discovery pipeline by geography, program family, and language.

Primary outputs:
- `reports/discovery/<run-id>_raw.jsonl`
- `reports/discovery/<run-id>_normalized.jsonl`
- `reports/discovery/<run-id>_followup_queue.jsonl`
- `data/raw/discovery-runs/<run-id>/...`
- raw source captures in `data/raw/evidence-pages/`

## 2. Validation
Validate overnight status, venue identity, and recent activity.

Primary outputs:
- `data/staging/validated-candidates.jsonl`
- `data/staging/rejected-candidates.jsonl`

## 3. Enrichment
Fill missing pricing, age ranges, grades, duration, contact details, and taxonomy.

Primary outputs:
- `data/staging/enrichment-queue.jsonl`
- `data/normalized/*.jsonl`

## 4. Rendering
Write one venue dossier per final record into `camps/...` and refresh browsable docs indexes.

## 5. QA
Run frontmatter validation, duplicate checks, stale checks, and index rebuilds.

## Year-over-year reuse
Keep raw evidence whenever practical so records can be re-validated in future years rather than rediscovered from scratch.
