from __future__ import annotations

from lib.region_prompt_pack import COUNTRY_REGION_SPECS, generate_prompt_pack, render_region_prompt


def test_region_prompt_pack_has_expected_country_counts() -> None:
    assert len(COUNTRY_REGION_SPECS["US"]) == 56
    assert len(COUNTRY_REGION_SPECS["CA"]) == 13
    assert len(COUNTRY_REGION_SPECS["MX"]) == 32


def test_render_region_prompt_is_ready_to_paste_without_max_placeholder() -> None:
    maryland = next(spec for spec in COUNTRY_REGION_SPECS["US"] if spec.region_code == "MD")
    prompt = render_region_prompt(maryland)

    assert "`run_slug`: `us-md-country-region-scan`" in prompt
    assert "`region_name`: `Maryland`" in prompt
    assert '"region": "MD"' in prompt
    assert "<max_candidates>" not in prompt
    assert "<run_slug>" not in prompt


def test_generate_prompt_pack_writes_expected_files(tmp_path) -> None:
    summary = generate_prompt_pack(tmp_path)

    assert summary["total"] == 101
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "TEMPLATE.md").exists()
    assert (tmp_path / "us" / "md-maryland.md").exists()
    assert (tmp_path / "ca" / "qc-quebec.md").exists()
    assert (tmp_path / "mx" / "cmx-ciudad-de-mexico.md").exists()
