# Copy-Paste Discovery Prompt: CA / NT / Northwest Territories

Use this prompt as-is with an outside agent. The default `run_slug` is ready to use.

If a report with the same `run_slug` already exists, append a suffix like `-02` or `-03`
before saving.

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find plausible overnight or residential programs for children or teens in this assigned region.
- Work only on this bounded slice.
- Save the gathered report to `reports/discovery/ca-nt-country-region-scan.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `ca-nt-country-region-scan`
- `country`: `CA`
- `region`: `NT`
- `region_name`: `Northwest Territories`
- `language_mode`: `english-first; keep French evidence when encountered`
- `source_focus`: `official program sites first; provincial camp associations and university pages next; directories only for recall expansion`

Search angles to cover:

- `"overnight camp" "Northwest Territories"`
- `"residential camp" "Northwest Territories"`
- `"camp with accommodation" "Northwest Territories"`
- `"family camp" "Northwest Territories"`
- `site:.ca "Northwest Territories" "pre-college" residential`

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
    "country": "CA",
    "region": "NT",
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
      "region": "NT",
      "country": "CA",
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

- Save the JSON to `reports/discovery/ca-nt-country-region-scan.json` if you can write files.
- Otherwise return only the JSON object.
- After the JSON, if non-JSON wrapper text is allowed, add only:
  - saved path
  - candidate count
  - next query count
  - blockers
