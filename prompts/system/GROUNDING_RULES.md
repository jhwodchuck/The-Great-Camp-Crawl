# Grounding Rules

These rules apply to every discovery, validation, enrichment, and rendering agent in this repository.

## Hard rules

1. Do not mark a program as qualifying unless there is evidence of overnight, residential, boarding, lodging, or housing tied to the program.
2. Do not infer overnight status from photos, cabins, dorm buildings, rustic branding, or the word `camp` alone.
3. Each final record must represent one physical venue or one session location.
4. If the source clearly covers multiple campuses or venues, keep it as a multi-venue lead or split candidate. Do not collapse it into fake single-site certainty.
5. A record needs evidence of activity in the last 24 months to reach validated status.
6. Prefer official program, institution, or operator pages as the main source of truth.
7. Directory and listing sites are valid discovery inputs, but they are weak proof if official evidence exists.
8. Preserve non-English evidence. Do not discard Spanish or French sources during discovery.
9. Record uncertainty explicitly. Do not invent missing facts.
10. Pricing can be missing during discovery and early enrichment, but missing pricing should be flagged.
11. College-run pre-college residential programs deserve extra recall effort.
12. Programs lasting one week or longer deserve extra recall effort and should be flagged when supported.

## Stage discipline

- Discovery finds plausible candidates and preserves evidence snippets.
- Validation decides the core gates: overnight, venue specificity, recent activity, and duplicate risk.
- Enrichment fills fields only when there is evidence.
- Rendering turns validated, evidence-backed data into dossier pages.

Do not skip a stage by overclaiming in an earlier stage.

## Evidence rules

- Prefer exact short snippets copied from the source.
- Keep evidence snippets short enough to audit quickly.
- Attach one URL per important claim when possible.
- If a date is visible, capture it exactly as shown.
- If the wording is ambiguous, say so instead of upgrading confidence.

## Unknown-value rules

- Use `null` for unknown scalar values.
- Use `[]` for known-empty lists.
- Use `uncertain` when the task asks for a decision but the evidence does not justify `pass` or `fail`.
- Do not fill geography, venue, ages, pricing, or duration from guesswork.

## Rejection triggers for final-record status

Reject or fail validation when the evidence shows:

- day camp only, with no overnight or residential proof
- venue rental only, with no child or teen program
- retreat center marketing with no specific youth or family program
- no recent activity signal within the last 24 months
- no usable tie to a physical venue or session site

## Auditability

Preserve source URLs, snippets, and uncertainty notes so another human or agent can re-check the record later.
