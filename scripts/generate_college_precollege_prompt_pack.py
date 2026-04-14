from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.college_precollege_prompt_pack import generate_prompt_pack


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the college-pre-college discovery prompt pack"
    )
    parser.add_argument(
        "--output-root",
        default="prompts/discovery/02-college-precollege-scanner-pack",
        help="Directory that will receive the generated prompt pack",
    )
    args = parser.parse_args()

    summary = generate_prompt_pack(Path(args.output_root))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
