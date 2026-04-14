# Copy-Paste Discovery Prompt: Country And Region Scanner Template

Replace the placeholders only if you need a custom slice. For the ready-to-use prompts,
open one of the region files in this folder instead.

- `<run_slug>`
- `<country>`
- `<region>`
- `<region_name>`
- `<language_mode>`
- `<source_focus>`

---

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find plausible overnight or residential programs for children or teens in the assigned geography.
- Work only on this bounded slice.
- Save the gathered report to `reports/discovery/<run_slug>.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `<run_slug>`
- `country`: `<country>`
- `region`: `<region>`
- `region_name`: `<region_name>`
- `language_mode`: `<language_mode>`
- `source_focus`: `<source_focus>`

Coverage pattern:

- the assigned state, province, or territory
- major metros and city clusters
- camp-heavy rural or resort regions
- official program sites first
- directories only for recall expansion

Include:

- traditional overnight camps
- specialty camps
- sports, arts, music, academic, and STEM camps
- family camps
- faith-based camps and retreats
- college-run pre-college residential programs

Priority bias:

- college-run pre-college residential programs
- programs that appear to last one week or longer

Hard rules:

- Do not mark a program as qualifying unless there is evidence of overnight, residential, boarding, lodging, or housing tied to the program.
- Do not infer overnight status from photos, cabins, dorm buildings, rustic branding, or the word `camp` alone.
- One final record should map to one physical venue or one session location.
- If the source clearly covers multiple campuses or venues, keep it as a multi-venue lead.
- Preserve Spanish and French evidence when found.
- Do not invent missing facts.
- Use `null` for unknown scalar values.
- Use `[]` for known-empty lists.
- Use absolute URLs.

Working rules:

- Gather as many strong leads as you can in one uninterrupted pass for this one region.
- If the batch becomes too large or you near context or time limits, stop cleanly and put continuation searches in `next_queries`.
- Prefer official sites over directories.
- Do not pad the batch with weak directory-only leads.
- Keep evidence snippets short and exact.
- Use `venue_unconfirmed` when the site looks real but the venue is not specific yet.

Return exactly one JSON object with this shape:

```json
{
  "scan_type": "country_region",
  "scope": {
    "country": "<country>",
    "region": "<region>",
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
      "region": "<region>",
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
