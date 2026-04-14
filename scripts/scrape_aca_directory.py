#!/usr/bin/env python3
import argparse
import json
import logging
from pathlib import Path

# Use the project's native discovery pipeline
from lib.search_pipeline import QuerySpec, search_duckduckgo


import concurrent.futures
import time
import random

STATE_NAMES = {
    'AK': 'Alaska', 'AL': 'Alabama', 'AR': 'Arkansas', 'AZ': 'Arizona',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'IA': 'Iowa',
    'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'MA': 'Massachusetts', 'MD': 'Maryland',
    'ME': 'Maine', 'MI': 'Michigan', 'MN': 'Minnesota', 'MO': 'Missouri',
    'MS': 'Mississippi', 'MT': 'Montana', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'NE': 'Nebraska', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
    'NV': 'Nevada', 'NY': 'New York', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VA': 'Virginia', 'VT': 'Vermont', 'WA': 'Washington', 'WI': 'Wisconsin',
    'WV': 'West Virginia', 'WY': 'Wyoming'
}

def scrape_state(state: str, out_dir: Path):
    state = state.upper()
    full_state = STATE_NAMES.get(state, state)
    
    # Stagger thread starts to avoid hitting DDOS protections
    time.sleep(random.uniform(0.5, 3.0))
    
    logging.info(f"Running ACA discovery sweep for {full_state} ({state})...")
    
    # We craft queries specifically tailored to find ACA-accredited camps for this state
    # Dropping strict quotes to allow DuckDuckGo to match "Residential", "Overnight", and full state names better
    queries = [
        QuerySpec(
            query=f'site:acacamps.org Resident {full_state} camp',
            source=f"aca-resident-{state.lower()}"
        ),
        QuerySpec(
            query=f'site:acacamps.org Overnight {full_state} camp',
            source=f"aca-overnight-{state.lower()}"
        )
    ]
    
    output_file = out_dir / f"us-{state.lower()}-aca-crawl.jsonl"
    
    result = search_duckduckgo(
        queries=queries,
        output_path=str(output_file),
        allow_hosts=[],
        deny_hosts=[],
        providers=["lite_html"],
        timeout=20,
        retries=3,
        backoff_seconds=1.0,
        sleep_seconds=2.0
    )
    
    logging.info(f"Finished {state}. Executed {result['counts']['queries']} queries, found {result['counts']['accepted_results']} raw results.")
    logging.info(f"Results written to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Systematically scrape ACA directory by State via Search")
    parser.add_argument("--states", nargs="+", help="State abbreviations (e.g., TX CA NY)", required=True)
    parser.add_argument("--output-dir", default="reports/discovery", help="Output directory")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent states to scrape")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(scrape_state, state, out_dir): state for state in args.states}
        for future in concurrent.futures.as_completed(futures):
            state = futures[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error scraping state {state}: {e}")

if __name__ == "__main__":
    main()
