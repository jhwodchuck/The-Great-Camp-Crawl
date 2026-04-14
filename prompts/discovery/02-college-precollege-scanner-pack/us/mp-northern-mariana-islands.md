# Copy-Paste Discovery Prompt: US / MP / Northern Mariana Islands — College Pre-College Scanner

Use this prompt as-is with an outside agent. The default `run_slug` is ready to use.

If a report with the same `run_slug` already exists, append a suffix like `-02` or `-03`
before saving.

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find overnight or residential pre-college programs hosted by colleges and universities
  in this assigned region.
- Work only on this bounded slice.
- Save the gathered report to `reports/discovery/us-mp-college-precollege-scan.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `us-mp-college-precollege-scan`
- `country`: `US`
- `region`: `MP`
- `region_name`: `Northern Mariana Islands`
- `language_mode`: `english-first; keep Spanish and French evidence when encountered`
- `source_focus`: `official university and college program pages first (.edu preferred); camp association directories only for recall expansion`
- `max_candidates`: `25`

Search angles to cover:

- `site:.edu "Northern Mariana Islands" "pre-college" residential`
- `site:.edu "Northern Mariana Islands" "summer program" residential overnight`
- `site:.edu "Northern Mariana Islands" "summer immersion" OR "summer institute" residential`
- `"Northern Mariana Islands" university "summer camp" residential "high school"`
- `"Northern Mariana Islands" college "summer program" residential "boarding" OR "dorm"`

Search focus:

- pre-college
- summer session
- residential program
- academic immersion
- university summer program
- on-campus summer program
- youth residential institute
- secondary school summer residency

Search posture:

- Prefer official university pages.
- Look for housing, residence hall, dorm, campus-life, or residential-life pages tied to the program.
- Capture a venue or campus name whenever visible.
- Tag likely one-week-plus programs only when the wording supports it.

Exclude:

- commuter-only programs
- online-only programs
- vague campus marketing with no youth program

Hard rules:

- Do not assume a program is residential just because it happens on a campus.
- Do not merge multiple campuses into one venue record.
- Keep multi-campus pages as `multi_venue_candidate`.
- Preserve uncertainty instead of guessing.
- Use `null` for unknown scalar values.
- Use `[]` for known-empty lists.
- Use absolute URLs.

Working rules:

- Return at most `25` candidates in one batch.
- Favor fewer high-signal candidates over weak lists.
- If more good leads exist, stop and put continuation searches in `next_queries`.

Return exactly one JSON object with this shape:

```json
{
  "scan_type": "college_precollege",
  "scope": {
    "country": "US",
    "region": "MP",
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
      "region": "MP",
      "country": "US",
      "canonical_url": "",
      "supporting_urls": [],
      "directory_source_url": null,
      "source_language": null,
      "program_family_tags": ["college-pre-college"],
      "camp_type_tags": [],
      "candidate_shape": "single_venue_candidate|venue_unconfirmed|multi_venue_candidate",
      "priority_flags": {
        "likely_college_precollege": true,
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

- Save the JSON to `reports/discovery/us-mp-college-precollege-scan.json` if you can write files.
- Otherwise return only the JSON object.
- After the JSON, if non-JSON wrapper text is allowed, add only:
  - saved path
  - candidate count
  - next query count
  - blockers
