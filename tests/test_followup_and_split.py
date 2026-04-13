from __future__ import annotations

from lib.followup_queue import generate_followup_queue
from lib.split_queue import generate_split_queue


def test_followup_queue_covers_expected_cases() -> None:
    rows = [
        {
            "candidate_id": "cand-1",
            "record_basis": "multi_venue_candidate",
            "canonical_url": "https://cty.jhu.edu/",
            "program_family": ["college-pre-college"],
            "priority_flags": {"college_precollege": True, "one_week_plus": True},
            "validation_needs": ["split_into_venue_records", "pricing", "contact", "confirm_recent_activity"],
        },
        {
            "candidate_id": "cand-2",
            "record_basis": "venue_candidate_pending_confirmation",
            "canonical_url": "https://cty.jhu.edu/",
            "program_family": ["traditional"],
            "priority_flags": {"college_precollege": False, "one_week_plus": False},
            "validation_needs": ["confirm_exact_venue", "confirm_overnight"],
        },
    ]
    queue = generate_followup_queue(rows)
    actions = {(item["candidate_id"], item["action"]) for item in queue}

    assert ("cand-1", "split_multi_venue_candidate") in actions
    assert ("cand-1", "capture_pricing") in actions
    assert ("cand-1", "duplicate_review") in actions
    assert ("cand-1", "priority_review_college_precollege") in actions
    assert ("cand-2", "confirm_exact_venue") in actions
    assert ("cand-2", "confirm_overnight") in actions


def test_split_queue_generates_stub_for_multi_venue_candidates() -> None:
    tasks, skeletons = generate_split_queue(
        [
            {
                "candidate_id": "cand-1",
                "record_basis": "multi_venue_candidate",
                "name": "CTY Residential",
                "operator_name": "Johns Hopkins University",
                "city": "Baltimore",
                "region": "MD",
                "country": "US",
                "canonical_url": "https://cty.jhu.edu/",
            }
        ]
    )
    assert len(tasks) == 1
    assert len(skeletons) == 1
    assert skeletons[0]["parent_candidate_id"] == "cand-1"
    assert skeletons[0]["record_basis"] == "venue_candidate_pending_confirmation"

