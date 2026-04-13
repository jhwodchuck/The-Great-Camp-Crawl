# Deduplication Rules

## Core principle

False merges are worse than duplicate candidates. Keep separate records unless the evidence strongly supports the same physical venue.

## Usually safe signals for same venue

- same operator
- same venue or campus name
- same city and region
- same canonical program page
- same admissions page tied to the same location

## Usually unsafe signals

- same operator but different campus names
- same university program across multiple campuses
- same camp brand in different cities
- same operator with separate boys, girls, junior, or specialty campuses at distinct sites
- same umbrella brand with franchise or partner locations

## Decision pattern

- `keep_both`: use when locations differ or venue evidence is weak
- `split_needed`: use when one candidate clearly covers multiple venues
- `likely_duplicate`: use when both candidates point to the same physical site
- `needs_human_review`: use when signals conflict

## Working rules

1. Compare venue name before brand name.
2. Compare city and region before marketing copy.
3. Prefer official URLs over directory cards.
4. If one page is brand-level and another is venue-level, do not merge automatically.
5. If uncertain, preserve both and explain the ambiguity.
