from __future__ import annotations

from pathlib import Path

import responses

from lib.capture_pipeline import capture_urls
from lib.common import parse_frontmatter_document
from lib.evidence_index import build_index_record


@responses.activate
def test_capture_writes_markdown_and_evidence_index(
    fixture_path: Path,
    load_fixture_json,
    tmp_path: Path,
) -> None:
    html = (fixture_path / "html" / "sample_page.html").read_text(encoding="utf-8")
    responses.add(
        responses.GET,
        "https://ei.jhu.edu/",
        status=302,
        headers={"Location": "https://ei.jhu.edu/programs/residential/"},
    )
    responses.add(
        responses.GET,
        "https://ei.jhu.edu/programs/residential/",
        body=html,
        status=200,
        headers={"Content-Type": "text/html"},
    )

    tmp_root = tmp_path
    text_dir = tmp_root / "text"
    html_dir = tmp_root / "html"
    manifest_path = tmp_root / "manifest.jsonl"

    result = capture_urls(
        urls=["https://ei.jhu.edu/"],
        text_dir=text_dir,
        html_dir=html_dir,
        manifest_path=manifest_path,
        skip_existing=False,
    )

    manifest_row = result["manifest"][0]
    markdown_path = Path(manifest_row["markdown_path"])
    frontmatter, body = parse_frontmatter_document(markdown_path.read_text(encoding="utf-8"))

    assert manifest_row["status"] == "captured"
    assert frontmatter["source_url"] == "https://ei.jhu.edu/"
    assert frontmatter["resolved_url"] == "https://ei.jhu.edu/programs/residential"
    assert frontmatter["capture_status"] == "captured"
    assert "Residential Summer Engineering Program" in body
    assert "Site navigation" not in body

    index_record = build_index_record(markdown_path)
    expected = load_fixture_json("evidence/sample_index_record.json")
    for key, value in expected.items():
        assert index_record[key] == value
