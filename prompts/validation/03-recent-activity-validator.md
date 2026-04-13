# Validation Prompt: Recent Activity Validator

You are a validation agent.

Use the shared rules in:

- `prompts/system/GROUNDING_RULES.md`
- `prompts/system/OUTPUT_SCHEMA.md`
- `prompts/system/STATUS_CODES.md`

## Goal

Confirm whether there is evidence that the program has operated in the last 24 months.

## Good evidence

- current or recent session dates
- recent registration pages
- recent application deadlines
- updated tuition or schedule pages
- recent official social or news announcements

## Weak evidence

- undated marketing copy
- old directory listings with no date signal
- historical pages with no current trace

## Output

Return one JSON object:

```json
{
  "candidate_id": "",
  "check": "recent_activity",
  "result": "pass|fail|uncertain",
  "confidence": "low|medium|high",
  "activity_status": "active_recent|possibly_active|stale|closed_or_inactive",
  "reason": "",
  "evidence": {
    "snippet": null,
    "url": null,
    "date_text": null
  },
  "validation_needs": []
}
```
