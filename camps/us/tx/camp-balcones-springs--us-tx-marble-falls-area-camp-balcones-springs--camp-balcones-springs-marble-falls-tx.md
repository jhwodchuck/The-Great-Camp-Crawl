---
record_id: camp-balcones-springs-marble-falls-tx
camp_id: camp-balcones-springs
venue_id: us-tx-marble-falls-area-camp-balcones-springs
name: Camp Balcones Springs
display_name: Camp Balcones Springs at Camp Balcones Springs
country: US
country_name: United States
region: TX
region_name: Texas
city: Marble Falls
venue_name: Camp Balcones Springs
program_family:
- adventure
- sports
- leadership
camp_types:
- overnight
priority_flags:
  college_precollege: false
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
  amount_min: 2185
  amount_max: 5145
  boarding_included: null
ages:
  min: 6
  max: 16
grades:
  min: null
  max: null
operator:
  name: Camp Balcones Springs
  type: camp-operator
website:
  canonical_url: https://campiscool.com/
  admissions_url: https://balcones.campintouch.com/ui/forms/application/camper/App
  session_dates_url: https://campiscool.com/dates-rates
  pricing_url: https://campiscool.com/dates-rates
contact:
  email: info@campbalconessprings.com
  phone: '(830) 693-2267'
location:
  address: 104 Balcones Springs Drive
  postal_code: '78654'
  latitude: null
  longitude: null
verification:
  overnight_confirmed: true
  active_past_2_years_confirmed: true
  confidence: high
  last_verified: '2026-04-17'
evidence:
  overnight_source_url: https://campiscool.com/
  recent_activity_source_url: https://campiscool.com/dates-rates
  duration_source_url: https://campiscool.com/dates-rates
  pricing_source_url: https://campiscool.com/dates-rates
tags:
- united-states
- tx
- marble-falls
- adventure
- sports
- leadership
- overnight
draft_status: draft
---

# Camp Balcones Springs at Camp Balcones Springs

## Quick Take
Camp Balcones Springs is an active Texas Hill Country overnight camp near Marble Falls with published 2026 one-week, ten-day, two-week, and three-week session options. It presents itself as a broad coed summer camp for ages 6 to 16, with a strong mix of adventure, sports, and leadership-oriented programming.

## Verified Facts
- Operator: Camp Balcones Springs
- Venue: Camp Balcones Springs
- Mailing location: Marble Falls, TX
- Address: 104 Balcones Springs Drive, Marble Falls, TX 78654
- Canonical URL: https://campiscool.com/
- Session dates / rates URL: https://campiscool.com/dates-rates
- Contact email: info@campbalconessprings.com
- Contact phone: (830) 693-2267
- Official age range: 6–16
- Founded: 1993
- Positioning: overnight summer camp in the Texas Hill Country
- Current published 2026 session lengths: 1 week, 10 days, 2 weeks, and 3 weeks
- Current published 2026 tuition range: $2,185 to $5,145

## Overnight Evidence
The official homepage describes Camp Balcones Springs as redefining the overnight summer camp experience for boys and girls ages 6 to 16. The camp-life pages also describe campers waking up with cabin mates and ending the day back in air-conditioned cabins, which is strong direct evidence for overnight classification.

## Recent Activity Evidence
The official Dates & Rates page is live for Summer 2026 and states that wait lists are already happening. The page publishes the full current session calendar and 2026 rates, which confirms recent activity well within the 24-month evidence window.

## Program Overview
Camp Balcones Springs is positioned as a coed Texas Hill Country sleepaway camp with a broad, activity-rich model rather than a narrow specialty program. The homepage says it was established in 1993 and founded on Christian principles, while camp-life pages emphasize outdoor adventure, sports, teamwork, food, special events, and unplugged camp living.

## Ages and Grades
The official site clearly markets the camp for boys and girls ages 6 to 16, so the age range in this record is well supported.

Grades are more complicated and remain unnormalized in this record. The 2026 dates page uses a mix of K–10th grade for major terms, K–4th grade for one-week sessions, K–5th grade for the 10-day term, and the high-school programs page separately references summer-after-9th-grade and summer-after-10th-grade leadership tracks. Because of that mixed structure, it is safer to leave the grade fields null for now.

## Session Length and Structure
The previous draft only said multi-session overnight. The official 2026 Dates & Rates page is now specific enough to normalize the visible duration range.

Published 2026 options include:
- 1 week sessions
- 10 day session
- 2 week sessions
- 3 week session

That supports:
- min_days: 7
- max_days: 21

This record should be treated as one-week-plus priority.

## Pricing
The official 2026 tuition page allows meaningful structured capture.

Published 2026 rates currently visible:
- One Week 1A: $2,185
- One Week 2A: $2,185
- One Week 4A: $2,185
- 10 Day 3A: $2,700
- Term 1: $3,890
- Term 2: $3,890
- Term 4: $3,890
- Term 3: $5,145

Structured pricing range captured:
- amount_min: 2185
- amount_max: 5145

Additional official pricing notes:
- Rates include the camp store account
- Deposit is $500 and refundable until January 31
- Invoice balances are due by April 15
- Credit-card tuition payments carry a 3% surcharge
- Additional-fee special programs include Horseback Riding and Wakeboarding
- There is a 5% discount for each additional child registered

## Location and Venue Notes
The official contact page gives the camp’s mailing address as 104 Balcones Springs Drive, Marble Falls, TX 78654. The homepage describes the property as being in the Texas Hill Country, just 40 miles northwest of Austin.

## Contact and Enrollment
Official site: https://campiscool.com/

Dates and rates:
https://campiscool.com/dates-rates

Registration link exposed from the official site:
https://balcones.campintouch.com/ui/forms/application/camper/App

Contact details:
- Email: info@campbalconessprings.com
- Phone: (830) 693-2267

## Leadership Notes
The draft’s leadership tag is supportable. The official high-school programs page says the camp’s older-camper programming is about building leadership skills and shaping campers into confident, inspiring role models. It specifically lists Senior Campers for the summer after 9th grade and Work Crew for the summer after 10th grade.

## Open Questions
- Latitude and longitude still need to be captured.
- A fully normalized grade-band model would need a more detailed per-session schema than the current single min/max grade fields.
- Boarding inclusion is likely implicit in the overnight model, but it was not stated in a way that I wanted to normalize into the YAML without a more explicit room-and-board statement.

## Sources
- https://campiscool.com/
- https://campiscool.com/dates-rates
- https://campiscool.com/contact-us
- https://campiscool.com/camp-life
- https://campiscool.com/camp-life/high-school-programs