from __future__ import annotations

import argparse
from pathlib import Path
from lib.evidence_index import discover_capture_paths, index_capture_paths
from lib.common import write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Index captured Markdown evidence pages into JSONL")
    parser.add_argument("capture_dir", nargs="?", default="data/raw/evidence-pages/text")
    parser.add_argument("--output", default="data/normalized/evidence_index.jsonl")
    parser.add_argument("--run-manifest", help="Optional run manifest used to index only this run's capture paths")
    args = parser.parse_args()

    if args.run_manifest:
        from lib.common import read_jsonl

        manifest_rows = read_jsonl(Path(args.run_manifest))
        capture_paths = []
        for row in manifest_rows:
            markdown_path = row.get("markdown_path")
            if not markdown_path:
                continue
            capture_paths.append(Path(markdown_path))
    else:
        capture_paths = discover_capture_paths(Path(args.capture_dir))
    rows = index_capture_paths(capture_paths)
    write_jsonl(Path(args.output), rows)
    print(f"Wrote {len(rows)} evidence index records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
