# Copy-Paste Discovery Prompt: Recent Activity Checker

Replace the placeholders before you paste this into an outside agent:

- `<run_slug>`
- `<candidate_id>`

---

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Check whether one candidate has evidence of activity in the last 24 months.
- Save the result to `reports/discovery/<run_slug>.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Good signals:

- recent session dates
- recent registration links
- recent tuition updates
- recent application deadlines
- recent official social posts or announcements

Weak signals:

- undated marketing copy
- old directory pages
- archived pages with no current trace

Return exactly one JSON object with this shape:

```json
{
  "candidate_id": "<candidate_id>",
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

When finished:

- Save the JSON to `reports/discovery/<run_slug>.json` if you can write files.
- Otherwise return only the JSON object.
- After the JSON, if non-JSON wrapper text is allowed, add only:
  - saved path
  - blockers
