#!/usr/bin/env python3
"""Phase 4 enrichment: deep demographics extraction.

Finds all candidates where age_grade or duration is 'missing',
constructs targeted search queries to extract them from snippets or deep links.
Merges updates into age_grade_enrichment_merged.jsonl and duration_enrichment_merged.jsonl.
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
from run_enrichment_phase2 import extract_age_grade_from_text, extract_duration_from_text, _enrichment_result, fetch_and_read_page


def run_phase4_demographics(
    staging_path: Path,
    merged_age_path: Path,
    merged_duration_path: Path,
    output_dir: Path,
    text_dir: Path,
    html_dir: Path,
    manifest_path: Path,
    limit: int | None = None,
    batch_sleep: float = 0.5,
) -> dict:
    
    candidates = {c["candidate_id"]: c for c in read_jsonl(staging_path)}
    age_results = read_jsonl(merged_age_path)
    dur_results = read_jsonl(merged_duration_path)
    
    age_map = {r["candidate_id"]: r for r in age_results}
    dur_map = {r["candidate_id"]: r for r in dur_results}
    
    missing_cids = set()
    for cid, row in age_map.items():
        if row.get("status") in ("missing",):
            missing_cids.add(cid)
    for cid, row in dur_map.items():
        if row.get("status") in ("missing",):
            missing_cids.add(cid)
            
    missing_cids = missing_cids.intersection(set(candidates.keys()))
    
    missing_items = [{"cid": cid, "cand": candidates[cid]} for cid in missing_cids]
    if limit:
        missing_items = missing_items[:limit]

    print(f"Phase 4: Targeted demographic extraction for {len(missing_items)} candidates")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    updated_ages = []
    updated_durs = []
    stats = {"processed": 0, "age_upgraded": 0, "dur_upgraded": 0}
    
    for i, item in enumerate(missing_items):
        candidate = item["cand"]
        cid = item["cid"]
        name = candidate.get("name", cid)
        url = candidate.get("canonical_url", "")
        
        host = extract_host(normalize_url(url)) if url else ""
        if not host:
            continue
            
        is_missing_age = age_map[cid].get("status") == "missing"
        is_missing_dur = dur_map[cid].get("status") == "missing"
        
        print(f"  [{i+1}/{len(missing_items)}] {name} (missing Age:{is_missing_age}, Dur:{is_missing_dur})")
        
        query_str = f"site:{host} ages OR grades OR dates OR duration OR sessions"
        spec = QuerySpec(query=query_str, source="phase4_deep_demographics")
        
        time.sleep(batch_sleep)
        search_res = search_duckduckgo(
            [spec], 
            providers=["searxng"], 
            timeout=15, 
            retries=2, 
            backoff_seconds=1.0
        )
        
        results = search_res.get("results", [])
        
        age_contact = None
        dur_contact = None
        
        for search_item in results[:2]:
            result_url = search_item.get("normalized_url", "")
            snippet = search_item.get("snippet", "")
            
            if host not in result_url:
                continue
                
            time.sleep(batch_sleep)
            page_text = fetch_and_read_page(result_url, text_dir, html_dir, manifest_path)
            if not page_text:
                continue
                
            if is_missing_age and not age_contact:
                age_extracted = extract_age_grade_from_text(page_text)
                if age_extracted and (age_extracted.get("min_age") or age_extracted.get("min_grade")):
                    evidence = age_extracted.pop("_evidence_snippet", snippet)
                    age_contact = _enrichment_result(
                        cid, "age_grade", "found", "medium", age_extracted,
                        evidence, evidence_url=result_url,
                        notes="Extracted via Phase 4 deep subpage search.",
                    )
                    updated_ages.append(age_contact)
                    stats["age_upgraded"] += 1
                    print(f"    -> AGE UPGRADE")

            if is_missing_dur and not dur_contact:
                dur_extracted = extract_duration_from_text(page_text)
                if dur_extracted and dur_extracted.get("max_duration_days"):
                    evidence = dur_extracted.pop("_evidence_snippet", snippet)
                    dur_contact = _enrichment_result(
                        cid, "duration", "found", "medium", dur_extracted,
                        evidence, evidence_url=result_url,
                        notes="Extracted via Phase 4 deep subpage search.",
                    )
                    updated_durs.append(dur_contact)
                    stats["dur_upgraded"] += 1
                    print(f"    -> DUR UPGRADE")
                    
            if (not is_missing_age or age_contact) and (not is_missing_dur or dur_contact):
                break
                
        stats["processed"] += 1
    
    if updated_ages:
        out_path = output_dir / "age_grade_enrichment_phase4.jsonl"
        write_jsonl(out_path, updated_ages)
        for u in updated_ages: age_map[u["candidate_id"]] = u
        write_jsonl(merged_age_path, age_map.values())
        print(f"Merged {len(updated_ages)} ages into {merged_age_path}")
        
    if updated_durs:
        out_path = output_dir / "duration_enrichment_phase4.jsonl"
        write_jsonl(out_path, updated_durs)
        for u in updated_durs: dur_map[u["candidate_id"]] = u
        write_jsonl(merged_duration_path, dur_map.values())
        print(f"Merged {len(updated_durs)} durations into {merged_duration_path}")
        
    summary = {
        "run_timestamp": utc_now_iso(),
        "phase": 4,
        "type": "demographics",
        "candidates_processed": len(missing_items),
        "phase4_stats": stats
    }
    
    summary_path = output_dir / "enrichment_phase4_demographics_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    return summary


def main():
    parser = argparse.ArgumentParser(description="Phase 4 Deep Demographics Extraction")
    parser.add_argument(
        "--staging-path", default="data/staging/discovered-candidates.jsonl",
    )
    parser.add_argument(
        "--limit", "-n", type=int, default=None,
    )
    parser.add_argument(
        "--batch-sleep", type=float, default=0.5,
    )
    args = parser.parse_args()

    output_dir = Path("data/enrichment")
    text_dir = Path("data/raw/evidence-pages/text")
    html_dir = Path("data/raw/evidence-pages/html")
    manifest_path = Path("data/raw/evidence-pages/manifests/enrichment_capture_manifest.jsonl")

    run_phase4_demographics(
        staging_path=Path(args.staging_path),
        merged_age_path=output_dir / "age_grade_enrichment_merged.jsonl",
        merged_duration_path=output_dir / "duration_enrichment_merged.jsonl",
        output_dir=output_dir,
        text_dir=text_dir,
        html_dir=html_dir,
        manifest_path=manifest_path,
        limit=args.limit,
        batch_sleep=args.batch_sleep,
    )

if __name__ == "__main__":
    main()
