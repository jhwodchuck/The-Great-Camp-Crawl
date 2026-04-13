# DuckDuckGo Discovery Scripts

These scripts provide the default deterministic raw-discovery path using DuckDuckGo seed search plus local HTML-to-Markdown capture.

## Important caveat

DuckDuckGo's Instant Answer API is useful for seed discovery, but it is not a full rich search-results API. The scripts now use a provider chain by default:

- `instant_answer` for structured DDG JSON hits when available
- `lite_html` as a deterministic fallback when Instant Answer has poor recall

Treat both as seed-discovery helpers rather than a complete search layer.

## Files

- `scripts/search_duckduckgo.py` — query DuckDuckGo with query expansion, host filters, retries, provider fallback, and query provenance
- `scripts/search_batch.py` — run file-based batch search
- `scripts/html_to_markdown.py` — fetch a page, preserve raw HTML, and convert main content to Markdown evidence
- `scripts/discover_and_capture.py` — do both in one pass for a small set of hits
- `scripts/run_discovery_pipeline.py` — orchestrate search, capture, normalization, indexing, follow-up generation, staging, and summary writing
- `scripts/requirements-discovery.txt` — Python dependencies for the discovery scripts

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements-discovery.txt
```

## Example usage

Run seed discovery:

```bash
python scripts/search_duckduckgo.py \
  "site:.edu pre-college residential program" \
  --output reports/discovery/manual_seed_raw.jsonl \
  --query-log data/raw/discovery-runs/manual_seed/queries.jsonl \
  --country US \
  --program-family college-pre-college
```

Use only the Lite HTML provider when Instant Answer recall is weak:

```bash
python scripts/search_duckduckgo.py \
  "Johns Hopkins Engineering Innovation residential" \
  --providers lite_html \
  --no-expand
```

Capture one page to Markdown:

```bash
python scripts/html_to_markdown.py \
  "https://globalscholars.yale.edu/" \
  --manifest data/raw/evidence-pages/manifests/manual_capture_manifest.jsonl
```

Run the full pipeline:

```bash
python scripts/run_discovery_pipeline.py \
  "site:.edu pre-college residential program" \
  --run-id us-college-precollege-seed \
  --country US \
  --region CT \
  --program-family college-pre-college
```

## Suggested role in this repo

Use these scripts to:
- generate raw leads
- capture source pages into Markdown for auditability
- normalize discovery into repo candidate schema
- generate deterministic follow-up and split queues
- feed later validation and enrichment work without requiring prompt-driven raw gathering
