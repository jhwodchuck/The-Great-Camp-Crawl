from __future__ import annotations

from pathlib import Path

import responses

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
