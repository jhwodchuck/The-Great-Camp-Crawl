# Naming Conventions

## File path policy

Final venue records live under country and region folders, for example:

```text
camps/us/tx/
camps/canada/on/
camps/mexico/jal/
```

## Final filename pattern

```text
[camp-slug]--[country]-[region]-[city]-[venue-slug]--[record-id].md
```

Example:

```text
johns-hopkins-engineering-innovation--us-md-baltimore-homewood-campus--us-md-baltimore-homewood-campus.md
```

## Identifier guidance

- `camp_id`: stable brand-level identity
- `venue_id`: stable physical-location identity
- `record_id`: usually the same as `venue_id`
- `candidate_id`: temporary or staging identity for a discovered lead

## Slug rules

- lowercase
- ASCII when practical
- words separated by hyphens
- avoid punctuation unless it is needed to preserve meaning
- prefer official campus or venue names over marketing slogans
- prefer city names over metro names when the venue is known

## Low-certainty rule

If the venue is not specific enough, do not invent a precise venue slug. Use a broader candidate label or leave the venue field `null` and flag venue follow-up instead.

## Multi-campus rule

If the same operator runs programs at multiple venues, create one final record per venue.

## Multi-track rule

If one venue hosts multiple tracks, keep one venue record unless the tracks are genuinely separate locations.
