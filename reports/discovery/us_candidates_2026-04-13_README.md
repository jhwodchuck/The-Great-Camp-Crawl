# US Candidates 2026-04-13

This discovery set now has companion files that fit the repository workflow more cleanly.

## Files

- `us_candidates_2026-04-13.jsonl` — original discovery report
- `us_candidates_2026-04-13_normalized.jsonl` — code-generated normalized candidate-schema companion file
- `us_candidates_2026-04-13_followup_queue.jsonl` — code-generated deterministic follow-up work items
- `us_candidates_2026-04-13_split_queue.jsonl` — multi-venue split-task queue
- `us_candidates_2026-04-13_split_stubs.jsonl` — split stub placeholders for venue-specific follow-up

## Why the normalized file exists

The original discovery report was strong research output, but it was missing some repo-oriented workflow fields such as:
- stable `candidate_id`
- explicit `record_basis`
- separated `program_family` and `camp_types`
- `priority_flags`
- `duration_guess`
- `validation_needs`
- structured handling for ambiguous multi-venue programs

## Recommended usage

Use the normalized file as the handoff into validation and enrichment stages, preserve the original file as the raw discovery artifact, and use the follow-up and split queues to drive next-step operational work.

These companion files are now produced by repository scripts rather than manual curation.
