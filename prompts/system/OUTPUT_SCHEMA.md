# Output Schema

Final venue dossiers should use YAML front matter followed by structured Markdown sections.

## Required identifiers

- `record_id`: unique identifier for this venue record
- `camp_id`: brand-level camp identifier
- `venue_id`: physical venue identifier

## Recommended front matter example

```yaml
---
record_id: us-md-baltimore-homewood-campus-jhu-engineering-innovation
camp_id: johns-hopkins-engineering-innovation
venue_id: us-md-baltimore-homewood-campus
name: Johns Hopkins Engineering Innovation
display_name: Johns Hopkins Engineering Innovation at Homewood Campus
country: US
country_name: United States
region: MD
region_name: Maryland
city: Baltimore
venue_name: Homewood Campus
program_family:
  - college-pre-college
  - academic
camp_types:
  - overnight
  - residential-academic
priority_flags:
  college_precollege: true
  one_week_plus: true
languages_found:
  - en
source_language_primary: en
activity_status: active_recent
activity_evidence_window_months: 24
duration:
  min_days: 7
  max_days: 21
pricing:
  currency: USD
  amount_min:
  amount_max:
  boarding_included:
ages:
  min:
  max:
grades:
  min:
  max:
operator:
  name:
  type:
website:
  canonical_url:
  admissions_url:
  session_dates_url:
  pricing_url:
contact:
  email:
  phone:
location:
  address:
  postal_code:
  latitude:
  longitude:
verification:
  overnight_confirmed: true
  active_past_2_years_confirmed: true
  confidence: high
  last_verified: 2026-04-13
evidence:
  overnight_source_url:
  recent_activity_source_url:
  duration_source_url:
  pricing_source_url:
tags:
  - united-states
  - maryland
  - baltimore
  - overnight
  - college-pre-college
  - one-week-plus
draft_status: final
---
```

## Required Markdown sections

1. Quick Take
2. Verified Facts
3. Overnight Evidence
4. Recent Activity Evidence
5. Program Overview
6. Ages and Grades
7. Session Length and Structure
8. Pricing
9. Location and Venue Notes
10. Contact and Enrollment
11. Open Questions
12. Sources
