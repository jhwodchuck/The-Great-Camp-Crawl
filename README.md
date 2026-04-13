# The Great Camp Crawl

The Great Camp Crawl is a breadth-first research project for finding, validating, enriching, and browsing **overnight child and teen programs** across the **United States, Canada, and Mexico**.

This repository is designed to support yearly research for one child while still building a reusable multi-year knowledge base.

## Scope

Included program families:
- traditional summer camps
- specialty camps
- sports camps
- arts camps
- academic camps
- band and music camps
- church and religious retreats or camps
- family camps
- college-run pre-college residential programs

Current priorities:
- **maximum breadth first**
- **one file per physical location or session venue**
- **college-run pre-college residential programs get extra focus**
- **one-week-or-longer programs get extra focus**
- only include programs with evidence of activity in the **past 24 months**

## Repository layout

```text
assets/                  Branding and UI assets
camps/                   Final Markdown dossiers, one per venue
data/raw/                Raw evidence captures, notes, and discovery-run artifacts
data/staging/            Candidate and workflow queue files
data/normalized/         Structured exported records
reports/                 Coverage, validation, and enrichment summaries
prompts/system/          Grounding, schema, naming, quality, dedupe rules
prompts/discovery/       Discovery-agent prompts
templates/               Camp dossier and index templates
docs/                    MkDocs site content
scripts/                 Validation and build helpers
mkdocs.yml               Docs configuration
```

## Canonical record policy

- One Markdown file per **physical venue or session location**.
- Keep **raw evidence** and **discovery notes** for auditability.
- Do not reject non-English camps at discovery time.
- Pricing is expected in the final knowledge base but can be added in later enrichment passes.

## Recommended workflow

1. Run discovery agents by country, region, and specialty.
2. Stage candidates in `data/staging/discovered-candidates.jsonl`.
3. Validate overnight status, venue identity, and recent activity.
4. Enrich pricing, duration, age ranges, contact details, and taxonomy.
5. Render a final dossier into `camps/...`.
6. Publish browsable documentation through MkDocs.

## Docs site

This repo is scaffolded for **MkDocs Material** so the Markdown findings can be browsed like a lightweight documentation site.

Typical local setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install mkdocs-material pyyaml
mkdocs serve
```

## Important reference files

- `prompts/system/GROUNDING_RULES.md`
- `prompts/system/OUTPUT_SCHEMA.md`
- `prompts/system/NAMING_CONVENTIONS.md`
- `templates/camp.md`

## Naming convention

Recommended filename pattern:

```text
[camp-slug]--[country]-[region]-[city]-[venue-slug]--[record-id].md
```

Example:

```text
johns-hopkins-engineering-innovation--us-md-baltimore-homewood-campus--us-md-baltimore-homewood-campus.md
```

## Build intent

This repository is intentionally set up as a research system rather than a loose notes folder. The structure should support:
- discovery-agent swarms
- multi-stage enrichment
- QA and stale-record review
- yearly reuse and filtering for a specific child later

## Near-term next steps

- add the remaining discovery, validation, and enrichment prompts
- create normalization/export scripts
- add sample venue dossiers
- add search index generation for docs browsing
