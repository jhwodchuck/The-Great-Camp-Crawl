# Discovery Report Save Contract

Use this contract when a discovery agent can write files into the repository.

## Save location

Save each gathered discovery report under:

```text
reports/discovery/<run_slug>.json
```

Use one file per bounded slice, not one file for the entire world.

Good slice examples:

- one country and one program family
- one province and one language mode
- one university pre-college pass
- one follow-up gap-repair pass

## Run slug

Use lowercase kebab-case:

```text
<country>-<region-or-national>-<scan-type>-<slice-label>-<YYYY-MM-DD>
```

Examples:

- `us-national-college-precollege-ivy-pass-2026-04-13`
- `ca-qc-canada-french-residential-2026-04-13`
- `mx-national-mexico-spanish-adolescentes-2026-04-13`

## File shape

Save one JSON object using the standard discovery batch shape from `prompts/system/OUTPUT_SCHEMA.md`.

That means:

- the top-level file is a JSON object
- candidate rows live in `candidates`
- `queries_used` records what was searched
- `next_queries` records the next continuation queries

Do not save Markdown, YAML, or prose summaries as the primary discovery report.

## Save behavior

- Create the file directly in `reports/discovery/`.
- Do not wrap JSON in code fences.
- Overwrite the file only when intentionally rerunning the same slice.
- If the batch is too large, stop and save the partial report with continuation queries in `next_queries`.

## Completion behavior

- Do the actual discovery work. Do not just suggest prompt edits or wording tweaks.
- Save the report file before you stop.
- End with a short completion note that includes:
  - saved path
  - candidate count
  - next query count
  - any blocker such as `403`, timeout, or write restriction
- Do not end with "what would you like me to do next?" unless the task is actually blocked.

## Ingestion

After saving one or more reports, run:

```bash
python scripts/ingest_discovery_reports.py
```

That will generate:

- `*_normalized.jsonl`
- `*_followup_queue.jsonl`
- `*_split_queue.jsonl`
- `*_split_stubs.jsonl`
- updated aggregate staging outputs in `data/staging/`

## If the agent cannot write files

Return the JSON object directly. A higher-level agent can save it to the intended `reports/discovery/<run_slug>.json` path.

## Completeness rule

Do not claim that one report is exhaustive.

Discovery should be run as many bounded slices:

- by country
- by region
- by language
- by program family
- by source type
- by gap-repair follow-up pass

Completeness comes from accumulating many saved slice reports, not from one giant prompt run.

## Practical rule for free-tier agents

One agent should handle one bounded slice and save one report.

Do not ask one free-tier agent to "find everything in North America." Instead, assign:

- one country or one province/state
- one language mode
- one program family or source class
- one follow-up repair pass
