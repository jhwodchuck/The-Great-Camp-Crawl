from __future__ import annotations

from typing import Any

from lib.common import slugify


def generate_split_queue(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks: list[dict[str, Any]] = []
    skeletons: list[dict[str, Any]] = []
    for row in rows:
        if row.get("record_basis") != "multi_venue_candidate":
            continue
        candidate_id = row["candidate_id"]
        task_id = slugify(f"{candidate_id}-split-task")
        tasks.append(
            {
                "split_task_id": task_id,
                "candidate_id": candidate_id,
                "name": row.get("name"),
                "operator_name": row.get("operator_name"),
                "canonical_url": row.get("canonical_url"),
                "status": "queued",
                "next_step": "Find each distinct physical venue or session site and create one candidate per venue.",
            }
        )
        skeletons.append(
            {
                "split_task_id": task_id,
                "parent_candidate_id": candidate_id,
                "record_basis": "venue_candidate_pending_confirmation",
                "name": row.get("name"),
                "operator_name": row.get("operator_name"),
                "venue_name": "venue to be confirmed",
                "city": row.get("city"),
                "region": row.get("region"),
                "country": row.get("country"),
                "canonical_url": row.get("canonical_url"),
                "status": "split_stub",
                "notes": [
                    "Created automatically from a multi-venue candidate.",
                    "Fill one copy of this stub per physical venue or session location.",
                ],
            }
        )
    tasks.sort(key=lambda row: row["candidate_id"])
    skeletons.sort(key=lambda row: row["parent_candidate_id"])
    return tasks, skeletons
