# Copy-Paste Discovery Prompt: Long-Duration Priority Scanner

Replace the placeholders before you paste this into an outside agent:

- `<run_slug>`
- `<country>`
- `<region_or_null>`
- `<language_mode>`
- `<source_focus>`
- `<max_candidates>`

---

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find residential or overnight programs with stronger one-week-plus or multi-week signals.
- Save the gathered report to `reports/discovery/<run_slug>.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `<run_slug>`
- `country`: `<country>`
- `region`: `<region_or_null>`
- `language_mode`: `<language_mode>`
- `source_focus`: `<source_focus>`
- `max_candidates`: `<max_candidates>`

Priority evidence:

- one-week sessions
- two-week sessions
- multi-week residential programs
- boarding programs lasting seven days or more

Hard rules:

- Do not exclude a candidate only because another visible session is shorter.
- Preserve exact duration wording in `duration_hint_text`.
- Set `priority_flags.likely_one_week_plus = true` only when the wording supports it.
- Keep boarding duration separate from optional day-program add-ons.
- Use `null` for unknown scalar values and `[]` for known-empty lists.

Return exactly one JSON object with this shape:

```json
{
  "scan_type": "long_duration",
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
