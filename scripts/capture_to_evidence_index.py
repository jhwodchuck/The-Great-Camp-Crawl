from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def extract_frontmatter_and_body(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text
    fm_text, body = parts
    frontmatter: dict[str, Any] = {}
    for line in fm_text.splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter, body


def summarize_body(body: str, max_chars: int = 280) -> str:
    text = re.sub(r"\s+", " ", body).strip()
    return text[:max_chars]


def build_index_record(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = extract_frontmatter_and_body(raw)
    return {
        "capture_path": str(path),
        "source_url": frontmatter.get("source_url"),
        "source_host": frontmatter.get("source_host"),
        "title": frontmatter.get("title"),
        "description": frontmatter.get("description"),
        "capture_method": frontmatter.get("capture_method"),
        "body_preview": summarize_body(body),
        "body_length_chars": len(body),
        "status": "indexed",
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Index captured Markdown evidence pages into JSONL")
    parser.add_argument("capture_dir", nargs="?", default="data/raw/evidence-pages/text")
    parser.add_argument("--output", default="data/normalized/evidence_index.jsonl")
    args = parser.parse_args()

    capture_dir = Path(args.capture_dir)
    rows = [build_index_record(path) for path in sorted(capture_dir.rglob("*.md"))]
    write_jsonl(Path(args.output), rows)
    print(f"Wrote {len(rows)} evidence index records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
