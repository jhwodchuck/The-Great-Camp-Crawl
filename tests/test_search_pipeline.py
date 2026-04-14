from __future__ import annotations

from pathlib import Path

import responses

from lib import search_pipeline
from lib.search_pipeline import build_query_specs, search_duckduckgo


def test_build_query_specs_keeps_base_query_and_adds_scoped_variant() -> None:
    queries = build_query_specs(
        seed_queries=["Maryland pre-college residential program"],
        expand_queries=False,
        country="US",
        region="MD",
    )
    rendered = [(query.query, query.source) for query in queries]
    assert ("Maryland pre-college residential program", "cli") in rendered
    assert ("Maryland pre-college residential program US MD", "cli_scoped") in rendered


@responses.activate
def test_search_duckduckgo_lite_html_returns_results(fixture_path: Path) -> None:
    html = (fixture_path / "ddg" / "sample_lite_search.html").read_text(encoding="utf-8")
    responses.add(
        responses.GET,
        "https://lite.duckduckgo.com/lite/",
        body=html,
        status=200,
        content_type="text/html",
    )

    result = search_duckduckgo(
        queries=build_query_specs(["Johns Hopkins Engineering Innovation residential"], expand_queries=False),
        providers=["lite_html"],
    )

    assert result["counts"]["accepted_results"] == 1
    row = result["results"][0]
    assert row["provider"] == "lite_html"
    assert row["normalized_url"] == "https://ei.jhu.edu/locations/residential-locations"
    assert "Residential Programs" in row["title"]


def test_search_duckduckgo_google_cdp_provider_dispatches(monkeypatch) -> None:
    def fake_search_google_cdp(spec, timeout, query_index, searched_at):
        return [
            {
                "query": spec.query,
                "query_source": spec.source,
                "query_parent": spec.parent_query,
                "query_index": query_index,
                "search_timestamp": searched_at,
                "title": "Test Result",
                "url": "https://example.edu/program",
                "normalized_url": "https://example.edu/program",
                "snippet": "Residential summer program",
                "source": "google_search_cdp",
                "source_section": "organic_results",
                "provider": "google_cdp",
                "provider_rank": 1,
                "host": "example.edu",
                "status": "discovered_raw",
            }
        ]

    monkeypatch.setattr(search_pipeline, "_search_google_cdp", fake_search_google_cdp)

    result = search_duckduckgo(
        queries=build_query_specs(["test query"], expand_queries=False),
        providers=["google_cdp"],
    )

    assert result["counts"]["accepted_results"] == 1
    assert result["results"][0]["provider"] == "google_cdp"


@responses.activate
def test_search_duckduckgo_searxng_supports_engine_filter() -> None:
    responses.add(
        responses.GET,
        "http://localhost:8080/search",
        json={
            "results": [
                {
                    "title": "Camp Augusta",
                    "url": "https://campaugusta.org/contact/",
                    "content": "Camp Augusta is nestled near Nevada City.",
                }
            ]
        },
        status=200,
        content_type="application/json",
    )

    result = search_duckduckgo(
        queries=build_query_specs(["Camp Augusta Nevada City"], expand_queries=False),
        providers=["searxng"],
        searxng_base="http://localhost:8080",
        searxng_engines="mojeek",
    )

    assert result["counts"]["accepted_results"] == 1
    assert "engines=mojeek" in responses.calls[0].request.url
