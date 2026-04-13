# Status Codes

Use these exact values unless a task explicitly asks for something else.

## Candidate lifecycle

- `discovered`
- `validated`
- `rejected`
- `enrichment_pending`
- `rendered`
- `stale_review`

## Candidate shape

- `single_venue_candidate`
- `venue_unconfirmed`
- `multi_venue_candidate`

## Validation result

- `pass`
- `fail`
- `uncertain`

## Activity status

- `active_recent`
- `possibly_active`
- `stale`
- `closed_or_inactive`

## Enrichment status

- `found`
- `partial`
- `missing`
- `uncertain`

## Duplicate review

- `duplicate_likelihood`: `low`, `medium`, `high`
- `recommended_action`: `keep_both`, `split_needed`, `likely_duplicate`, `needs_human_review`

## Confidence

- `low`
- `medium`
- `high`
