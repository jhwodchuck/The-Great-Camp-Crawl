# Status Codes

## Candidate lifecycle

- `discovered` — found by a discovery agent but not yet validated
- `validated` — passed overnight, venue, and recent-activity checks
- `rejected` — does not meet requirements for a final record
- `enrichment_pending` — validated but missing important fields
- `rendered` — venue dossier written
- `stale_review` — requires human or automated recency re-check

## Activity status values

- `active_recent` — evidence of activity in the last 24 months
- `possibly_active` — weak current evidence, needs follow-up
- `stale` — no acceptable recent-activity evidence
- `closed_or_inactive` — evidence suggests the program is no longer operating

## Confidence values

- `high`
- `medium`
- `low`
