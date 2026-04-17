"""FastAPI application entry point for local development and Vercel."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import ensure_bootstrap_parent
from database import Base, SessionLocal, engine
import models  # noqa: F401 – ensure models are registered before create_all
from routers import auth, missions, contributions, evidence, answers, reviews, export, camps, favorites, scrape
from settings import (
    RESEARCH_UI_CORS_ALLOW_ORIGIN_REGEX,
    RESEARCH_UI_CORS_ORIGINS,
    validate_runtime_settings,
)

validate_runtime_settings()
Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    ensure_bootstrap_parent(db)

app = FastAPI(
    title="The Great Camp Crawl – Research UI",
    description="Child-friendly camp research collaboration app",
    version="0.1.0",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=RESEARCH_UI_CORS_ORIGINS,
    allow_origin_regex=RESEARCH_UI_CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(missions.router)
app.include_router(contributions.router)
app.include_router(evidence.router)
app.include_router(answers.router)
app.include_router(reviews.router)
app.include_router(export.router)
app.include_router(camps.router)
app.include_router(favorites.router)
app.include_router(scrape.router)


@app.get("/health")
def health():
    return {"status": "ok"}
