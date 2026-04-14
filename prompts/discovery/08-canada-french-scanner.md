# Copy-Paste Discovery Prompt: Canada French Scanner

Replace the placeholders before you paste this into an outside agent:

- `<run_slug>`
- `<country>`
- `<region_or_null>`
- `<source_focus>`
- `<max_candidates>`

---

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find overnight or residential youth programs in Canada, including French-language sources.
- Save the gathered report to `reports/discovery/<run_slug>.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `<run_slug>`
- `country`: `<country>`
- `region`: `<region_or_null>`
- `language_mode`: `fr|mixed`
- `source_focus`: `<source_focus>`
- `max_candidates`: `<max_candidates>`

Search posture:

- Search in both English and French.
- Preserve French evidence wording when found.
- Prefer official camp or institution pages over directories.

Example search language:

- camp d'ete avec hebergement
- camp residentiel
- programme preuniversitaire residentiel
- sejour jeunesse
- camp musical residentiel
- programme academique d'ete en residence

Hard rules:

- Do not reject French-only sources during discovery.
- Separate distinct campuses or venues into distinct candidates.
- Use `translated_name_hint` only when it reduces ambiguity.
- Use `null` for unknown scalar values and `[]` for known-empty lists.

Return exactly one JSON object with this shape:

```json
{
  "scan_type": "canada_french",
  "scope": {
    "country": "<country>",
    "region": "<region_or_null>",
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
      "country": "<country>",
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

When finished:

- Save the JSON to `reports/discovery/<run_slug>.json` if you can write files.
- Otherwise return only the JSON object.
- After the JSON, if non-JSON wrapper text is allowed, add only:
  - saved path
  - candidate count
  - next query count
  - blockers
