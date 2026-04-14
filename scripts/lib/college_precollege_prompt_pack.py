"""
Generate the college-pre-college scanner prompt pack.

Mirrors the structure of region_prompt_pack.py but produces prompts
focused exclusively on college- and university-hosted residential
pre-college programs (scan_type = "college_precollege").

Each region gets one ready-to-paste file with baked-in:
  - run_slug
  - country / region / region_name
  - language_mode
  - source_focus
  - search angles targeting .edu and university pages
  - max_candidates (default 25)
"""
from __future__ import annotations

import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# Re-use the geography tables from the region pack.
from lib.region_prompt_pack import (
    US_REGION_ROWS,
    CA_REGION_ROWS,
    MX_REGION_ROWS,
)

MAX_CANDIDATES: int = 25


@dataclass(frozen=True)
class CollegePromptSpec:
    country_code: str
    country_name: str
    country_slug: str
    region_code: str
    region_name: str
    language_mode: str
    source_focus: str
    query_angles: tuple[str, ...]
    max_candidates: int = MAX_CANDIDATES

    @property
    def region_slug(self) -> str:
        return _slugify(self.region_name)

    @property
    def run_slug(self) -> str:
        return f"{self.country_slug}-{self.region_code.lower()}-college-precollege-scan"

    @property
    def relative_path(self) -> Path:
        filename = f"{self.region_code.lower()}-{self.region_slug}.md"
        return Path(self.country_slug) / filename


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    pieces: list[str] = []
    previous_dash = False
    for char in ascii_value.lower():
        if char.isalnum():
            pieces.append(char)
            previous_dash = False
            continue
        if previous_dash:
            continue
        pieces.append("-")
        previous_dash = True
    slug = "".join(pieces).strip("-")
    return slug or "region"


def _language_mode(country_code: str, region_code: str) -> str:
    if country_code == "US":
        return "english-first; keep Spanish and French evidence when encountered"
    if country_code == "CA" and region_code == "QC":
        return "french-first; keep English evidence when encountered"
    if country_code == "CA" and region_code == "NB":
        return "bilingual English/French; preserve whichever language the source uses"
    if country_code == "CA":
        return "english-first; keep French evidence when encountered"
    return "spanish-first; keep English evidence when encountered"


def _source_focus(country_code: str) -> str:
    if country_code == "US":
        return (
            "official university and college program pages first (.edu preferred);"
            " camp association directories only for recall expansion"
        )
    if country_code == "CA":
        return (
            "official university and college program pages first (.ca .edu preferred);"
            " provincial associations only for recall expansion"
        )
    return (
        "official university program pages first (.mx .edu sites preferred);"
        " regional directories only for recall expansion"
    )


def _query_angles(country_code: str, region_name: str, region_code: str) -> tuple[str, ...]:
    if country_code == "US":
        return (
            f'site:.edu "{region_name}" "pre-college" residential',
            f'site:.edu "{region_name}" "summer program" residential overnight',
            f'site:.edu "{region_name}" "summer immersion" OR "summer institute" residential',
            f'"{region_name}" university "summer camp" residential "high school"',
            f'"{region_name}" college "summer program" residential "boarding" OR "dorm"',
        )
    if country_code == "CA" and region_code == "QC":
        return (
            f'site:.ca "{region_name}" "programme preuniversitaire" residentiel',
            f'site:.ca "{region_name}" "programme d\'ete" residentiel secondaire',
            f'"{region_name}" universite "camp ete" residentiel secondaire',
            f'"{region_name}" college "programme residentiel" "secondaire" OR "lycee"',
            f'"{region_name}" university "summer program" residential "high school"',
        )
    if country_code == "CA" and region_code == "NB":
        return (
            f'site:.ca "{region_name}" "pre-college" residential',
            f'site:.ca "{region_name}" "summer program" residential overnight',
            f'site:.ca "{region_name}" "programme d\'ete" residentiel secondaire',
            f'"{region_name}" university college "summer camp" residential "high school"',
            f'"{region_name}" universite "programme residentiel" secondaire',
        )
    if country_code == "CA":
        return (
            f'site:.ca "{region_name}" "pre-college" residential',
            f'site:.ca "{region_name}" "summer program" residential overnight',
            f'site:.ca "{region_name}" "summer institute" OR "summer immersion" residential',
            f'"{region_name}" university "summer camp" residential "high school"',
            f'"{region_name}" college "summer program" residential "boarding" OR "dorm"',
        )
    # Mexico
    return (
        f'site:.mx "{region_name}" "programa preuniversitario" residencial',
        f'site:.mx "{region_name}" "programa de verano" residencial preparatoria',
        f'"{region_name}" universidad "campamento" residencial "preparatoria" OR "bachillerato"',
        f'"{region_name}" universidad "verano" "internado" OR "residencia" preparatoria',
        f'"{region_name}" colegio "programa residencial" preparatoria',
    )


# ---------------------------------------------------------------------------
# Build specs
# ---------------------------------------------------------------------------

def _build_specs(
    country_code: str,
    country_name: str,
    country_slug: str,
    rows: tuple[tuple[str, str], ...],
) -> tuple[CollegePromptSpec, ...]:
    return tuple(
        CollegePromptSpec(
            country_code=country_code,
            country_name=country_name,
            country_slug=country_slug,
            region_code=region_code,
            region_name=region_name,
            language_mode=_language_mode(country_code, region_code),
            source_focus=_source_focus(country_code),
            query_angles=_query_angles(country_code, region_name, region_code),
        )
        for region_code, region_name in rows
    )


US_COLLEGE_SPECS = _build_specs("US", "United States", "us", US_REGION_ROWS)
CA_COLLEGE_SPECS = _build_specs("CA", "Canada", "ca", CA_REGION_ROWS)
MX_COLLEGE_SPECS = _build_specs("MX", "Mexico", "mx", MX_REGION_ROWS)

COUNTRY_COLLEGE_SPECS: dict[str, tuple[CollegePromptSpec, ...]] = {
    "US": US_COLLEGE_SPECS,
    "CA": CA_COLLEGE_SPECS,
    "MX": MX_COLLEGE_SPECS,
}

ALL_COLLEGE_SPECS: tuple[CollegePromptSpec, ...] = (
    US_COLLEGE_SPECS + CA_COLLEGE_SPECS + MX_COLLEGE_SPECS
)


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_template_prompt() -> str:
    return """\
# Copy-Paste Discovery Prompt: College Pre-College Scanner Template

Replace the placeholders only if you need a custom slice. For the ready-to-use prompts,
open one of the region files in this folder instead.

- `<run_slug>`
- `<country>`
- `<region>`
- `<region_name>`
- `<language_mode>`
- `<source_focus>`
- `<max_candidates>`

---

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find overnight or residential pre-college programs hosted by colleges and universities
  in the assigned region.
- Work only on this bounded slice.
- Save the gathered report to `reports/discovery/<run_slug>.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `<run_slug>`
- `country`: `<country>`
- `region`: `<region>`
- `region_name`: `<region_name>`
- `language_mode`: `<language_mode>`
- `source_focus`: `<source_focus>`
- `max_candidates`: `<max_candidates>`

Search focus:

- pre-college
- summer session
- residential program
- academic immersion
- university summer program
- on-campus summer program
- youth residential institute
- secondary school summer residency

Search posture:

- Prefer official university pages.
- Look for housing, residence hall, dorm, campus-life, or residential-life pages tied to the program.
- Capture a venue or campus name whenever visible.
- Tag likely one-week-plus programs only when the wording supports it.

Exclude:

- commuter-only programs
- online-only programs
- vague campus marketing with no youth program

Hard rules:

- Do not assume a program is residential just because it happens on a campus.
- Do not merge multiple campuses into one venue record.
- Keep multi-campus pages as `multi_venue_candidate`.
- Preserve uncertainty instead of guessing.
- Use `null` for unknown scalar values.
- Use `[]` for known-empty lists.
- Use absolute URLs.

Working rules:

- Return at most `<max_candidates>` candidates in one batch.
- Favor fewer high-signal candidates over weak lists.
- If more good leads exist, stop and put continuation searches in `next_queries`.

Return exactly one JSON object with this shape:

```json
{
  "scan_type": "college_precollege",
  "scope": {
    "country": "<country>",
    "region": "<region>",
    "city": null
  },
  "queries_used": [],
  "next_queries": [],
  "candidates": [
    {
      "candidate_name": "",
      "translated_name_hint": null,
      "operator_name": null,
      "venue_name": null,
      "city": null,
      "region": "<region>",
      "country": "<country>",
      "canonical_url": "",
      "supporting_urls": [],
      "directory_source_url": null,
      "source_language": null,
      "program_family_tags": ["college-pre-college"],
      "camp_type_tags": [],
      "candidate_shape": "single_venue_candidate|venue_unconfirmed|multi_venue_candidate",
      "priority_flags": {
        "likely_college_precollege": true,
        "likely_one_week_plus": null
      },
      "duration_hint_text": null,
      "overnight_evidence": {
        "snippet": null,
        "url": null
      },
      "recent_activity_evidence": {
        "snippet": null,
        "url": null,
        "date_text": null
      },
      "notes": null,
      "validation_needs": [],
      "confidence": "low|medium|high"
    }
  ]
}
```

When finished:

- Save the JSON to `reports/discovery/<run_slug>.json` if you can write files.
- Otherwise return only the JSON object.
- After the JSON, if non-JSON wrapper text is allowed, add only:
  - saved path
  - candidate count
  - next query count
  - blockers
"""


def render_region_prompt(spec: CollegePromptSpec) -> str:
    query_lines = "\n".join(f"- `{q}`" for q in spec.query_angles)
    return f"""\
# Copy-Paste Discovery Prompt: {spec.country_code} / {spec.region_code} / {spec.region_name} — College Pre-College Scanner

Use this prompt as-is with an outside agent. The default `run_slug` is ready to use.

If a report with the same `run_slug` already exists, append a suffix like `-02` or `-03`
before saving.

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find overnight or residential pre-college programs hosted by colleges and universities
  in this assigned region.
- Work only on this bounded slice.
- Save the gathered report to `reports/discovery/{spec.run_slug}.json` if you have file-write access.
- If you do not have file-write access, return only the JSON object so it can be saved to that path.

Assigned slice:

- `run_slug`: `{spec.run_slug}`
- `country`: `{spec.country_code}`
- `region`: `{spec.region_code}`
- `region_name`: `{spec.region_name}`
- `language_mode`: `{spec.language_mode}`
- `source_focus`: `{spec.source_focus}`
- `max_candidates`: `{spec.max_candidates}`

Search angles to cover:

{query_lines}

Search focus:

- pre-college
- summer session
- residential program
- academic immersion
- university summer program
- on-campus summer program
- youth residential institute
- secondary school summer residency

Search posture:

- Prefer official university pages.
- Look for housing, residence hall, dorm, campus-life, or residential-life pages tied to the program.
- Capture a venue or campus name whenever visible.
- Tag likely one-week-plus programs only when the wording supports it.

Exclude:

- commuter-only programs
- online-only programs
- vague campus marketing with no youth program

Hard rules:

- Do not assume a program is residential just because it happens on a campus.
- Do not merge multiple campuses into one venue record.
- Keep multi-campus pages as `multi_venue_candidate`.
- Preserve uncertainty instead of guessing.
- Use `null` for unknown scalar values.
- Use `[]` for known-empty lists.
- Use absolute URLs.

Working rules:

- Return at most `{spec.max_candidates}` candidates in one batch.
- Favor fewer high-signal candidates over weak lists.
- If more good leads exist, stop and put continuation searches in `next_queries`.

Return exactly one JSON object with this shape:

```json
{{
  "scan_type": "college_precollege",
  "scope": {{
    "country": "{spec.country_code}",
    "region": "{spec.region_code}",
    "city": null
  }},
  "queries_used": [],
  "next_queries": [],
  "candidates": [
    {{
      "candidate_name": "",
      "translated_name_hint": null,
      "operator_name": null,
      "venue_name": null,
      "city": null,
      "region": "{spec.region_code}",
      "country": "{spec.country_code}",
      "canonical_url": "",
      "supporting_urls": [],
      "directory_source_url": null,
      "source_language": null,
      "program_family_tags": ["college-pre-college"],
      "camp_type_tags": [],
      "candidate_shape": "single_venue_candidate|venue_unconfirmed|multi_venue_candidate",
      "priority_flags": {{
        "likely_college_precollege": true,
        "likely_one_week_plus": null
      }},
      "duration_hint_text": null,
      "overnight_evidence": {{
        "snippet": null,
        "url": null
      }},
      "recent_activity_evidence": {{
        "snippet": null,
        "url": null,
        "date_text": null
      }},
      "notes": null,
      "validation_needs": [],
      "confidence": "low|medium|high"
    }}
  ]
}}
```

When finished:

- Save the JSON to `reports/discovery/{spec.run_slug}.json` if you can write files.
- Otherwise return only the JSON object.
- After the JSON, if non-JSON wrapper text is allowed, add only:
  - saved path
  - candidate count
  - next query count
  - blockers
"""


def render_root_readme() -> str:
    lines = [
        "# College Pre-College Scanner Prompt Pack",
        "",
        "This folder contains ready-to-paste discovery prompts for the college pre-college",
        "scanner. Each region gets its own file, pre-filled with university-focused search",
        "angles so you do not need to edit placeholders before sending the prompt to an",
        "outside agent.",
        "",
        "What changed from the old single `02-college-precollege-scanner.md` prompt:",
        "",
        "- one file per region across the United States, Canada, and Mexico",
        "- `max_candidates` set to 25 per batch (increase in the file if needed)",
        "- fixed `run_slug` per region prompt",
        "- region-specific query angles targeting `.edu` and university pages",
        "",
        "If you reuse the same region prompt multiple times, append a suffix like `-02` or",
        "`-03` to the `run_slug` before saving so files do not overwrite each other.",
        "",
        "Generated by `python scripts/generate_college_precollege_prompt_pack.py`.",
        "",
        f"- [Template](TEMPLATE.md)",
        f"- [United States](us/README.md) ({len(US_COLLEGE_SPECS)} prompts)",
        f"- [Canada](ca/README.md) ({len(CA_COLLEGE_SPECS)} prompts)",
        f"- [Mexico](mx/README.md) ({len(MX_COLLEGE_SPECS)} prompts)",
        "",
    ]
    return "\n".join(lines)


def render_country_readme(country_code: str, specs: tuple[CollegePromptSpec, ...]) -> str:
    if not specs:
        raise ValueError(f"no college prompt specs for {country_code}")
    lines = [
        f"# {specs[0].country_name} College Pre-College Scanner Prompts",
        "",
        "Use one file per outside-agent run. Each file is ready to paste as-is.",
        "",
    ]
    for spec in specs:
        filename = spec.relative_path.name
        lines.append(f"- [{spec.region_code} / {spec.region_name}]({filename})")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_prompt_pack(output_root: Path) -> dict[str, int]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    (output_root / "README.md").write_text(render_root_readme(), encoding="utf-8")
    (output_root / "TEMPLATE.md").write_text(render_template_prompt(), encoding="utf-8")

    for country_code, specs in COUNTRY_COLLEGE_SPECS.items():
        country_dir = output_root / specs[0].country_slug
        country_dir.mkdir(parents=True, exist_ok=True)
        (country_dir / "README.md").write_text(
            render_country_readme(country_code, specs),
            encoding="utf-8",
        )
        for spec in specs:
            prompt_path = output_root / spec.relative_path
            prompt_path.write_text(render_region_prompt(spec), encoding="utf-8")

    return {
        "US": len(US_COLLEGE_SPECS),
        "CA": len(CA_COLLEGE_SPECS),
        "MX": len(MX_COLLEGE_SPECS),
        "total": len(ALL_COLLEGE_SPECS),
    }
