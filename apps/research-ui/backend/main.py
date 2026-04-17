"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # noqa: F401 – ensure models are registered before create_all
from routers import auth, missions, contributions, evidence, answers, reviews, export

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="The Great Camp Crawl – Research UI",
    description="Child-friendly camp research collaboration app",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


@app.get("/health")
def health():
    return {"status": "ok"}
