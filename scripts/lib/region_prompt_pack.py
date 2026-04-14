from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import unicodedata


@dataclass(frozen=True)
class RegionPromptSpec:
    country_code: str
    country_name: str
    country_slug: str
    region_code: str
    region_name: str
    language_mode: str
    source_focus: str
    query_angles: tuple[str, ...]

    @property
    def region_slug(self) -> str:
        return _slugify(self.region_name)

    @property
    def run_slug(self) -> str:
        return f"{self.country_slug}-{self.region_code.lower()}-country-region-scan"

    @property
    def relative_path(self) -> Path:
        filename = f"{self.region_code.lower()}-{self.region_slug}.md"
        return Path(self.country_slug) / filename


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


US_REGION_ROWS: tuple[tuple[str, str], ...] = (
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("AS", "American Samoa"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DC", "District of Columbia"),
    ("DE", "Delaware"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("GU", "Guam"),
    ("HI", "Hawaii"),
    ("IA", "Iowa"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("MA", "Massachusetts"),
    ("MD", "Maryland"),
    ("ME", "Maine"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MO", "Missouri"),
    ("MP", "Northern Mariana Islands"),
    ("MS", "Mississippi"),
    ("MT", "Montana"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("NE", "Nebraska"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NV", "Nevada"),
    ("NY", "New York"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("PR", "Puerto Rico"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VA", "Virginia"),
    ("VI", "U.S. Virgin Islands"),
    ("VT", "Vermont"),
    ("WA", "Washington"),
    ("WI", "Wisconsin"),
    ("WV", "West Virginia"),
    ("WY", "Wyoming"),
)

CA_REGION_ROWS: tuple[tuple[str, str], ...] = (
    ("AB", "Alberta"),
    ("BC", "British Columbia"),
    ("MB", "Manitoba"),
    ("NB", "New Brunswick"),
    ("NL", "Newfoundland and Labrador"),
    ("NS", "Nova Scotia"),
    ("NT", "Northwest Territories"),
    ("NU", "Nunavut"),
    ("ON", "Ontario"),
    ("PE", "Prince Edward Island"),
    ("QC", "Quebec"),
    ("SK", "Saskatchewan"),
    ("YT", "Yukon"),
)

MX_REGION_ROWS: tuple[tuple[str, str], ...] = (
    ("AGU", "Aguascalientes"),
    ("BCN", "Baja California"),
    ("BCS", "Baja California Sur"),
    ("CAM", "Campeche"),
    ("CHH", "Chihuahua"),
    ("CHP", "Chiapas"),
    ("CMX", "Ciudad de Mexico"),
    ("COA", "Coahuila"),
    ("COL", "Colima"),
    ("DUR", "Durango"),
    ("GRO", "Guerrero"),
    ("GUA", "Guanajuato"),
    ("HID", "Hidalgo"),
    ("JAL", "Jalisco"),
    ("MEX", "Estado de Mexico"),
    ("MIC", "Michoacan"),
    ("MOR", "Morelos"),
    ("NAY", "Nayarit"),
    ("NLE", "Nuevo Leon"),
    ("OAX", "Oaxaca"),
    ("PUE", "Puebla"),
    ("QUE", "Queretaro"),
    ("ROO", "Quintana Roo"),
    ("SIN", "Sinaloa"),
    ("SLP", "San Luis Potosi"),
    ("SON", "Sonora"),
    ("TAB", "Tabasco"),
    ("TAM", "Tamaulipas"),
    ("TLA", "Tlaxcala"),
    ("VER", "Veracruz"),
    ("YUC", "Yucatan"),
    ("ZAC", "Zacatecas"),
)


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
            "official program sites first; university pre-college pages and regional camp"
            " associations next; directories only for recall expansion"
        )
    if country_code == "CA":
        return (
            "official program sites first; provincial camp associations and university pages"
            " next; directories only for recall expansion"
        )
    return (
        "official program sites first; university and regional program pages next;"
        " directories only for recall expansion"
    )


def _query_angles(country_code: str, region_name: str, region_code: str) -> tuple[str, ...]:
    if country_code == "US":
        return (
            f'"overnight summer camp" "{region_name}"',
            f'"residential summer camp" "{region_name}"',
            f'"family camp" "{region_name}"',
            f'"youth retreat" "{region_name}" overnight',
            f'site:.edu "{region_name}" "pre-college" residential',
        )
    if country_code == "CA" and region_code == "QC":
        return (
            f'"camp de vacances" "{region_name}"',
            f'"camp residentiel" "{region_name}"',
            f'"camp avec hebergement" "{region_name}"',
            f'"camp familial" "{region_name}"',
            f'site:.ca "{region_name}" programme residentiel secondaire',
        )
    if country_code == "CA" and region_code == "NB":
        return (
            f'"overnight camp" "{region_name}"',
            f'"camp de vacances" "{region_name}"',
            f'"camp with accommodation" "{region_name}"',
            f'"camp residentiel" "{region_name}"',
            f'site:.ca "{region_name}" "pre-college" residential',
        )
    if country_code == "CA":
        return (
            f'"overnight camp" "{region_name}"',
            f'"residential camp" "{region_name}"',
            f'"camp with accommodation" "{region_name}"',
            f'"family camp" "{region_name}"',
            f'site:.ca "{region_name}" "pre-college" residential',
        )
    return (
        f'"campamento de verano con alojamiento" "{region_name}"',
        f'"campamento residencial" "{region_name}"',
        f'"campamento juvenil" "{region_name}"',
        f'"retiro juvenil" "{region_name}" hospedaje',
        f'site:.mx "{region_name}" programa residencial preuniversitario',
    )


def _build_region_specs(
    country_code: str,
    country_name: str,
    country_slug: str,
    rows: tuple[tuple[str, str], ...],
) -> tuple[RegionPromptSpec, ...]:
    return tuple(
        RegionPromptSpec(
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


US_REGION_SPECS = _build_region_specs("US", "United States", "us", US_REGION_ROWS)
CA_REGION_SPECS = _build_region_specs("CA", "Canada", "ca", CA_REGION_ROWS)
MX_REGION_SPECS = _build_region_specs("MX", "Mexico", "mx", MX_REGION_ROWS)

COUNTRY_REGION_SPECS: dict[str, tuple[RegionPromptSpec, ...]] = {
    "US": US_REGION_SPECS,
    "CA": CA_REGION_SPECS,
    "MX": MX_REGION_SPECS,
}

REGION_PROMPT_SPECS: tuple[RegionPromptSpec, ...] = (
    US_REGION_SPECS + CA_REGION_SPECS + MX_REGION_SPECS
)


def render_template_prompt() -> str:
    return """# Copy-Paste Discovery Prompt: Country And Region Scanner Template

Replace the placeholders only if you need a custom slice. For the ready-to-use prompts,
open one of the region files in this folder instead.

- `<run_slug>`
- `<country>`
- `<region>`
- `<region_name>`
- `<language_mode>`
- `<source_focus>`

---

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find plausible overnight or residential programs for children or teens in the assigned geography.
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

Coverage pattern:

- the assigned state, province, or territory
- major metros and city clusters
- camp-heavy rural or resort regions
- official program sites first
- directories only for recall expansion

Include:

- traditional overnight camps
- specialty camps
- sports, arts, music, academic, and STEM camps
- family camps
- faith-based camps and retreats
- college-run pre-college residential programs

Priority bias:

- college-run pre-college residential programs
- programs that appear to last one week or longer

Hard rules:

- Do not mark a program as qualifying unless there is evidence of overnight, residential, boarding, lodging, or housing tied to the program.
- Do not infer overnight status from photos, cabins, dorm buildings, rustic branding, or the word `camp` alone.
- One final record should map to one physical venue or one session location.
- If the source clearly covers multiple campuses or venues, keep it as a multi-venue lead.
- Preserve Spanish and French evidence when found.
- Do not invent missing facts.
- Use `null` for unknown scalar values.
- Use `[]` for known-empty lists.
- Use absolute URLs.

Working rules:

- Gather as many strong leads as you can in one uninterrupted pass for this one region.
- If the batch becomes too large or you near context or time limits, stop cleanly and put continuation searches in `next_queries`.
- Prefer official sites over directories.
- Do not pad the batch with weak directory-only leads.
- Keep evidence snippets short and exact.
- Use `venue_unconfirmed` when the site looks real but the venue is not specific yet.

Return exactly one JSON object with this shape:

```json
{
  "scan_type": "country_region",
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
      "program_family_tags": [],
      "camp_type_tags": [],
      "candidate_shape": "single_venue_candidate|venue_unconfirmed|multi_venue_candidate",
      "priority_flags": {
        "likely_college_precollege": null,
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


def render_region_prompt(spec: RegionPromptSpec) -> str:
    query_lines = "\n".join(f"- `{query}`" for query in spec.query_angles)
    return f"""# Copy-Paste Discovery Prompt: {spec.country_code} / {spec.region_code} / {spec.region_name}

Use this prompt as-is with an outside agent. The default `run_slug` is ready to use.

If a report with the same `run_slug` already exists, append a suffix like `-02` or `-03`
before saving.

You are gathering discovery data for The Great Camp Crawl.

This is a data-gathering task, not a prompt-editing task.
Do not rewrite these instructions.
Do not suggest improvements to the prompt.
Do the discovery work now.

Task:

- Find plausible overnight or residential programs for children or teens in this assigned region.
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

Search angles to cover:

{query_lines}

Coverage pattern:

- the assigned state, province, or territory
- major metros and city clusters
- camp-heavy rural or resort regions
- official program sites first
- directories only for recall expansion

Include:

- traditional overnight camps
- specialty camps
- sports, arts, music, academic, and STEM camps
- family camps
- faith-based camps and retreats
- college-run pre-college residential programs

Priority bias:

- college-run pre-college residential programs
- programs that appear to last one week or longer

Hard rules:

- Do not mark a program as qualifying unless there is evidence of overnight, residential, boarding, lodging, or housing tied to the program.
- Do not infer overnight status from photos, cabins, dorm buildings, rustic branding, or the word `camp` alone.
- One final record should map to one physical venue or one session location.
- If the source clearly covers multiple campuses or venues, keep it as a multi-venue lead.
- Preserve Spanish and French evidence when found.
- Do not invent missing facts.
- Use `null` for unknown scalar values.
- Use `[]` for known-empty lists.
- Use absolute URLs.

Working rules:

- Gather as many strong leads as you can in one uninterrupted pass for this one region.
- If the batch becomes too large or you near context or time limits, stop cleanly and put continuation searches in `next_queries`.
- Prefer official sites over directories.
- Do not pad the batch with weak directory-only leads.
- Keep evidence snippets short and exact.
- Use `venue_unconfirmed` when the site looks real but the venue is not specific yet.

Return exactly one JSON object with this shape:

```json
{{
  "scan_type": "country_region",
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
      "program_family_tags": [],
      "camp_type_tags": [],
      "candidate_shape": "single_venue_candidate|venue_unconfirmed|multi_venue_candidate",
      "priority_flags": {{
        "likely_college_precollege": null,
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
        "# Country And Region Scanner Prompt Pack",
        "",
        "This folder contains ready-to-paste discovery prompts for the country-and-region",
        "scanner. Each region gets its own file, so you do not need to hand-edit geography",
        "placeholders before sending the prompt to an outside agent.",
        "",
        "What changed from the old single prompt:",
        "",
        "- one file per region across the United States, Canada, and Mexico",
        "- no explicit `max_candidates` cap in this scanner path",
        "- fixed `run_slug` per region prompt",
        "- region-specific query angles baked into each file",
        "",
        "If you reuse the same region prompt multiple times, append a suffix like `-02` or",
        "`-03` to the `run_slug` before saving so files do not overwrite each other.",
        "",
        "Generated by `python scripts/generate_region_discovery_prompt_pack.py`.",
        "",
        f"- [Template](TEMPLATE.md)",
        f"- [United States](us/README.md) ({len(US_REGION_SPECS)} prompts)",
        f"- [Canada](ca/README.md) ({len(CA_REGION_SPECS)} prompts)",
        f"- [Mexico](mx/README.md) ({len(MX_REGION_SPECS)} prompts)",
        "",
    ]
    return "\n".join(lines)


def render_country_readme(country_code: str, specs: tuple[RegionPromptSpec, ...]) -> str:
    if not specs:
        raise ValueError(f"no region prompt specs for {country_code}")
    lines = [
        f"# {specs[0].country_name} Country And Region Scanner Prompts",
        "",
        "Use one file per outside-agent run. Each file is ready to paste as-is.",
        "",
    ]
    for spec in specs:
        filename = spec.relative_path.name
        lines.append(f"- [{spec.region_code} / {spec.region_name}]({filename})")
    lines.append("")
    return "\n".join(lines)


def generate_prompt_pack(output_root: Path) -> dict[str, int]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    (output_root / "README.md").write_text(render_root_readme(), encoding="utf-8")
    (output_root / "TEMPLATE.md").write_text(render_template_prompt(), encoding="utf-8")

    for country_code, specs in COUNTRY_REGION_SPECS.items():
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
        "US": len(US_REGION_SPECS),
        "CA": len(CA_REGION_SPECS),
        "MX": len(MX_REGION_SPECS),
        "total": len(REGION_PROMPT_SPECS),
    }
