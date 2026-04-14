# Free-Tier Agent Task Template

Copy this template when handing a discovery slice to an outside agent.

## Template

```text
You are gathering discovery data for The Great Camp Crawl.

Read and follow these files first:
- prompts/discovery/00-report-save-contract.md
- prompts/system/GROUNDING_RULES.md
- prompts/system/OUTPUT_SCHEMA.md
- prompts/system/STATUS_CODES.md
- prompts/discovery/<scanner-file>.md

Task:
- Run one bounded discovery slice only.
- Gather plausible overnight or residential child/teen programs for the assigned slice.
- Save the gathered report to:
  reports/discovery/<run_slug>.json

Rules:
- Do the actual discovery work. Do not rewrite prompt files.
- Save one JSON object using the standard discovery batch shape.
- Use null for unknown scalar values and [] for known-empty lists.
- Keep evidence snippets short and exact.
- Preserve uncertainty instead of guessing.
- If you find more leads than fit comfortably, stop and put continuation searches in next_queries.
- Do not claim completeness.

Assigned slice:
- scanner file: <scanner-file>
- run slug: <run_slug>
- country: <country>
- region: <region-or-empty>
- language mode: <language-mode>
- program family: <program-family-or-empty>
- source focus: <official|directory|mixed>
- notes: <notes>

When finished:
- Save the file.
- Reply with only:
  - saved path
  - candidate count
  - next query count
  - blockers
```

## Example

```text
You are gathering discovery data for The Great Camp Crawl.

Read and follow these files first:
- prompts/discovery/00-report-save-contract.md
- prompts/system/GROUNDING_RULES.md
- prompts/system/OUTPUT_SCHEMA.md
- prompts/system/STATUS_CODES.md
- prompts/discovery/08-canada-french-scanner.md

Task:
- Run one bounded discovery slice only.
- Gather plausible overnight or residential child/teen programs for the assigned slice.
- Save the gathered report to:
  reports/discovery/ca-qc-canada-french-residential-pass-2026-04-13.json

Rules:
- Do the actual discovery work. Do not rewrite prompt files.
- Save one JSON object using the standard discovery batch shape.
- Use null for unknown scalar values and [] for known-empty lists.
- Keep evidence snippets short and exact.
- Preserve uncertainty instead of guessing.
- If you find more leads than fit comfortably, stop and put continuation searches in next_queries.
- Do not claim completeness.

Assigned slice:
- scanner file: 08-canada-french-scanner.md
- run slug: ca-qc-canada-french-residential-pass-2026-04-13
- country: CA
- region: QC
- language mode: fr
- program family: mixed
- source focus: official
- notes: Focus on Quebec residential youth camps and official institution pages first.

When finished:
- Save the file.
- Reply with only:
  - saved path
  - candidate count
  - next query count
  - blockers
```

## Coverage note

You will not get a complete set from one prompt or one agent.

Use this template many times across slices such as:

- `us` + `college_precollege`
- `us` + `specialty`
- `ca-qc` + `french`
- `mx` + `spanish`
- association directories
- university lists
- gap-repair passes
