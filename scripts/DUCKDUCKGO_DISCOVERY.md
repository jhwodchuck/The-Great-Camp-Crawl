# Discovery Search Scripts

These scripts provide the deterministic raw-discovery search path. The preferred provider is a local SearXNG instance. DuckDuckGo and Google CDP are available as fallbacks.

## Provider summary

| Provider | Script | When to use |
|----------|--------|-------------|
| `searxng` | `search_searxng.py` | **Default** — highest recall, no rate limits, requires local Docker instance |
| `instant_answer` | `search_duckduckgo.py` | DDG structured hits; good for quick seed passes |
| `lite_html` | `search_duckduckgo.py` | DDG fallback when Instant Answer recall is weak |
| `google_cdp` | `search_duckduckgo.py` | Broadest recall via local Chrome; use when both DDG providers are insufficient |

## Important caveat

DuckDuckGo’s Instant Answer API is useful for seed discovery but is not a full rich search-results API. Treat all DDG providers as seed-discovery helpers rather than a complete search layer.

SearXNG returns significantly more results per query and has no rate-limiting concerns when running locally.

## Files

- `scripts/search_searxng.py` — query a local SearXNG instance; preferred high-recall provider
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

### SearXNG (preferred)

Start the Docker container before running searches:

```bash
docker start searxng
# or install: docker run -d --name searxng --restart unless-stopped \
#   -p 8080:8080 -e SEARXNG_BASE_URL="http://localhost:8080/" searxng/searxng:latest
```

## Example usage

### SearXNG (preferred)

All 50 US states:

```bash
python scripts/search_searxng.py \
  "overnight residential summer camp" \
  --country US --region TX \
  --output data/staging/discovered-searxng-tx.jsonl
```

With query file and narrowed program family:

```bash
python scripts/search_searxng.py \
  --query-file data/seed-queries/us-college-precollege-national.txt \
  --country US --region MA \
  --program-family college-pre-college \
  --output data/staging/discovered-searxng-ma-college.jsonl
```

### DuckDuckGo (fallback)

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

Use local Chrome-driven Google results when you need broader recall and Chrome is already running with remote debugging:

```bash
python scripts/search_duckduckgo.py \
  "site:.edu Massachusetts pre-college residential" \
  --providers google_cdp \
  --no-expand
```
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
