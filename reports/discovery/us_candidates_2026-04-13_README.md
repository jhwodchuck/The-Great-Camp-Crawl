# US Candidates 2026-04-13

This discovery set now has companion files that fit the repository workflow more cleanly.

## Files

- `us_candidates_2026-04-13.jsonl` — original discovery report
- `us_candidates_2026-04-13_normalized.jsonl` — normalized candidate-schema companion file
- `us_candidates_2026-04-13_followup_queue.jsonl` — high-priority next actions for venue validation and enrichment

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

Use the normalized file as the handoff into validation and enrichment stages, while preserving the original file as the raw discovery artifact.
