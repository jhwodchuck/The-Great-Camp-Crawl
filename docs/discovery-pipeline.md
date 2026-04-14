# Discovery Pipeline

The repository now includes a deterministic raw-discovery pipeline for seed search, evidence capture, normalization, indexing, and staging.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements-discovery.txt
```

## Main entrypoint

Use `scripts/run_discovery_pipeline.py` for most runs.

Example:

```bash
python scripts/run_discovery_pipeline.py \
  "site:.edu pre-college residential program" \
  --run-id us-college-precollege-seed \
  --country US \
  --region MA \
  --program-family college-pre-college
```

For nationwide college pre-college discovery, use the region fanout wrapper instead of
trying to do the whole country in a single prompt:

```bash
python scripts/run_college_precollege_nationwide.py \
  --country US \
  --run-prefix us-college-precollege-wave1 \
  --generate-prompt-pack \
  --ingest-after
```

That wrapper runs one deterministic pipeline pass per region using the college
pre-college query angles from `scripts/lib/college_precollege_prompt_pack.py`. When
`--generate-prompt-pack` is set, it also writes ready-to-paste outside-agent prompts to
`prompts/discovery/02-college-precollege-scanner-pack/`.

Key options:

- `--query-file` reads one query per line.
- `--country` and `--region` set discovery defaults for sparse raw records.
- `--program-family` controls deterministic query expansion templates.
- `--allow-host-file` and `--deny-host-file` filter search results by host.
- `--search-providers` chooses the provider chain for the main runner. Default: `instant_answer,lite_html`. Use `searxng` for higher recall when the local SearXNG instance is running on `http://localhost:8080`.
- `google_cdp` is available when local Chrome is already running on `localhost:9222`; use it when both DDG and SearXNG recall is insufficient.
- `--no-expand` disables query expansion.
- `--no-skip-existing-captures` forces re-fetching even when a stable capture file already exists.

## What a run writes

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
data/staging/discovery-runs/<run-id>/split_stubs.jsonl
data/normalized/evidence_index.jsonl
```

## Script roles

- `scripts/search_searxng.py`: preferred high-recall seed search via a local SearXNG Docker instance. Same interface as `search_duckduckgo.py`. Start the instance with `docker start searxng`.
- `scripts/search_duckduckgo.py`: DDG seed search with expansion, retries, timestamps, host filters, query logs, and Lite HTML fallback.
- `scripts/search_batch.py`: file-driven wrapper around the same search layer.
- `scripts/html_to_markdown.py`: capture one page, preserve HTML, emit Markdown evidence, and append to a manifest.
- `scripts/discover_and_capture.py`: lightweight combined path for small search-and-capture jobs.
- `scripts/normalize_existing_discovery_report.py`: normalize an existing discovery report into the repo candidate schema.
- `scripts/generate_followup_queue.py`: emit deterministic follow-up work items from normalized candidates.
- `scripts/split_multi_venue_candidates.py`: emit multi-venue split tasks and split stubs.
- `scripts/capture_to_evidence_index.py`: build an evidence index for a run or the full Markdown evidence corpus.

## Reruns

- Stable capture filenames are based on normalized URLs.
- By default, existing capture files are skipped on rerun.
- Run summaries are written to both `data/raw/discovery-runs/<run-id>/run.json` and `reports/discovery/<run-id>_summary.json`.
- The global evidence index can be rebuilt at any time with:

```bash
python scripts/capture_to_evidence_index.py data/raw/evidence-pages/text --output data/normalized/evidence_index.jsonl
```

## Existing discovery reports

The seeded `reports/discovery/us_candidates_2026-04-13.jsonl` report is now supported by code-driven companion files:

- `reports/discovery/us_candidates_2026-04-13_normalized.jsonl`
- `reports/discovery/us_candidates_2026-04-13_followup_queue.jsonl`
- `reports/discovery/us_candidates_2026-04-13_split_queue.jsonl`
- `reports/discovery/us_candidates_2026-04-13_split_stubs.jsonl`

## Limitations

- DuckDuckGo Instant Answer is not exhaustive. The Lite HTML fallback improves recall, but it is still a seed-discovery layer rather than a guaranteed complete index. **SearXNG returns significantly more results per query and should be the default when available.**
- Content extraction is heuristic. It is built for auditability and repeatability, not perfect page rendering.
- Multi-venue split generation operationalizes the problem, but venue-specific filling still needs later validation work.
- Normalization is intentionally conservative; ambiguity is preserved instead of guessed away.
