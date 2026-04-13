# Naming Conventions

## File path policy

Final records live under country and region folders, for example:

```text
camps/us/tx/
camps/canada/on/
camps/mexico/jal/
```

## Filename pattern

```text
[camp-slug]--[country]-[region]-[city]-[venue-slug]--[record-id].md
```

## Example

```text
johns-hopkins-engineering-innovation--us-md-baltimore-homewood-campus--us-md-baltimore-homewood-campus.md
```

## Identifier guidance

### `camp_id`
Stable brand-level identity.

### `venue_id`
Stable physical-location identity.

### `record_id`
Normally the same as `venue_id` unless there is a justified need to distinguish the rendered record from the location key.

## Slug rules

- lowercase
- ASCII when practical
- words separated by hyphens
- avoid punctuation unless necessary to preserve meaning
- prefer city names over metro names when venue specificity is available

## Multi-campus rule

If the same operator runs programs at multiple venues, create one file per venue rather than one file per operator.

## Multi-track rule

If the same venue hosts multiple program tracks, keep one venue file and capture track distinctions inside structured fields unless there is a strong reason to split them.
