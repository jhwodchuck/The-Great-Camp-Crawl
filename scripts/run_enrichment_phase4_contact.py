#!/usr/bin/env python3
"""Phase 4 enrichment: deep contact extraction.

Finds all candidates where contact is 'partial' or 'missing',
constructs likely contact subpages (/contact, /contact-us) on the host,
and attempts to extract email, phone, and socials.
Falls back to a SearXNG search for contact subpages if direct fetches fail.
Merges updates into contact_enrichment_merged.jsonl.
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
from run_enrichment_phase2 import extract_contact_from_text, _enrichment_result, fetch_and_read_page


def run_phase4_contact(
    staging_path: Path,
    merged_contact_path: Path,
    output_dir: Path,
    text_dir: Path,
    html_dir: Path,
    manifest_path: Path,
    limit: int | None = None,
    batch_sleep: float = 0.5,
) -> dict:
    
    candidates = {c["candidate_id"]: c for c in read_jsonl(staging_path)}
    contact_results = read_jsonl(merged_contact_path)
    
    missing_contact = []
    for row in contact_results:
        cid = row["candidate_id"]
        # Partial means we usually just have a URL or operator, missing means nothing.
        if row.get("status") in ("missing", "partial"):
            if cid in candidates:
                missing_contact.append({
                    "candidate": candidates[cid],
                    "existing_contact": row
                })
                
    if limit:
        missing_contact = missing_contact[:limit]

    print(f"Phase 4: Targeted contact extraction for {len(missing_contact)} candidates")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    updated_contacts = []
    stats = {"processed": 0, "upgraded": 0, "failed_fetch": 0}
    
    for i, item in enumerate(missing_contact):
        candidate = item["candidate"]
        cid = candidate["candidate_id"]
        name = candidate.get("name", cid)
        url = candidate.get("canonical_url", "")
        
        host = extract_host(normalize_url(url)) if url else ""
        if not host:
            print(f"  [{i+1}/{len(missing_contact)}] {name}: no usable host")
            stats["failed_fetch"] += 1
            continue
            
        print(f"  [{i+1}/{len(missing_contact)}] {name}")
        
        contact = None
        candidate_upgraded = False
        evidence_url = ""
        evidence_snippet = ""
        
        # 1. Use deep search via SearXNG to find contact pages instantly
        query_str = f"site:{host} contact details OR email OR phone OR contact us"
        spec = QuerySpec(query=query_str, source="phase4_deep_contact")
        time.sleep(batch_sleep)
        search_res = search_duckduckgo(
            [spec], 
            providers=["searxng"], 
            timeout=15, 
            retries=2, 
            backoff_seconds=1.0
        )
        
        results = search_res.get("results", [])
        for search_item in results[:2]:
            result_url = search_item.get("normalized_url", "")
            snippet = search_item.get("snippet", "")
            
            if host not in result_url:
                continue
                
            time.sleep(batch_sleep)
            page_text = fetch_and_read_page(result_url, text_dir, html_dir, manifest_path)
            if page_text:
                extracted = extract_contact_from_text(page_text, result_url)
                if extracted and (extracted.get("email") or extracted.get("phone")):
                    contact = extracted
                    evidence_url = result_url
                    evidence_snippet = contact.pop("_evidence_snippet", snippet)
                    if not contact.get("operator"):
                        contact["operator"] = item["existing_contact"].get("contact", {}).get("operator")
                    if not contact.get("url"):
                        contact["url"] = item["existing_contact"].get("contact", {}).get("url", url)
                    break
        
        stats["processed"] += 1
        
        if contact and (contact.get("email") or contact.get("phone")):
            # It's an upgrade!
            # Ensure no missing required fields
            contact["url"] = contact.get("url") or url
            contact["operator"] = contact.get("operator") or name
            
            status = "found" if (contact.get("email") and contact.get("phone")) else "partial"
            
            res = _enrichment_result(
                cid, "contact", status, "medium", contact,
                evidence_snippet, evidence_url=evidence_url,
                notes="Extracted via Phase 4 deep subpage search.",
            )
            updated_contacts.append(res)
            candidate_upgraded = True
            
            disp = []
            if contact.get("email"): disp.append(contact["email"])
            if contact.get("phone"): disp.append(contact["phone"])
            print(f"    -> UPGRADED: {' / '.join(disp)}")
        else:
            print("    -> Missing/unclear contact info across subpages.")
            
        if candidate_upgraded:
            stats["upgraded"] += 1
    
    if updated_contacts:
        out_path = output_dir / "contact_enrichment_phase4.jsonl"
        write_jsonl(out_path, updated_contacts)
        print(f"\nPhase 4: {len(updated_contacts)} new contact results -> {out_path}")
        
        # Merge back into merged file
        merged_path = output_dir / "contact_enrichment_merged.jsonl"
        prior_rows = {r["candidate_id"]: r for r in contact_results}
        for u in updated_contacts:
            # We only overwrite if the new status is 'found' OR if prior status was 'missing'
            # Or if it's 'partial' but has more data than before
            prior = prior_rows[u["candidate_id"]]
            prior_status = prior.get("status")
            new_status = u.get("status")
            if new_status == "found" or (new_status == "partial" and prior_status == "missing"):
                 prior_rows[u["candidate_id"]] = u
            elif new_status == "partial" and prior_status == "partial":
                 # Favor the one with an email or phone over the one with just URL
                 prior_has_email = prior.get("contact", {}).get("email")
                 new_has_email = u.get("contact", {}).get("email")
                 prior_has_phone = prior.get("contact", {}).get("phone")
                 new_has_phone = u.get("contact", {}).get("phone")
                 
                 prior_score = (1 if prior_has_email else 0) + (1 if prior_has_phone else 0)
                 new_score = (1 if new_has_email else 0) + (1 if new_has_phone else 0)
                 
                 if new_score > prior_score:
                     prior_rows[u["candidate_id"]] = u
                     
        write_jsonl(merged_path, prior_rows.values())
        print(f"Merged into {merged_path}")
        
    summary = {
        "run_timestamp": utc_now_iso(),
        "phase": 4,
        "type": "contact",
        "candidates_processed": len(missing_contact),
        "phase4_stats": stats
    }
    
    summary_path = output_dir / "enrichment_phase4_contact_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    return summary


def main():
    parser = argparse.ArgumentParser(description="Phase 4 Deep Contact Extraction")
    parser.add_argument(
        "--staging-path",
        default="data/staging/discovered-candidates.jsonl",
    )
    parser.add_argument(
        "--merged-contact",
        default="data/enrichment/contact_enrichment_merged.jsonl",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--batch-sleep",
        type=float,
        default=0.5,
    )
    args = parser.parse_args()

    output_dir = Path("data/enrichment")
    text_dir = Path("data/raw/evidence-pages/text")
    html_dir = Path("data/raw/evidence-pages/html")
    manifest_path = Path("data/raw/evidence-pages/manifests/enrichment_capture_manifest.jsonl")

    summary = run_phase4_contact(
        staging_path=Path(args.staging_path),
        merged_contact_path=Path(args.merged_contact),
        output_dir=output_dir,
        text_dir=text_dir,
        html_dir=html_dir,
        manifest_path=manifest_path,
        limit=args.limit,
        batch_sleep=args.batch_sleep,
    )

    print(f"\nDone. Upgraded {summary['phase4_stats']['upgraded']} candidates out of {summary['candidates_processed']}.")

if __name__ == "__main__":
    main()
