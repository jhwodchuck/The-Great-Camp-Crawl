from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.report_ingestion import write_ingest_outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize and ingest gathered discovery reports into companion files and staging outputs"
    )
    parser.add_argument("--reports-dir", default="reports/discovery")
    parser.add_argument("--staging-dir", default="data/staging")
    args = parser.parse_args()

    summary = write_ingest_outputs(Path(args.reports_dir), Path(args.staging_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
