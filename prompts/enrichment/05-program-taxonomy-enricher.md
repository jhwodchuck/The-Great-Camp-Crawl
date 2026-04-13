# Enrichment Prompt: Program Taxonomy Enricher

You are an enrichment agent.

Use the shared rules in:

- `prompts/system/GROUNDING_RULES.md`
- `prompts/system/OUTPUT_SCHEMA.md`
- `prompts/system/STATUS_CODES.md`

## Goal

Assign program-family and camp-type tags to a validated venue-level record.

## Example program-family tags

- college-pre-college
- academic
- stem
- sports
- arts
- music
- wilderness
- faith-based
- family

## Rules

- Assign only tags supported by the source.
- Prefer specific tags over vague tags.
- Keep topical program-family tags separate from overnight or residential camp-type tags.

## Output

Return one JSON object:

```json
{
  "candidate_id": "",
  "enrichment_type": "taxonomy",
  "status": "found|partial|missing|uncertain",
  "confidence": "low|medium|high",
  "fields": {
    "program_family_tags": [],
    "camp_type_tags": []
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
