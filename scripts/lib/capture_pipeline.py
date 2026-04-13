from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

from lib.common import USER_AGENT, build_frontmatter_document, compact_whitespace, read_jsonl, sha256_bytes, utc_now_iso
from lib.url_utils import extract_host, normalize_url, stable_capture_stem


def fetch_response(
    session: requests.Session,
    url: str,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(backoff_seconds * attempt)
    if last_error is None:
        raise RuntimeError("capture failed without an error")
    raise last_error


def _score_content_node(node: Tag) -> int:
    text = compact_whitespace(node.get_text(" ", strip=True))
    if not text:
        return 0
    paragraphs = len(node.find_all("p"))
    headings = len(node.find_all(["h1", "h2", "h3"]))
    links = len(node.find_all("a"))
    return len(text) + (paragraphs * 120) + (headings * 80) - (links * 8)


def _pick_content_node(soup: BeautifulSoup) -> Tag:
    for selector in ["main", "article", "[role=main]"]:
        found = soup.select_one(selector)
        if isinstance(found, Tag):
            return found

    candidates = [node for node in soup.find_all(["section", "div", "body"]) if isinstance(node, Tag)]
    scored = sorted(candidates, key=_score_content_node, reverse=True)
    for candidate in scored:
        if _score_content_node(candidate) > 200:
            return candidate
    if soup.body:
        return soup.body
    return soup


def extract_markdown_content(html: str, page_url: str) -> tuple[str, dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe", "form", "button", "input"]):
        tag.decompose()
    for selector in ["nav", "footer", "aside"]:
        for tag in soup.select(selector):
            tag.decompose()

    title = compact_whitespace(soup.title.get_text(" ", strip=True)) if soup.title else ""
    description = ""
    description_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if description_tag and description_tag.get("content"):
        description = compact_whitespace(str(description_tag["content"]))

    canonical_url = ""
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    if canonical_tag and canonical_tag.get("href"):
        canonical_url = normalize_url(urljoin(page_url, str(canonical_tag["href"])))

    lang = ""
    if soup.html and soup.html.get("lang"):
        lang = str(soup.html["lang"]).strip()

    content_node = _pick_content_node(soup)
    markdown_body = md(str(content_node), heading_style="ATX", bullets="-")
    markdown_body = "\n".join(line.rstrip() for line in markdown_body.splitlines())
    markdown_body = markdown_body.replace("\r\n", "\n")
    markdown_body = compact_whitespace(markdown_body) if not markdown_body.strip() else markdown_body.strip()
    markdown_body = "\n".join(line for line in markdown_body.splitlines() if line.strip() or line == "")
    markdown_body = markdown_body.replace("\n\n\n", "\n\n")

    metadata = {
        "title": title or None,
        "description": description or None,
        "canonical_url_meta": canonical_url or None,
        "language_hint": lang or None,
    }
    return markdown_body.strip(), metadata


def _existing_capture_record(source_url: str, text_dir: Path) -> dict[str, Any] | None:
    stem = stable_capture_stem(source_url)
    markdown_path = text_dir / f"{stem}.md"
    html_path = text_dir.parent / "html" / f"{stem}.html"
    if markdown_path.exists():
        return {
            "status": "skipped_existing",
            "source_url": source_url,
            "normalized_source_url": normalize_url(source_url),
            "markdown_path": str(markdown_path),
            "html_path": str(html_path) if html_path.exists() else None,
        }
    return None


def capture_urls(
    urls: list[str],
    text_dir: Path,
    html_dir: Path,
    manifest_path: Path,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: float = 1.0,
    sleep_seconds: float = 0.0,
    skip_existing: bool = True,
) -> dict[str, Any]:
    text_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    existing_manifest = read_jsonl(manifest_path)
    results: list[dict[str, Any]] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for url in urls:
        if skip_existing:
            existing = _existing_capture_record(url, text_dir)
            if existing:
                results.append(existing)
                continue

        captured_at = utc_now_iso()
        stem = stable_capture_stem(url)
        html_path = html_dir / f"{stem}.html"
        markdown_path = text_dir / f"{stem}.md"
        try:
            response = fetch_response(session, url, timeout=timeout, retries=retries, backoff_seconds=backoff_seconds)
            html = response.text
            checksum = sha256_bytes(response.content)
            resolved_url = normalize_url(response.url)
            history = [normalize_url(item.url) for item in response.history]
            body_markdown, metadata = extract_markdown_content(html, response.url)
            frontmatter = {
                "source_url": url,
                "resolved_url": resolved_url,
                "source_host": extract_host(normalize_url(url)),
                "resolved_host": extract_host(resolved_url),
                "capture_timestamp": captured_at,
                "capture_status": "captured",
                "http_status": response.status_code,
                "redirect_chain": history,
                "title": metadata.get("title"),
                "description": metadata.get("description"),
                "canonical_url_meta": metadata.get("canonical_url_meta"),
                "language_hint": metadata.get("language_hint"),
                "content_sha256": checksum,
                "capture_method": "requests_beautifulsoup_markdownify",
            }
            document = build_frontmatter_document(frontmatter, body_markdown)
            old_checksum = html_path.read_bytes() if html_path.exists() else None
            old_checksum_value = sha256_bytes(old_checksum) if old_checksum is not None else None
            if old_checksum_value == checksum and markdown_path.exists():
                capture_status = "unchanged"
            else:
                html_path.write_text(html, encoding="utf-8")
                markdown_path.write_text(document, encoding="utf-8")
                capture_status = "captured"
            results.append(
                {
                    "status": capture_status,
                    "source_url": url,
                    "normalized_source_url": normalize_url(url),
                    "resolved_url": resolved_url,
                    "resolved_host": extract_host(resolved_url),
                    "http_status": response.status_code,
                    "capture_timestamp": captured_at,
                    "redirect_count": len(history),
                    "html_path": str(html_path),
                    "markdown_path": str(markdown_path),
                    "content_sha256": checksum,
                }
            )
        except requests.RequestException as exc:
            results.append(
                {
                    "status": "capture_failed",
                    "source_url": url,
                    "normalized_source_url": normalize_url(url),
                    "capture_timestamp": captured_at,
                    "error": str(exc),
                    "html_path": None,
                    "markdown_path": None,
                }
            )
        if sleep_seconds:
            time.sleep(sleep_seconds)

    merged = [*existing_manifest, *results]
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in reversed(merged):
        key = row.get("normalized_source_url", "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    deduped.reverse()
    from lib.common import write_jsonl

    write_jsonl(manifest_path, deduped)
    return {
        "manifest": results,
        "counts": {
            "requested": len(urls),
            "captured": sum(1 for row in results if row["status"] == "captured"),
            "unchanged": sum(1 for row in results if row["status"] == "unchanged"),
            "skipped_existing": sum(1 for row in results if row["status"] == "skipped_existing"),
            "failed": sum(1 for row in results if row["status"] == "capture_failed"),
        },
    }
