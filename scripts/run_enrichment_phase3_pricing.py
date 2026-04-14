#!/usr/bin/env python3
"""Phase 3 enrichment: deep tuition extraction using targeted searches.

Finds all candidates where pricing is still 'missing' (after Phase 2).
For each, searches for subpages using query "<candidate_name> OR site:<host> tuition OR pricing OR rates OR cost".
Fetches top results and attempts to extract pricing from page text or search snippets.
Merges updates into pricing_enrichment_merged.jsonl.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import read_jsonl, write_jsonl, ensure_parent, utc_now_iso
from lib.url_utils import extract_host, normalize_url
from lib.search_pipeline import QuerySpec, search_duckduckgo
from run_enrichment_phase2 import extract_pricing_from_text, _enrichment_result, fetch_and_read_page


def run_phase3(
    staging_path: Path,
    merged_pricing_path: Path,
    output_dir: Path,
    text_dir: Path,
    html_dir: Path,
    manifest_path: Path,
    limit: int | None = None,
    batch_sleep: float = 2.0,
) -> dict:
    
    # Load all base candidates
    candidates = {c["candidate_id"]: c for c in read_jsonl(staging_path)}
    
    # Load merged pricing status
    pricing_results = read_jsonl(merged_pricing_path)
    
    # Identify missing
    missing_pricing = []
    for row in pricing_results:
        cid = row["candidate_id"]
        if row.get("status") in ("missing", "partial"):
            if cid in candidates:
                missing_pricing.append({
                    "candidate": candidates[cid],
                    "existing_pricing": row
                })
                
    if limit:
        missing_pricing = missing_pricing[:limit]

    print(f"Phase 3: Targeted search for {len(missing_pricing)} candidates missing pricing")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    updated_pricing = []
    stats = {"searched": 0, "upgraded": 0, "failed_search": 0}
    
    for i, item in enumerate(missing_pricing):
        candidate = item["candidate"]
        cid = candidate["candidate_id"]
        name = candidate.get("name", cid)
        url = candidate.get("canonical_url", "")
        
        host = extract_host(normalize_url(url)) if url else ""
        
        # Build query
        if host:
            # If we know the host, search specifically on it for pricing terms
            query_str = f"site:{host} tuition OR rates"
        else:
            # If no host, search the candidate name plus pricing terms
            query_str = f"{name} overnight camp tuition"
        spec = QuerySpec(query=query_str, source="phase3_deep_pricing")
        
        if i > 0:
            time.sleep(batch_sleep)
            
        print(f"  [{i+1}/{len(missing_pricing)}] Searching: {query_str}")
        
        # Search using SearXNG
        search_res = search_duckduckgo(
            [spec], 
            providers=["searxng"], 
            timeout=15, 
            retries=2, 
            backoff_seconds=1.0
        )
        
        results = search_res.get("results", [])
        if not results:
            print(f"    -> No search results.")
            stats["failed_search"] += 1
            continue
            
        stats["searched"] += 1
        
        # Try fetching the top 2 results that match the host
        candidate_upgraded = False
        
        for search_item in results[:3]:
            result_url = search_item.get("normalized_url", "")
            snippet = search_item.get("snippet", "")
            
            # Prefer URLs on the same host if we know it
            if host and host not in result_url:
                continue
                
            # First try extracting from the search snippet directly as a fallback
            pricing = None
            if "$" in snippet:
                pricing = extract_pricing_from_text(snippet, result_url)
                
            # Then try fetching the full page
            page_text = fetch_and_read_page(result_url, text_dir, html_dir, manifest_path)
            if page_text:
                full_page_pricing = extract_pricing_from_text(page_text, result_url)
                if full_page_pricing and full_page_pricing.get("amount_min") is not None:
                    pricing = full_page_pricing
            
            if pricing and pricing.get("amount_min") is not None:
                evidence_snippet = pricing.pop("_evidence_snippet", snippet)
                res = _enrichment_result(
                    cid, "pricing", "found", "medium", pricing,
                    evidence_snippet, evidence_url=result_url,
                    notes="Extracted via deep Phase 3 subpage search.",
                )
                updated_pricing.append(res)
                candidate_upgraded = True
                print(f"    -> FOUND: {pricing['amount_min']}-{pricing['amount_max']} {pricing['currency']}")
                break
                
        if candidate_upgraded:
            stats["upgraded"] += 1
        else:
            print("    -> Missing/unclear pricing in top pages.")
    
    if updated_pricing:
        out_path = output_dir / "pricing_enrichment_phase3.jsonl"
        write_jsonl(out_path, updated_pricing)
        print(f"\nPhase 3: {len(updated_pricing)} new results -> {out_path}")
        
        # Merge back into merged file
        merged_path = output_dir / "pricing_enrichment_merged.jsonl"
        prior_rows = {r["candidate_id"]: r for r in pricing_results}
        for u in updated_pricing:
            prior_rows[u["candidate_id"]] = u
        write_jsonl(merged_path, prior_rows.values())
        print(f"Merged into {merged_path}")
        
    summary = {
        "run_timestamp": utc_now_iso(),
        "phase": 3,
        "candidates_processed": len(missing_pricing),
        "phase3_stats": stats
    }
    
    summary_path = output_dir / "enrichment_phase3_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    return summary


def main():
    parser = argparse.ArgumentParser(description="Phase 3 Deep Tuition Extraction")
    parser.add_argument(
        "--staging-path",
        default="data/staging/discovered-candidates.jsonl",
    )
    parser.add_argument(
        "--merged-pricing",
        default="data/enrichment/pricing_enrichment_merged.jsonl",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--batch-sleep",
        type=float,
        default=2.0,
    )
    args = parser.parse_args()

    output_dir = Path("data/enrichment")
    text_dir = Path("data/raw/evidence-pages/text")
    html_dir = Path("data/raw/evidence-pages/html")
    manifest_path = Path("data/raw/evidence-pages/manifests/enrichment_capture_manifest.jsonl")

    summary = run_phase3(
        staging_path=Path(args.staging_path),
        merged_pricing_path=Path(args.merged_pricing),
        output_dir=output_dir,
        text_dir=text_dir,
        html_dir=html_dir,
        manifest_path=manifest_path,
        limit=args.limit,
        batch_sleep=args.batch_sleep,
    )

    print(f"\nDone. Upgraded {summary['phase3_stats']['upgraded']} candidates out of {summary['candidates_processed']}.")

if __name__ == "__main__":
    main()
