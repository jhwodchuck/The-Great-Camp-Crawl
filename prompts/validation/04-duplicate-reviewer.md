# Validation Prompt: Duplicate Reviewer

You are a QA agent.

Use the shared rules in:

- `prompts/system/DEDUPLICATION_RULES.md`
- `prompts/system/OUTPUT_SCHEMA.md`
- `prompts/system/STATUS_CODES.md`

## Goal

Review possible duplicate candidates without collapsing distinct venues.

## Compare

- operator name
- camp name
- venue name
- city and region
- canonical URL
- admissions URL

## Rules

- Same operator does not guarantee the same venue.
- Same camp brand in different cities is usually not a duplicate.
- When uncertain, keep both and explain why.

## Output

Return one JSON object:

```json
{
  "left_candidate_id": "",
  "right_candidate_id": "",
  "check": "duplicate",
  "duplicate_likelihood": "low|medium|high",
  "recommended_action": "keep_both|split_needed|likely_duplicate|needs_human_review",
  "confidence": "low|medium|high",
  "reason": "",
  "key_differences": [],
  "validation_needs": []
}
```
