---
record_id: cand-us-tx-college-station-yap-engineering-tamu-texas-a-m-campus
camp_id: yap-engineering-tamu
venue_id: us-tx-college-station-texas-a-m-campus
name: 'YAP: Engineering (TAMU)'
display_name: 'YAP: Engineering (TAMU) at Texas A&M Campus'
country: US
country_name: United States
region: TX
region_name: Texas
city: College Station
venue_name: Texas A&M Campus
program_family:
- Engineering
- Pre-college
- stem
camp_types:
- residential
- overnight
priority_flags:
  college_precollege: true
  one_week_plus: false
languages_found:
- English
source_language_primary: English
activity_status: active_recent
activity_evidence_window_months: 24
duration:
  min_days: 6
  max_days: 6
pricing:
  currency: USD
  amount_min: 1299
  amount_max: 1299
  boarding_included: true
ages:
  min: null
  max: null
grades:
  min: 7
  max: 12
operator:
  name: Texas A&M University
  type: university
website:
  canonical_url: https://yap.tamu.edu/course-session-information/
  admissions_url: https://events.circuitree.com/yapreg/Login.aspx
  session_dates_url: https://yap.tamu.edu/course-session-information/
  pricing_url: https://yap.tamu.edu/course-session-information/
contact:
  email: yap@tamu.edu
  phone: 979-845-1802
location:
  address: null
  postal_code: null
  latitude: null
  longitude: null
verification:
  overnight_confirmed: true
  active_past_2_years_confirmed: true
  confidence: high
  last_verified: '2026-04-17'
evidence:
  overnight_source_url: https://yap.tamu.edu/
  recent_activity_source_url: https://yap.tamu.edu/course-session-information/
  duration_source_url: https://yap.tamu.edu/course-session-information/
  pricing_source_url: https://yap.tamu.edu/course-session-information/
tags:
- us
- tx
- college-station
- engineering
- pre-college
- stem
- residential
- overnight
draft_status: draft
---

# YAP: Engineering (TAMU) at Texas A&M Campus

## Quick Take
YAP: Engineering is an active Texas A&M residential pre-college engineering camp track within the Youth Adventure Program. For Summer 2026, the engineering offerings are split across two 6-day residential sessions: Engineering Design: Spark! for rising 7th–10th graders and Engineering Design: Mechanics! for rising 9th–12th graders. :contentReference[oaicite:1]{index=1}

## Verified Facts
- Operator: Texas A&M University
- Venue anchor: Texas A&M Campus
- Location anchor: College Station, TX
- Canonical URL: https://yap.tamu.edu/course-session-information/
- Program family: Engineering, Pre-college, stem
- Residential housing location: Cambridge Hall near Texas A&M
- 2026 engineering sessions:
  - Engineering Design: Spark! (YAP B), July 12–17, 2026
  - Engineering Design: Mechanics! (YAP C), July 19–24, 2026
- Tuition: $1,299
- Deposit: $399
- Contact: yap@tamu.edu | 979-845-1802 :contentReference[oaicite:2]{index=2}

## Overnight Evidence
The official YAP site says campers are housed at Cambridge Hall, a private dormitory near Texas A&M with suite-style accommodations, and explicitly states that YAP is a residential camp where campers stay all week. :contentReference[oaicite:3]{index=3}

## Recent Activity Evidence
The current Course & Session Information page says registration for YAP 2026 is now open and lists both 2026 engineering offerings and their session dates. :contentReference[oaicite:4]{index=4}

## Program Overview
This record is best treated as the engineering track within Texas A&M’s Youth Adventure Program rather than a single standalone camp. The 2026 engineering options are:
- **Engineering Design: Spark! (YAP B)**, which introduces the engineering design process through prototyping, CAD, 3D printing, laser cutting, soldering, robotics, and related skills
- **Engineering Design: Mechanics! (YAP C)**, which focuses on designing, prototyping, and testing mechanical systems and simple and compound machines through hands-on team-based work :contentReference[oaicite:5]{index=5}

## Ages and Grades
The official engineering sessions support a combined normalized grade range of:
- minimum grade observed: rising 7th grade
- maximum grade observed: rising 12th grade

The official pages reviewed for this pass do not publish a general age range for the engineering sessions, so ages remain uncaptured in structured form. :contentReference[oaicite:6]{index=6}

## Session Length and Structure
Although YAP describes itself broadly as a series of one-week courses, the published 2026 engineering session dates support a 6-day calendar-span structure:
- YAP B: July 12–17, 2026
- YAP C: July 19–24, 2026

Structured duration capture:
- min_days: 6
- max_days: 6

Because this is under 7 days, `one_week_plus` should be false in a strict duration-based schema. :contentReference[oaicite:7]{index=7}

## Pricing
The current official pricing page states that tuition for all courses in YAP A, B, and C is $1,299 and covers everything from check-in to check-out. It also states that a $399 deposit is required at registration, with the remaining balance payable in three equal monthly payments from March through May. :contentReference[oaicite:8]{index=8}

The official FAQ adds that tuition includes:
- housing
- meals
- materials
- transport
- instruction
- T-shirt
- activities

The refund policy shown publicly is:
- full refunds until March 1
- later refunds only if a replacement is found :contentReference[oaicite:9]{index=9}

## Location and Venue Notes
The official YAP site places the program at Texas A&M University in College Station and states that campers are housed at Cambridge Hall, a private dormitory near campus. I left the structured street address null because the YAP pages reviewed do not publish a single official program address field for the camp itself. :contentReference[oaicite:10]{index=10}

## Contact and Enrollment
Official site:
https://yap.tamu.edu/

Course and session details:
https://yap.tamu.edu/course-session-information/

Registration:
https://events.circuitree.com/yapreg/Login.aspx

Official public contact details:
- yap@tamu.edu
- 979-845-1802 :contentReference[oaicite:11]{index=11}

## Data Quality Notes
This record is now much stronger on:
- active 2026 confirmation
- residential / overnight confirmation
- exact engineering session dates
- real tuition and deposit capture
- normalized grade band
- public contact details

The main remaining structured gap is a clean official address field for the program itself, plus direct age normalization. :contentReference[oaicite:12]{index=12}

## Open Questions
- Exact age range still needs direct official capture if you want age normalization.
- Structured venue address, postal code, latitude, and longitude still need to be captured from a more specific official source.
- If you later want tighter granularity, Spark and Mechanics could each be split into separate linked records. :contentReference[oaicite:13]{index=13}

## Sources
- https://yap.tamu.edu/
- https://yap.tamu.edu/course-session-information/
- https://events.circuitree.com/yapreg/Login.aspx