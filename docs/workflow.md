# Workflow

## 1. Discovery
Run discovery agents by geography, program family, and language.

Primary outputs:
- `data/staging/discovered-candidates.jsonl`
- raw source captures in `data/raw/`
- discovery notes in `data/raw/notes/`

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
