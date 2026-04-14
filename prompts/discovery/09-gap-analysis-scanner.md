# Copy-Paste Discovery Prompt: Gap Analysis Scanner

Replace the placeholders before you paste this into an outside agent:

- `<run_slug>`
- `<country>`
- `<region_or_null>`
- `<language_mode>`
- `<source_focus>`

---

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Review an existing discovery slice and find under-covered areas plus the next best follow-up searches.
- Include new candidate leads only when they have a usable URL and a plausible qualifying signal.
- Save the gathered report to `reports/discovery/<run_slug>.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `<run_slug>`
- `country`: `<country>`
- `region`: `<region_or_null>`
- `language_mode`: `<language_mode>`
- `source_focus`: `<source_focus>`

Look for under-covered areas such as:

- states or provinces with too few results
- program families with weak recall
- university-hosted residential programs missed by generic searches
- Spanish or French sources not yet represented

Return exactly one JSON object with this shape:

```json
{
  "scan_type": "gap_analysis",
  "scope": {
    "country": "<country>",
    "region": "<region_or_null>",
    "city": null
  },
  "queries_used": [],
  "next_queries": [],
  "undercovered_slices": [
    {
      "slice_type": "",
      "label": "",
      "reason": ""
    }
  ],
  "candidates": []
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
