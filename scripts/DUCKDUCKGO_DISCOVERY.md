# DuckDuckGo Discovery Scripts

These scripts add a lightweight web-discovery path using `https://api.duckduckgo.com/` plus HTML-to-Markdown capture.

## Important caveat

DuckDuckGo's Instant Answer API is useful for seed discovery, but it is not a full rich search-results API. Treat it as a recall helper rather than the only search source forever.

## Files

- `scripts/search_duckduckgo.py` — query the DuckDuckGo API and emit deduplicated JSONL hits
- `scripts/html_to_markdown.py` — fetch a page, extract main content, and convert it to Markdown
- `scripts/discover_and_capture.py` — do both in one pass for a small set of hits
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
python scripts/search_duckduckgo.py "site:.edu pre-college residential program" --output data/staging/discovered-ddg.jsonl
```

Capture one page to Markdown:

```bash
python scripts/html_to_markdown.py "https://globalscholars.yale.edu/" --output data/raw/evidence-pages/text/yale-young-global-scholars.md
```

Run combined discovery and capture:

```bash
python scripts/discover_and_capture.py "pre-college residential program" --limit 10
```

## Suggested role in this repo

Use these scripts to:
- generate raw leads
- capture source pages into Markdown for auditability
- feed the validation and enrichment prompts already in the repository
