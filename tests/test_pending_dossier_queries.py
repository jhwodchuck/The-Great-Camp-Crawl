from __future__ import annotations

from lib.pending_dossier_queries import build_pending_query_pack, build_queries_for_record


def test_build_queries_for_record_prefers_official_host_and_current_year() -> None:
    record = {
        "candidate_id": "cand-us-ca-nevada-city-camp-augusta-pending-venue-campaugusta-org",
        "name": "Camp Augusta",
        "city": "Nevada City",
        "region": "CA",
        "country": "US",
        "canonical_url": "https://campaugusta.org/",
        "record_basis": "venue_candidate",
        "reasons": ["unknown_venue"],
    }

    queries = build_queries_for_record(record, current_year=2026)

    assert queries == [
        'site:campaugusta.org "Camp Augusta" Nevada City CA location',
        'site:campaugusta.org "Camp Augusta" Nevada City CA address',
        'site:campaugusta.org "Camp Augusta" Nevada City CA summer 2026',
    ]


def test_build_pending_query_pack_filters_and_dedupes_query_lines() -> None:
    rows = [
        {
            "candidate_id": "cand-1",
            "name": "Camp Echo",
            "city": "Austin",
            "region": "TX",
            "country": "US",
            "canonical_url": "https://example.org/camp-echo",
            "record_basis": "venue_candidate_pending_confirmation",
            "reasons": ["pending_venue_confirmation"],
        },
        {
            "candidate_id": "cand-2",
            "name": "Camp Echo",
            "city": "Austin",
            "region": "TX",
            "country": "US",
            "canonical_url": "https://example.org/another-page",
            "record_basis": "venue_candidate_pending_confirmation",
            "reasons": ["unknown_venue"],
        },
        {
            "candidate_id": "cand-3",
            "name": "Camp Multi",
            "city": "Austin",
            "region": "TX",
            "country": "US",
            "canonical_url": "https://example.org/multi",
            "record_basis": "multi_venue_candidate",
            "reasons": ["multi_venue_candidate", "unknown_city"],
        },
    ]

    pack = build_pending_query_pack(rows, current_year=2026)

    assert pack["summary"]["selected_records"] == 2
    assert pack["summary"]["selected_queries"] == 3
    assert pack["summary"]["reason_counts"] == {
        "pending_venue_confirmation": 1,
        "unknown_venue": 1,
    }
    assert pack["query_rows"][0]["candidate_ids"] == ["cand-1", "cand-2"]
