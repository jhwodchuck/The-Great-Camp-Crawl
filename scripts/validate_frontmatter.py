from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required. Install with: pip install pyyaml")
    raise

REQUIRED_KEYS = ["record_id", "camp_id", "venue_id", "name", "country", "region", "city", "venue_name"]


def iter_markdown_files(root: Path):
    for path in root.rglob("*.md"):
        if path.name.lower() == "readme.md":
            continue
        yield path


def extract_frontmatter(text: str):
    if not text.startswith("---\n"):
        return None
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return None
    frontmatter = parts[0][4:]
    return yaml.safe_load(frontmatter) or {}


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("camps")
    failures = 0

    for path in iter_markdown_files(root):
        data = extract_frontmatter(path.read_text(encoding="utf-8"))
        if data is None:
            print(f"MISSING_FRONTMATTER {path}")
            failures += 1
            continue
        missing = [key for key in REQUIRED_KEYS if not data.get(key)]
        if missing:
            print(f"MISSING_KEYS {path}: {', '.join(missing)}")
            failures += 1

    if failures:
        print(f"Validation failed: {failures} issue(s) found.")
        return 1

    print("Frontmatter validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
