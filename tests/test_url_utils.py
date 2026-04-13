from __future__ import annotations

from lib.url_utils import normalize_url


def test_normalize_url_removes_tracking_and_fragments() -> None:
    left = normalize_url("https://www.example.org/path/?utm_source=newsletter&a=1#section")
    right = normalize_url("https://example.org/path?a=1")
    assert left == right


def test_normalize_url_normalizes_default_ports_and_trailing_slash() -> None:
    assert normalize_url("https://example.org:443/path/") == "https://example.org/path"

