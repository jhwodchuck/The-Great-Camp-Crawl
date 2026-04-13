from __future__ import annotations

from typing import Any

from lib.common import slugify
from lib.url_utils import normalize_url


def _duplicate_candidate_ids(rows: list[dict[str, Any]]) -> set[str]:
    seen_urls: dict[str, str] = {}
    duplicates: set[str] = set()
    for row in rows:
        normalized_url = normalize_url(row.get("canonical_url") or "")
        if not normalized_url:
            continue
        if normalized_url in seen_urls:
            duplicates.add(row["candidate_id"])
            duplicates.add(seen_urls[normalized_url])
        else:
            seen_urls[normalized_url] = row["candidate_id"]
    return duplicates


def generate_followup_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    duplicate_ids = _duplicate_candidate_ids(rows)
    items: list[dict[str, Any]] = []
    for row in rows:
        candidate_id = row["candidate_id"]
        validation_needs = set(row.get("validation_needs") or [])
        families = set(row.get("program_family") or [])
        priority_flags = row.get("priority_flags") or {}
        actions: list[tuple[str, str, str, str]] = []

        if row.get("record_basis") == "multi_venue_candidate":
            actions.append(
                (
                    "split_multi_venue_candidate",
                    "high",
                    "Venue-level final records are required by repository policy.",
                    "Identify each physical venue or session location and emit one venue candidate per site.",
                )
            )
        if "confirm_exact_venue" in validation_needs:
            actions.append(
                (
                    "confirm_exact_venue",
                    "high",
                    "The venue is not specific enough for a venue-level final record.",
                    "Confirm the exact campus, property, or session site before validation.",
                )
            )
        if "pricing" in validation_needs:
            actions.append(
                (
                    "capture_pricing",
                    "medium",
                    "Pricing is important downstream and is currently missing.",
                    "Capture tuition, lodging, deposits, and any boarding inclusion details.",
                )
            )
        if "contact" in validation_needs:
            actions.append(
                (
                    "capture_contact",
                    "medium",
                    "No contact details were preserved in the discovery-stage candidate.",
                    "Find an official email, phone, or admissions contact page.",
                )
            )
        if "confirm_recent_activity" in validation_needs:
            actions.append(
                (
                    "confirm_recent_activity",
                    "high",
                    "No strong past-24-month activity signal is currently preserved.",
                    "Capture session dates, registration, or recent season evidence from the last 24 months.",
                )
            )
        if "confirm_overnight" in validation_needs:
            actions.append(
                (
                    "confirm_overnight",
                    "high",
                    "Overnight or residential status is still uncertain.",
                    "Capture explicit overnight, lodging, dorm, or residential wording from an official source.",
                )
            )
        if candidate_id in duplicate_ids:
            actions.append(
                (
                    "duplicate_review",
                    "medium",
                    "Another candidate shares the same canonical URL.",
                    "Review whether these candidates represent the same physical venue or just related pages.",
                )
            )
        if "college-pre-college" in families or priority_flags.get("college_precollege"):
            actions.append(
                (
                    "priority_review_college_precollege",
                    "medium",
                    "College-run pre-college programs are a stated high-focus discovery area.",
                    "Prioritize validation and venue confirmation for this candidate.",
                )
            )
        if priority_flags.get("one_week_plus"):
            actions.append(
                (
                    "priority_review_one_week_plus",
                    "medium",
                    "Programs lasting one week or longer are a stated high-focus discovery area.",
                    "Prioritize duration confirmation and enrichment for this candidate.",
                )
            )

        for action, priority, why, next_step in actions:
            items.append(
                {
                    "followup_id": slugify(f"{candidate_id}-{action}"),
                    "candidate_id": candidate_id,
                    "action": action,
                    "priority": priority,
                    "why": why,
                    "next_step": next_step,
                    "status": "queued",
                }
            )
    items.sort(key=lambda row: (row["candidate_id"], row["action"]))
    return items

