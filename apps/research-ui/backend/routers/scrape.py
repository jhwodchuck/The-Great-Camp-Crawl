"""Scrape endpoint — fetch a URL and extract structured camp data."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from models import User
from schemas import ScrapeRequest, ScrapeResult
from scraper import scrape_camp_url

router = APIRouter(prefix="/api/scrape", tags=["scrape"])

# Simple in-memory rate limiter: user_id -> list of timestamps
_rate_window: dict[int, list[float]] = defaultdict(list)
_RATE_LIMIT = 10  # requests
_RATE_PERIOD = 60  # seconds


def _check_rate_limit(user_id: int) -> None:
    now = time.time()
    window = _rate_window[user_id]
    # Prune old entries
    _rate_window[user_id] = [t for t in window if now - t < _RATE_PERIOD]
    if len(_rate_window[user_id]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {_RATE_LIMIT} scrape requests per minute.",
        )
    _rate_window[user_id].append(now)


@router.post("/", response_model=ScrapeResult)
async def scrape_url(
    payload: ScrapeRequest,
    user: User = Depends(get_current_user),
):
    """Fetch a URL and return extracted camp data (not persisted)."""
    _check_rate_limit(user.id)
    try:
        result = await scrape_camp_url(payload.url)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to scrape URL: {exc}",
        )
    return ScrapeResult(**result)
