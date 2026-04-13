from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from search_duckduckgo import dedupe_hits, search_once, slugify
from html_to_markdown import convert_url_to_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DDG discovery and capture Markdown pages")
    parser.add_argument("query")
    parser.add_argument("--out-jsonl", default="data/staging/discovered-ddg-captured.jsonl")
    parser.add_argument("--capture-dir", default="data/raw/evidence-pages/text")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    hits = dedupe_hits(search_once(args.query))[: args.limit]
    capture_dir = Path(args.capture_dir)
    capture_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as fh:
        for hit in hits:
            markdown_path = None
            error = None
            try:
                parsed = urlparse(hit.url)
                stem = Path(parsed.path).stem or slugify(parsed.netloc) or "capture"
                markdown_path = capture_dir / f"{slugify(stem)}.md"
                markdown_path.write_text(convert_url_to_markdown(hit.url), encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                error = str(exc)

            record = {
                "query": hit.query,
                "title": hit.title,
                "url": hit.url,
                "snippet": hit.snippet,
                "markdown_capture_path": str(markdown_path) if markdown_path else None,
                "capture_error": error,
                "status": "captured" if error is None else "capture_failed",
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            time.sleep(args.sleep_seconds)

    print(f"Wrote capture records to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
