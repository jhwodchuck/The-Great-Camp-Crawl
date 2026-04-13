# Discovery Pipeline Gap Analysis

Audit date: 2026-04-13

Audited files:

- `scripts/search_duckduckgo.py`
- `scripts/html_to_markdown.py`
- `scripts/discover_and_capture.py`
- `scripts/ddg_discovery_to_candidate_schema.py`
- `scripts/capture_to_evidence_index.py`
- `scripts/run_discovery_pipeline.py`
- `scripts/requirements-discovery.txt`
- `prompts/system/OUTPUT_SCHEMA.md`
- `prompts/system/GROUNDING_RULES.md`
- `reports/discovery/us_candidates_2026-04-13.jsonl`
- `reports/discovery/us_candidates_2026-04-13_normalized.jsonl`
- `reports/discovery/us_candidates_2026-04-13_followup_queue.jsonl`

## Completed pieces in the original scaffold

- Repository direction was already clear: venue-level records, auditability, and staged discovery to validation to enrichment.
- Basic DDG seed search existed and proved the API could return seed candidates.
- Basic HTML-to-Markdown conversion existed and proved local capture was viable without an external MCP converter.
- A first-pass normalizer existed and demonstrated the target discovered-candidate shape.
- A basic evidence indexer existed.
- A simple runner existed and established a CLI orchestration entrypoint.
- Seeded sample records and sample US discovery outputs gave the schema and workflow a concrete target.

## Broken or fragile pieces in the original scaffold

- Search was single-query, prototype-grade, and had no real run metadata, retries, host filtering, or configurable expansion.
- URL deduplication was naïve and based on raw strings rather than normalized URLs.
- Capture did not preserve fetch metadata, redirects, status codes, timestamps, or a stable global evidence corpus.
- Capture filenames were unstable and collision-prone.
- Capture skipped neither duplicate URLs nor unchanged pages.
- Evidence indexing only handled a very thin frontmatter shape and omitted hashes, resolved URLs, timestamps, and text stats.
- Candidate normalization only handled one DDG-flavored input style and over-relied on simplistic defaults.
- Follow-up queue generation was absent from code and existed only as a hand-curated example.
- Multi-venue split handling was absent from code.
- The runner delegated everything through subprocess calls, had no partial-failure model, and did not emit a real run summary.
- No tests or reusable fixtures existed.

## Weak assumptions found during audit

- Treating DuckDuckGo Instant Answer as if it were a broad search API would create false confidence in recall.
- Inferring `traditional` from the word `camp` alone would overclaim taxonomy.
- Inferring `family` from the word `family` alone would create false positives from surnames or unrelated copy.
- Using default geography arguments as hard overrides would corrupt existing discovery reports.
- Flattening HTML-to-Markdown output too aggressively would damage evidence readability and auditability.

## Missing scripts and modules that were needed

- Shared utility modules for slugging, JSONL I/O, URL normalization, run layout, capture, normalization, evidence indexing, follow-up generation, and split-task generation.
- `scripts/search_batch.py` for file-driven batch search.
- `scripts/normalize_existing_discovery_report.py` to normalize seeded or externally prepared discovery reports.
- `scripts/generate_followup_queue.py` for deterministic queue generation.
- `scripts/split_multi_venue_candidates.py` for venue split operationalization.

## Testing gaps in the original scaffold

- No tests for slug generation.
- No tests for URL normalization or deduplication.
- No tests for candidate ID stability.
- No tests for duration or program-family inference.
- No tests for capture frontmatter or Markdown structure.
- No tests for evidence indexing.
- No tests for follow-up queue generation.
- No tests for pipeline runner behavior under mocked network conditions.

## Schema mismatches found during audit

- The original normalizer produced output too thin for the repo’s discovered-candidate conventions.
- The original evidence indexer could not recover enough metadata to support downstream auditability.
- The runner’s output layout did not align with a durable run concept.
- The seeded US discovery companion files were stronger than the actual normalizer implementation and were not yet reproducible by code.

## Operational risks before hardening

- Reruns could silently overwrite or collide with previous outputs.
- Capture failures were not preserved in a structured manifest.
- Search and capture lacked retry behavior and timeout controls.
- There was no consistent machine-readable run summary for debugging or automation.
- Multi-venue programs could clog the pipeline because nothing operationalized the split requirement.

## Remediation delivered in this hardening pass

- Added shared deterministic pipeline modules under `scripts/lib/`.
- Hardened DDG seed search with query files, expansion, timestamps, provenance, host filters, retries, backoff, and normalized URL dedupe.
- Hardened capture with stable filenames, raw HTML retention, structured Markdown frontmatter, redirect preservation, timestamps, checksums, and capture manifests.
- Added a reusable evidence indexer with resolved URLs, status, hashes, previews, and text stats.
- Expanded normalization to support DDG-style input and seeded discovery-report style input while preserving ambiguity.
- Added deterministic follow-up queue generation and multi-venue split-task generation.
- Added a run-centered orchestrator with structured output directories and machine-readable summaries.
- Added fixtures and pytest coverage for core behaviors and a mocked end-to-end run.
- Re-generated the seeded US normalized and follow-up companion files through code and added split artifacts.

## Remaining known limitations

- DuckDuckGo Instant Answer remains a seed-discovery layer rather than an exhaustive search layer.
- HTML extraction is heuristic and may still need later tuning for unusually heavy JavaScript or deeply nested marketing pages.
- Split-task generation does not automatically enumerate every venue; it operationalizes the need for venue-level follow-up.
- Taxonomy and duration inference remain conservative by design and should not replace later validation.
