from __future__ import annotations

from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from lib.common import slugify


TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "ref",
    "ref_src",
    "source",
    "spm",
    "trk",
}

TRACKING_QUERY_PREFIXES = ("utm_",)


def normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    parts = urlsplit(raw)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if not netloc and parts.path:
        reparsed = urlsplit(f"https://{raw}")
        scheme = reparsed.scheme.lower()
        netloc = reparsed.netloc.lower()
        path = reparsed.path
        query = reparsed.query
    else:
        path = parts.path
        query = parts.query

    if netloc.startswith("www."):
        netloc = netloc[4:]

    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    cleaned_path = path or "/"
    if cleaned_path != "/":
        cleaned_path = cleaned_path.rstrip("/")
        if not cleaned_path.startswith("/"):
            cleaned_path = f"/{cleaned_path}"

    query_pairs = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower in TRACKING_QUERY_KEYS:
            continue
        if any(key_lower.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        query_pairs.append((key, value))
    query_pairs.sort()
    cleaned_query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, cleaned_path, cleaned_query, ""))


def extract_host(url: str) -> str:
    return urlsplit(url).netloc.lower()


def host_matches(host: str, patterns: Iterable[str]) -> bool:
    host = host.lower()
    for pattern in patterns:
        normalized = pattern.lower().lstrip(".")
        if host == normalized or host.endswith(f".{normalized}"):
            return True
    return False


def is_host_allowed(url: str, allowlist: list[str], denylist: list[str]) -> bool:
    host = extract_host(normalize_url(url))
    if denylist and host_matches(host, denylist):
        return False
    if allowlist and not host_matches(host, allowlist):
        return False
    return True


def stable_url_token(url: str, length: int = 12) -> str:
    from lib.common import sha256_text

    return sha256_text(normalize_url(url))[:length]


def stable_capture_stem(url: str) -> str:
    normalized = normalize_url(url)
    parts = urlsplit(normalized)
    leaf = slugify(parts.path.rsplit("/", 1)[-1] or parts.netloc or "capture")
    host = slugify(parts.netloc or "site")
    return f"{host}-{leaf}-{stable_url_token(normalized, length=10)}"

