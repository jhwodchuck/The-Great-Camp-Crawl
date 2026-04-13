from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.common import compact_whitespace, parse_frontmatter_document, sha256_text, write_jsonl
from lib.url_utils import extract_host


def summarize_body(body: str, max_chars: int = 280) -> str:
    return compact_whitespace(body)[:max_chars]


def build_index_record(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter_document(raw)
    compact_body = compact_whitespace(body)
    words = [token for token in compact_body.split(" ") if token]
    resolved_url = frontmatter.get("resolved_url")
    source_url = frontmatter.get("source_url")
    host = frontmatter.get("resolved_host") or frontmatter.get("source_host") or extract_host(source_url or "")
    return {
        "capture_path": str(path),
        "source_url": source_url,
        "resolved_url": resolved_url,
        "source_host": frontmatter.get("source_host") or host,
        "resolved_host": host,
        "title": frontmatter.get("title"),
        "description": frontmatter.get("description"),
        "capture_timestamp": frontmatter.get("capture_timestamp"),
        "capture_method": frontmatter.get("capture_method"),
        "evidence_status": frontmatter.get("capture_status", "indexed"),
        "body_preview": summarize_body(body),
        "body_sha256": sha256_text(body),
        "body_length_chars": len(body),
        "body_word_count": len(words),
        "body_line_count": len(body.splitlines()),
        "status": "indexed",
    }


def index_capture_paths(paths: list[Path], output_path: Path | None = None) -> list[dict[str, Any]]:
    rows = [build_index_record(path) for path in sorted(paths)]
    if output_path:
        write_jsonl(output_path, rows)
    return rows


def discover_capture_paths(capture_dir: Path) -> list[Path]:
    return sorted(capture_dir.rglob("*.md"))

