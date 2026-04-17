"""Self-contained URL scraper for extracting camp data from web pages.

This module is intentionally standalone — it doesn't import from scripts/lib/
because Vercel serverless functions only deploy the backend directory.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


async def scrape_camp_url(url: str, timeout: float = 8.0) -> dict[str, Any]:
    """Fetch a URL and extract structured camp data.

    Returns a dict matching the ScrapeResult schema.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https")

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CampCrawl/1.0; research-tool)",
        },
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style noise
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    title = _extract_title(soup)
    description = _extract_description(soup)
    text = soup.get_text(separator="\n", strip=True)

    pricing = _extract_pricing(text)
    ages = _extract_ages(text)
    duration = _extract_duration(text)
    contact = _extract_contact(text, html)
    overnight_signals = _extract_overnight_signals(text)
    evidence_snippets = _extract_evidence_snippets(text, overnight_signals)

    return {
        "url": url,
        "title": title,
        "description": description,
        "pricing": pricing,
        "ages": ages,
        "duration": duration,
        "contact": contact,
        "overnight_signals": overnight_signals,
        "evidence_snippets": evidence_snippets,
    }


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return None


def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    for attr in [{"name": "description"}, {"property": "og:description"}]:
        tag = soup.find("meta", attrs=attr)
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


# ---------------------------------------------------------------------------
# Regex extractors
# ---------------------------------------------------------------------------

_PRICE_RE = re.compile(
    r"\$\s?([\d,]+(?:\.\d{2})?)", re.IGNORECASE
)
_AGE_RE = re.compile(
    r"(?:ages?|for)\s+(\d{1,2})\s*[-–to]+\s*(\d{1,2})", re.IGNORECASE
)
_GRADE_RE = re.compile(
    r"(?:grades?)\s+(\d{1,2})\s*[-–to]+\s*(\d{1,2})", re.IGNORECASE
)
_DURATION_RE = re.compile(
    r"(\d{1,3})\s*[-–]?\s*(?:day|night|week)", re.IGNORECASE
)
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
_PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)
_OVERNIGHT_RE = re.compile(
    r"\b(?:overnight|sleepaway|residential|cabin|cabins|dormitory|dorm|bunk|bunks|"
    r"lodge|lodging|sleep-away|boarding|campers\s+stay)\b",
    re.IGNORECASE,
)


def _extract_pricing(text: str) -> Optional[dict]:
    prices = [float(m.replace(",", "")) for m in _PRICE_RE.findall(text)]
    if not prices:
        return None
    return {
        "currency": "USD",
        "min": min(prices),
        "max": max(prices),
    }


def _extract_ages(text: str) -> Optional[dict]:
    result: dict[str, Any] = {}
    age_matches = _AGE_RE.findall(text)
    if age_matches:
        all_ages = [int(a) for pair in age_matches for a in pair]
        result["min"] = min(all_ages)
        result["max"] = max(all_ages)
    grade_matches = _GRADE_RE.findall(text)
    if grade_matches:
        all_grades = [int(g) for pair in grade_matches for g in pair]
        result["grade_min"] = min(all_grades)
        result["grade_max"] = max(all_grades)
    return result or None


def _extract_duration(text: str) -> Optional[dict]:
    matches = _DURATION_RE.findall(text)
    if not matches:
        return None
    days = [int(m) for m in matches]
    # Heuristic: if "week" appears near the number, multiply
    week_re = re.compile(r"(\d{1,2})\s*[-–]?\s*weeks?", re.IGNORECASE)
    week_matches = week_re.findall(text)
    if week_matches:
        for w in week_matches:
            days.append(int(w) * 7)
    return {"min_days": min(days), "max_days": max(days)}


def _extract_contact(text: str, html: str) -> Optional[dict]:
    result: dict[str, Any] = {}
    emails = _EMAIL_RE.findall(text)
    if emails:
        # Filter out common non-contact emails
        filtered = [e for e in emails if not any(
            x in e.lower() for x in ["example.com", "sentry.io", "wixpress", "w3.org"]
        )]
        if filtered:
            result["email"] = filtered[0]
    phones = _PHONE_RE.findall(text)
    if phones:
        result["phone"] = phones[0].strip()
    return result or None


def _extract_overnight_signals(text: str) -> list[str]:
    matches = _OVERNIGHT_RE.findall(text)
    return list(set(m.lower() for m in matches))


def _extract_evidence_snippets(text: str, overnight_signals: list[str]) -> list[str]:
    """Extract relevant sentences that mention pricing, ages, or overnight signals."""
    snippets: list[str] = []
    sentences = re.split(r"[.!?\n]+", text)
    keywords = re.compile(
        r"\$\d|(?:ages?\s+\d)|(?:grades?\s+\d)|(?:overnight|sleepaway|residential|cabin|dormitory)",
        re.IGNORECASE,
    )
    seen = set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15 or len(s) > 500:
            continue
        if keywords.search(s) and s not in seen:
            seen.add(s)
            snippets.append(s)
            if len(snippets) >= 8:
                break
    return snippets
