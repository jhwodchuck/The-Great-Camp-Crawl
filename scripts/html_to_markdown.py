from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

USER_AGENT = "TheGreatCampCrawl/0.1 (+https://github.com/jhwodchuck/The-Great-Camp-Crawl)"


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def fetch_html(url: str, timeout: int = 30) -> str:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.text


def extract_main_html(html: str) -> tuple[str, dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    description = ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag and desc_tag.get("content"):
        description = desc_tag["content"].strip()

    main = soup.find("main") or soup.find("article")
    if main is None:
        candidates = sorted(
            soup.find_all(["div", "section"], recursive=True),
            key=lambda el: len(el.get_text(" ", strip=True)),
            reverse=True,
        )
        main = candidates[0] if candidates else soup.body or soup

    return str(main), {"title": title, "description": description}


def convert_url_to_markdown(url: str) -> str:
    html = fetch_html(url)
    main_html, meta = extract_main_html(html)
    body_md = md(main_html, heading_style="ATX")
    frontmatter = {
        "source_url": url,
        "source_host": urlparse(url).netloc,
        "title": meta.get("title") or None,
        "description": meta.get("description") or None,
        "capture_method": "requests_beautifulsoup_markdownify",
    }
    lines = ["---"]
    for key, value in frontmatter.items():
        if value is None or value == "":
            lines.append(f"{key}: ")
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
    lines.append("---\n")
    lines.append(body_md.strip())
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a page and convert its main content to Markdown")
    parser.add_argument("url")
    parser.add_argument("--output")
    args = parser.parse_args()

    out_path = Path(args.output) if args.output else Path("data/raw/evidence-pages/text") / f"{slugify(args.url)}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = convert_url_to_markdown(args.url)
    out_path.write_text(markdown, encoding="utf-8")
    print(json.dumps({"output": str(out_path), "url": args.url}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
