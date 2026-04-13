from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch DuckDuckGo search wrapper using a query file")
    parser.add_argument("--query-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--query-log")
    parser.add_argument("--country")
    parser.add_argument("--region")
    parser.add_argument("--program-family")
    parser.add_argument("--allow-host-file")
    parser.add_argument("--deny-host-file")
    parser.add_argument("--providers", default="instant_answer,lite_html")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--no-expand", action="store_true")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "scripts/search_duckduckgo.py",
        "--query-file",
        args.query_file,
        "--output",
        args.output,
        "--timeout",
        str(args.timeout),
        "--retries",
        str(args.retries),
        "--backoff-seconds",
        str(args.backoff_seconds),
        "--sleep-seconds",
        str(args.sleep_seconds),
        "--providers",
        args.providers,
    ]
    if args.query_log:
        cmd.extend(["--query-log", args.query_log])
    if args.country:
        cmd.extend(["--country", args.country])
    if args.region:
        cmd.extend(["--region", args.region])
    if args.program_family:
        cmd.extend(["--program-family", args.program_family])
    if args.allow_host_file:
        cmd.extend(["--allow-host-file", args.allow_host_file])
    if args.deny_host_file:
        cmd.extend(["--deny-host-file", args.deny_host_file])
    if args.no_expand:
        cmd.append("--no-expand")
    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
