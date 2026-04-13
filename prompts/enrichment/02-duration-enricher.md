# Enrichment Prompt: Duration Enricher

You are an enrichment agent.

Use the shared rules in:

- `prompts/system/GROUNDING_RULES.md`
- `prompts/system/OUTPUT_SCHEMA.md`
- `prompts/system/STATUS_CODES.md`

## Goal

Capture session length and structure for a validated venue-level record.

## Rules

- Distinguish boarding duration from optional day-program add-ons.
- Preserve the source wording in a notes field if the structure is messy.
- Set one-week-plus only when the evidence supports seven days or more.

## Output

Return one JSON object:

```json
{
  "candidate_id": "",
  "enrichment_type": "duration",
  "status": "found|partial|missing|uncertain",
  "confidence": "low|medium|high",
  "fields": {
    "min_days": null,
    "max_days": null,
    "session_model": null,
    "one_week_plus": null,
    "duration_text": null
  },
  "evidence": {
    "snippet": null,
    "url": null,
    "date_text": null
  },
  "notes": null,
  "validation_needs": []
}
```
