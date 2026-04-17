# Web LLM Discovery Prompts

Use these prompts with web-enabled chat agents when you want manual discovery help for under-covered regions or program families.

These prompts are for **discovery-stage candidate finding**, not final validation.

## When to use

Use only after:

1. running gap analysis
2. confirming the gap is real
3. choosing a target country, region, and/or program family

## Core rules to embed in every prompt

Every web agent prompt should reinforce these rules:

- Scope includes US, Canada, and Mexico.
- In-scope families: traditional overnight camps, specialty camps, sports camps, arts camps, music and band camps, academic and STEM camps, family camps, faith-based camps and retreats, and college-run pre-college residential programs.
- Do not count a program as qualifying without evidence of overnight, residential, boarding, lodging, dorms, residence halls, housing, or similar wording tied to the program.
- Prefer official operator, camp, university, or venue pages.
- Directory pages are acceptable discovery inputs, but weak proof.
- One candidate should represent one physical venue or session location.
- If a source covers multiple campuses or venues, return it as a multi-venue lead instead of inventing a single site.
- Preserve Spanish and French evidence when relevant.
- Do not invent city, venue, ages, pricing, or dates.
- Capture evidence snippets and URLs.
- Prefer activity evidence from the last 24 months when visible.

## Output contract

Ask the agent to return JSON only.

Use this shape:

```json
[
  {
    "name": "Program name",
    "operator_name": "Operator if known",
    "website_url": "https://official-site.example/program",
    "evidence_url": "https://source-for-overnight-or-activity-proof",
    "country": "US",
    "region": "TX",
    "city": "Austin",
    "venue_name": "Venue if explicit",
    "program_family": ["college-pre-college", "academic"],
    "camp_types": ["residential", "overnight"],
    "status_guess": "candidate",
    "overnight_evidence": "Short quoted or paraphrased snippet",
    "recent_activity_evidence": "Short snippet with exact visible year/date if available",
    "source_type": "official",
    "multi_venue_risk": "low",
    "duplicate_risk_note": "Same operator may have multiple campuses; keep venue-specific if possible",
    "notes": "Anything ambiguous or worth checking later"
  }
]
```

Allowed `status_guess` values:

- `candidate`
- `multi_venue_lead`
- `weak_lead`
- `reject`

## Universal system prompt

Use this as the system message when the web agent supports one:

```text
You are helping build a catalog of overnight and residential youth programs in the United States, Canada, and Mexico.

In scope:
- traditional overnight camps
- specialty camps
- sports camps
- arts camps
- music and band camps
- academic and STEM camps
- family camps
- faith-based camps and retreats
- college-run pre-college residential programs

Hard rules:
- Do not classify a program as in scope without evidence of overnight, residential, boarding, lodging, housing, dorms, residence halls, or equivalent wording tied to the program.
- Prefer official program, operator, institution, or venue pages.
- Directory pages can be used to discover candidates, but not as strong proof when official pages exist.
- One candidate must represent one physical venue or one session location.
- If a source covers multiple campuses or venues, do not invent a single location. Mark it as multi_venue_lead instead.
- Preserve ambiguity instead of guessing.
- Preserve Spanish and French evidence where relevant.
- If visible, capture evidence of activity within the last 24 months.

Return JSON only. Do not add prose outside the JSON.
```

## Prompt 1: Regional gap-fill sweep

Use when a state, province, or Mexican state is under-covered.

```text
Search the web for overnight or residential youth programs in [COUNTRY] / [REGION].

Goal:
Find 20-40 plausible discovery-stage candidates for this region.

Priorities:
- official camp or program pages first
- official university pages for residential pre-college programs
- official church, retreat, YMCA, scout, arts, sports, STEM, or family camp pages
- only include candidates with at least one visible overnight/residential signal, or clearly return them as weak_lead if the source looks promising but the overnight evidence is not yet explicit

Do not include:
- day camps only
- campground rentals with no youth program
- general tourism pages
- directories as final candidates when official pages are available
- social posts unless they are the only trace of a real program

For each result:
- prefer one official page per candidate
- capture one short overnight/residential evidence snippet
- capture one recent activity snippet if visible
- identify city and venue only if explicit
- if multiple campuses are covered on one page, mark multi_venue_lead

Return JSON only using the agreed schema.
```

## Prompt 2: Program-family sweep

Use when a family is underrepresented in a region.

```text
Search the web for [PROGRAM_FAMILY] programs in [COUNTRY] / [REGION] that are overnight or residential.

Examples of [PROGRAM_FAMILY]:
- traditional overnight
- sports
- arts
- music
- academic
- stem
- family
- faith-based
- college-pre-college

Goal:
Find 15-30 plausible candidates with official pages and brief evidence.

Rules:
- do not include programs without a visible overnight/residential signal unless you label them weak_lead
- prefer venue-specific pages over umbrella brand pages
- if the operator has multiple venues, keep them separate when the venue is explicit
- if venue is not explicit, return multi_venue_lead instead of guessing

Return JSON only using the agreed schema.
```

## Prompt 3: College pre-college residential sweep

Use for `.edu`-heavy searches and university-hosted residential programs.

```text
Search for college-run pre-college residential programs in [COUNTRY] / [REGION].

In scope:
- pre-college residential programs
- residential summer academies
- university-hosted high school summer programs with housing
- academic institutes, scholars programs, and summer intensives for high school students when they include residence halls, dorms, housing, or boarding

Important:
- do not exclude a result only because it is not a traditional camp
- university-hosted residential youth programs are in scope
- look for wording like residence halls, housing, live on campus, dormitory, boarding, campus housing, meals included, or residential program

Goal:
Find 20+ plausible candidates with strong official evidence.

Return JSON only using the agreed schema.
```

## Prompt 4: French-Canada sweep

Use for Quebec and other French-language discovery.

```text
Search French-language web sources for overnight or residential youth programs in [PROVINCE], Canada.

Prioritize terms like:
- camp résidentiel
- camp d'été avec hébergement
- séjour linguistique résidentiel
- camp musical avec hébergement
- camp sportif résidentiel
- programme préuniversitaire résidentiel

Rules:
- keep French evidence snippets in French
- prefer official camp, school, university, church, and organization pages
- if the page is only a directory, try to follow through to the official page
- do not invent English translations inside the JSON fields except where needed for notes

Return JSON only using the agreed schema.
```

## Prompt 5: Mexico / Spanish-language sweep

Use for Mexico and Spanish-language discovery in the US or Canada when relevant.

```text
Search Spanish-language web sources for overnight or residential youth programs in [STATE], Mexico.

Prioritize terms like:
- campamento residencial
- campamento de verano con hospedaje
- campamento juvenil con alojamiento
- campamento deportivo residencial
- campamento de arte con internado
- programa preuniversitario residencial

Rules:
- preserve Spanish evidence snippets in Spanish
- prefer official camp, school, university, parish, retreat, and operator pages
- do not treat campground rentals or tourism lodging as camps
- if the source covers multiple locations, mark multi_venue_lead

Return JSON only using the agreed schema.
```

## Prompt 6: Follow official links from weak sources

Use when a directory or article gives you names, but you need the official page.

```text
I already have weak discovery leads. For each lead below, find the most likely official program page and determine whether there is explicit overnight or residential evidence.

Rules:
- prefer official domains over directories, social media, news, or listicles
- if you cannot find an official page, keep the lead but mark source_type as weak
- do not upgrade a lead to candidate without a direct program page or very strong evidence
- if multiple venues exist, do not collapse them

Leads:
[PASTE LEADS HERE]

Return JSON only using the agreed schema.
```

## Prompt 7: De-junking prompt

Use when a web agent is returning garbage.

```text
Re-run the search more strictly.

Exclude:
- social media pages
- news stories
- directories unless no official source exists
- campgrounds and venue rentals
- tourism sites
- shopping pages
- dictionary pages
- unrelated youth organizations without a specific overnight program
- day camps without lodging evidence

Only keep:
- official program pages
- official university pages for residential pre-college programs
- official organization pages for overnight youth or family programs

If a candidate does not have explicit overnight/residential wording, downgrade it to weak_lead instead of candidate.

Return JSON only using the agreed schema.
```

## Suggested workflow with chat agents

1. Start with Prompt 1 or Prompt 2.
2. Run Prompt 6 on the weaker leads.
3. Run Prompt 7 if the first pass returns junk.
4. Do DB dedup checks before import.
5. Keep multi-venue leads separate from venue-specific candidates.

## Practical guidance

- Ask for `20-40` results, not `5-10`.
- Tell the agent to return JSON only.
- Tell it not to argue about scope; you have already defined it.
- Explicitly say that university-hosted residential programs are in scope.
- Explicitly forbid invented venue names and city guesses.
- If an agent is weak on large searches, split by region and family:
  - `Texas + sports`
  - `Texas + arts`
  - `Texas + college-pre-college`
  - `Texas + faith-based`

