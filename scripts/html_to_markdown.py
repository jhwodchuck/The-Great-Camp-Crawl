from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.capture_pipeline import capture_urls
from lib.url_utils import stable_capture_stem


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a page and convert its main content to Markdown")
    parser.add_argument("url")
    parser.add_argument("--output")
    parser.add_argument("--html-output")
    parser.add_argument("--manifest", default="data/raw/evidence-pages/manifests/manual_capture_manifest.jsonl")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    default_stem = stable_capture_stem(args.url)
    text_dir = Path(args.output).parent if args.output else Path("data/raw/evidence-pages/text")
    html_dir = Path(args.html_output).parent if args.html_output else Path("data/raw/evidence-pages/html")
    result = capture_urls(
        urls=[args.url],
        text_dir=text_dir,
        html_dir=html_dir,
        manifest_path=Path(args.manifest),
        timeout=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        skip_existing=not args.no_skip_existing,
    )
    manifest_row = result["manifest"][0]
    if args.output and manifest_row.get("markdown_path") and manifest_row["status"] in {"captured", "unchanged", "skipped_existing"}:
        source = Path(manifest_row["markdown_path"])
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        manifest_row["markdown_path"] = str(destination)
    if args.html_output and manifest_row.get("html_path") and manifest_row["status"] in {"captured", "unchanged"}:
        source = Path(manifest_row["html_path"])
        destination = Path(args.html_output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        manifest_row["html_path"] = str(destination)
    print(json.dumps({"url": args.url, "stem": default_stem, **manifest_row}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
