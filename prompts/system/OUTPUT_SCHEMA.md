# Output Schema

Use this contract for free-tier or low-capability agents. Favor short, strict JSON over prose.

## Global output rules

1. Return JSON only unless a task explicitly asks for Markdown.
2. Do not wrap JSON in code fences.
3. If a field is unknown, use `null`.
4. If a list has no confirmed values, use `[]`.
5. Use absolute URLs.
6. Copy evidence snippets exactly when possible.
7. Keep evidence snippets short and audit-friendly.
8. Use `YYYY-MM-DD` for exact dates when visible.
9. If only month or year is visible, preserve the raw date text in a note field and leave the exact date field `null`.
10. Keep each batch small. If there are more results than fit comfortably, stop and put follow-up search strings in `next_queries`.

## Standard discovery batch shape

Use this for discovery prompts unless the prompt says otherwise.

```json
{
  "scan_type": "country_region|college_precollege|specialty|faith_family_retreat|directory|long_duration|mexico_spanish|canada_french|gap_analysis",
  "scope": {
    "country": null,
    "region": null,
    "city": null
  },
  "queries_used": [],
  "next_queries": [],
  "candidates": [
    {
      "candidate_name": "",
      "translated_name_hint": null,
      "operator_name": null,
      "venue_name": null,
      "city": null,
      "region": null,
      "country": null,
      "canonical_url": "",
      "supporting_urls": [],
      "directory_source_url": null,
      "source_language": null,
      "program_family_tags": [],
      "camp_type_tags": [],
      "candidate_shape": "single_venue_candidate|venue_unconfirmed|multi_venue_candidate",
      "priority_flags": {
        "likely_college_precollege": null,
        "likely_one_week_plus": null
      },
      "duration_hint_text": null,
      "overnight_evidence": {
        "snippet": null,
        "url": null
      },
      "recent_activity_evidence": {
        "snippet": null,
        "url": null,
        "date_text": null
      },
      "notes": null,
      "validation_needs": [],
      "confidence": "low|medium|high"
    }
  ]
}
```

## Standard validation result shape

Use one object per candidate or per candidate pair.

```json
{
  "candidate_id": "",
  "check": "overnight|venue|recent_activity|duplicate",
  "result": "pass|fail|uncertain",
  "confidence": "low|medium|high",
  "reason": "",
  "evidence": {
    "snippet": null,
    "url": null,
    "date_text": null
  },
  "normalized_fields": {},
  "validation_needs": []
}
```

For duplicate review, replace `candidate_id` with:

```json
{
  "left_candidate_id": "",
  "right_candidate_id": ""
}
```

## Standard enrichment result shape

Use one object per validated venue-level candidate.

```json
{
  "candidate_id": "",
  "enrichment_type": "pricing|duration|age_grade|contact|taxonomy",
  "status": "found|partial|missing|uncertain",
  "confidence": "low|medium|high",
  "fields": {},
  "evidence": {
    "snippet": null,
    "url": null,
    "date_text": null
  },
  "notes": null,
  "validation_needs": []
}
```

## Final rendered dossier note

Final venue pages in the repo still use YAML front matter plus Markdown sections. That is a later rendering step. Discovery, validation, and enrichment agents should usually return JSON, not prose dossiers.
