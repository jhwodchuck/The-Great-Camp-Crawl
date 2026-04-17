#!/usr/bin/env python3
"""
Prepare the MkDocs site for building.

Steps:
  1. Copy every camp dossier from camps/ into docs/camps/<country>/<region>/<slug>.md
     so MkDocs can serve them (files must live inside docs_dir).
  2. Re-generate the per-region index pages in docs/camps/ with corrected relative
     links pointing at the copied files rather than ../../../camps/...
  3. Re-write the mkdocs.yml nav so every region appears in the sidebar.

Run before `mkdocs build` or `mkdocs gh-deploy`.
"""
from __future__ import annotations

import re
import shutil
from collections import defaultdict
from pathlib import Path

import yaml  # PyYAML

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPS_ROOT = REPO_ROOT / "camps"
DOCS_ROOT = REPO_ROOT / "docs"
DOCS_CAMPS_ROOT = DOCS_ROOT / "camps"
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"

# ---------------------------------------------------------------------------
# Display-name maps
# ---------------------------------------------------------------------------

US_STATES: dict[str, str] = {
    "ak": "Alaska",
    "al": "Alabama",
    "ar": "Arkansas",
    "az": "Arizona",
    "ca": "California",
    "co": "Colorado",
    "ct": "Connecticut",
    "dc": "District of Columbia",
    "de": "Delaware",
    "fl": "Florida",
    "ga": "Georgia",
    "hi": "Hawaii",
    "ia": "Iowa",
    "id": "Idaho",
    "il": "Illinois",
    "in": "Indiana",
    "ks": "Kansas",
    "ky": "Kentucky",
    "la": "Louisiana",
    "ma": "Massachusetts",
    "md": "Maryland",
    "me": "Maine",
    "mi": "Michigan",
    "mn": "Minnesota",
    "mo": "Missouri",
    "ms": "Mississippi",
    "nc": "North Carolina",
    "nd": "North Dakota",
    "ne": "Nebraska",
    "nh": "New Hampshire",
    "nj": "New Jersey",
    "nm": "New Mexico",
    "nv": "Nevada",
    "ny": "New York",
    "oh": "Ohio",
    "ok": "Oklahoma",
    "or": "Oregon",
    "pa": "Pennsylvania",
    "ri": "Rhode Island",
    "sc": "South Carolina",
    "sd": "South Dakota",
    "tn": "Tennessee",
    "tx": "Texas",
    "ut": "Utah",
    "va": "Virginia",
    "vt": "Vermont",
    "wa": "Washington",
    "wi": "Wisconsin",
    "wv": "West Virginia",
    "wy": "Wyoming",
}

CANADA_PROVINCES: dict[str, str] = {
    "ab": "Alberta",
    "bc": "British Columbia",
    "mb": "Manitoba",
    "nb": "New Brunswick",
    "nl": "Newfoundland and Labrador",
    "ns": "Nova Scotia",
    "on": "Ontario",
    "pe": "Prince Edward Island",
    "qc": "Quebec",
    "sk": "Saskatchewan",
}

MEXICO_STATES: dict[str, str] = {
    "ags": "Aguascalientes",
    "bc": "Baja California",
    "bcs": "Baja California Sur",
    "camp": "Campeche",
    "chis": "Chiapas",
    "chih": "Chihuahua",
    "coah": "Coahuila",
    "col": "Colima",
    "cdmx": "Mexico City",
    "dgo": "Durango",
    "gto": "Guanajuato",
    "gro": "Guerrero",
    "hgo": "Hidalgo",
    "jal": "Jalisco",
    "mex": "State of Mexico",
    "mich": "Michoacán",
    "mor": "Morelos",
    "nay": "Nayarit",
    "nl": "Nuevo León",
    "oax": "Oaxaca",
    "pue": "Puebla",
    "qro": "Querétaro",
    "qroo": "Quintana Roo",
    "slp": "San Luis Potosí",
    "sin": "Sinaloa",
    "son": "Sonora",
    "tab": "Tabasco",
    "tamps": "Tamaulipas",
    "tlax": "Tlaxcala",
    "ver": "Veracruz",
    "yuc": "Yucatán",
    "zac": "Zacatecas",
}

COUNTRY_LABELS = {"us": "United States", "canada": "Canada", "mexico": "Mexico"}


def region_display_name(country: str, region: str) -> str:
    if country == "us":
        return US_STATES.get(region, region.upper())
    if country == "canada":
        return CANADA_PROVINCES.get(region, region.upper())
    if country == "mexico":
        return MEXICO_STATES.get(region, region.upper())
    return region.upper()


def titleize_slug(value: str) -> str:
    return re.sub(r"-+", " ", value).title()


# ---------------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------------


def main() -> int:
    # ---- Step 0: Clean previously generated camp pages from docs/ ----------
    # Remove individual dossier subdirectories and regional index files so
    # stale entries (regions with no current dossiers) don't cause broken links.
    for country_dir in (DOCS_CAMPS_ROOT / "us", DOCS_CAMPS_ROOT / "canada", DOCS_CAMPS_ROOT / "mexico"):
        if country_dir.exists():
            for child in country_dir.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                elif child.suffix == ".md":
                    child.unlink()

    # ---- Step 1: Discover all camp dossiers --------------------------------

    grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)

    for src in sorted(CAMPS_ROOT.rglob("*.md")):
        parts = src.relative_to(CAMPS_ROOT).parts
        if len(parts) < 3:
            continue
        country, region = parts[0], parts[1]
        grouped[(country, region)].append(src)

    # ---- Step 2: Copy dossiers into docs/ and regenerate index pages -------

    for (country, region), src_files in sorted(grouped.items()):
        dest_dir = DOCS_CAMPS_ROOT / country / region
        dest_dir.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# {COUNTRY_LABELS.get(country, country.title())} / {region_display_name(country, region)}",
            "",
            "## Venue records",
            "",
        ]

        for src in sorted(src_files):
            dest = dest_dir / src.name
            shutil.copy2(src, dest)

            label = titleize_slug(src.stem.split("--")[0])
            # Relative link from the index page (docs/camps/<country>/<region>.md)
            # to the individual file (docs/camps/<country>/<region>/<slug>.md)
            rel = Path(region) / src.name
            lines.append(f"- [{label}]({rel.as_posix()})")

        index_path = DOCS_CAMPS_ROOT / country / f"{region}.md"
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  {country}/{region}: {len(src_files)} dossier(s)")

    # ---- Step 3: Regenerate docs/camps/index.md ----------------------------

    root_lines = [
        "# Venue Records",
        "",
        "Browsable camp and program dossiers by region.",
        "",
    ]
    for country_key in ("us", "canada", "mexico"):
        country_label = COUNTRY_LABELS[country_key]
        regions = sorted(
            region for (c, _) in grouped if c == country_key
            for region in [_]
        )
        if not regions:
            continue
        root_lines += [f"## {country_label}", ""]
        for region in regions:
            display = region_display_name(country_key, region)
            root_lines.append(f"- [{display}]({country_key}/{region}.md)")
        root_lines.append("")

    (DOCS_CAMPS_ROOT / "index.md").write_text("\n".join(root_lines), encoding="utf-8")

    # ---- Step 4: Build the nav section -------------------------------------

    def region_nav_entry(country: str, region: str) -> dict:
        display = region_display_name(country, region)
        return {display: f"camps/{country}/{region}.md"}

    venue_nav: list = [{"Overview": "camps/index.md"}]

    for country_key, country_label in COUNTRY_LABELS.items():
        regions = sorted(
            region for (c, region) in grouped if c == country_key
        )
        if not regions:
            continue
        sub = [region_nav_entry(country_key, r) for r in regions]
        venue_nav.append({country_label: sub})

    # ---- Step 5: Rewrite mkdocs.yml nav ------------------------------------

    with open(MKDOCS_YML, encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    # Ensure docs_dir is set to 'docs' (MkDocs default) and strip any legacy
    # 'docs/' prefixes from existing nav entries so all paths are relative to
    # the docs/ directory consistently.
    config.pop("docs_dir", None)  # let it default to 'docs/'

    def _strip_docs_prefix(nav_list: list) -> list:
        """Recursively strip leading 'docs/' from nav path values."""
        result = []
        for item in nav_list:
            if isinstance(item, dict):
                new_item = {}
                for key, val in item.items():
                    if isinstance(val, str) and val.startswith("docs/"):
                        new_item[key] = val[len("docs/"):]
                    elif isinstance(val, list):
                        new_item[key] = _strip_docs_prefix(val)
                    else:
                        new_item[key] = val
                result.append(new_item)
            else:
                result.append(item)
        return result

    cleaned_nav = _strip_docs_prefix(config.get("nav", []))

    # Replace (or append) the Venue Records entry
    new_nav = []
    replaced = False
    for entry in cleaned_nav:
        if isinstance(entry, dict) and "Venue Records" in entry:
            new_nav.append({"Venue Records": venue_nav})
            replaced = True
        else:
            new_nav.append(entry)

    if not replaced:
        new_nav.append({"Venue Records": venue_nav})

    config["nav"] = new_nav

    with open(MKDOCS_YML, "w", encoding="utf-8") as fh:
        yaml.dump(config, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print("Updated mkdocs.yml nav.")

    total = sum(len(v) for v in grouped.values())
    print(f"\nDone. {total} dossiers copied across {len(grouped)} regions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
