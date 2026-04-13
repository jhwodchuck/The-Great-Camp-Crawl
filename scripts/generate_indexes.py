from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re

CAMPS_ROOT = Path("camps")
DOCS_CAMPS_ROOT = Path("docs/camps")


def titleize_slug(value: str) -> str:
    return re.sub(r"-+", " ", value).title()


def main() -> int:
    grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)

    for path in CAMPS_ROOT.rglob("*.md"):
        parts = path.parts
        if len(parts) < 4:
            continue
        _, country, region, *_ = parts
        grouped[(country, region)].append(path)

    for (country, region), files in grouped.items():
        out_dir = DOCS_CAMPS_ROOT / country
        out_dir.mkdir(parents=True, exist_ok=True)
        index_path = out_dir / f"{region}.md"
        lines = [f"# {country.upper()} / {region.upper()}", "", "## Venue records", ""]
        for file in sorted(files):
            label = titleize_slug(file.stem.split("--")[0])
            rel = Path("../../..") / file
            lines.append(f"- [{label}]({rel.as_posix()})")
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("Generated regional indexes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
