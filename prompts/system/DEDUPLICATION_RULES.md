# Deduplication Rules

## Core principle

Do not merge records unless there is strong evidence they represent the same physical venue.

## Usually safe to merge

- same operator
- same venue name
- same city and region
- same canonical program URL or same admissions page

## Usually not safe to merge

- same operator but different campus names
- same camp brand in different cities
- same university program across different campuses
- same operator with separate boys and girls campuses at distinct locations

## Workflow

1. Prefer preserving separate candidates.
2. Mark likely duplicates in QA outputs.
3. Merge only after venue-level review.

## Keep both when uncertain

False merges are more damaging than duplicate candidates in a breadth-first research system.
