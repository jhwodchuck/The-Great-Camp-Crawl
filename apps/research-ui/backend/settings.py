"""Runtime configuration for the research UI."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = REPO_ROOT / "data" / "staging" / "research_ui.db"
DEFAULT_SECRET = "dev-secret-change-in-production-please"


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _resolve_database_url() -> tuple[str, Path | None]:
    explicit_url = (
        os.environ.get("RESEARCH_UI_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL_NON_POOLING")
        or os.environ.get("POSTGRES_URL")
    )
    if explicit_url:
        return _normalize_database_url(explicit_url), None

    db_path = Path(os.environ.get("RESEARCH_UI_DB", str(DEFAULT_SQLITE_PATH)))
    return f"sqlite:///{db_path}", db_path


DATABASE_URL, SQLITE_DB_PATH = _resolve_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite://")

IS_VERCEL = _env_flag("VERCEL", False) or bool(os.environ.get("VERCEL_ENV"))
IS_PRODUCTION = (
    os.environ.get("VERCEL_ENV") == "production"
    or os.environ.get("ENVIRONMENT") == "production"
    or os.environ.get("NODE_ENV") == "production"
)

RESEARCH_UI_SECRET = os.environ.get("RESEARCH_UI_SECRET", DEFAULT_SECRET)
TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "480"))

RESEARCH_UI_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "RESEARCH_UI_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

RESEARCH_UI_PARENT_INVITE_CODE = os.environ.get("RESEARCH_UI_PARENT_INVITE_CODE", "").strip() or None
RESEARCH_UI_ALLOW_UNINVITED_FIRST_PARENT = _env_flag(
    "RESEARCH_UI_ALLOW_UNINVITED_FIRST_PARENT",
    default=not IS_PRODUCTION,
)
RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME = os.environ.get("RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME", "").strip() or None
RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD = os.environ.get("RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD", "").strip() or None
RESEARCH_UI_BOOTSTRAP_PARENT_DISPLAY_NAME = (
    os.environ.get("RESEARCH_UI_BOOTSTRAP_PARENT_DISPLAY_NAME", "Parent").strip() or "Parent"
)

RESEARCH_UI_ENABLE_FILE_EXPORTS = _env_flag("RESEARCH_UI_ENABLE_FILE_EXPORTS", default=not IS_VERCEL)
RESEARCH_UI_EXPORT_DIR = Path(
    os.environ.get(
        "RESEARCH_UI_EXPORT_DIR",
        str(REPO_ROOT / "data" / "staging" / "contributions"),
    )
)


def validate_runtime_settings() -> None:
    errors: list[str] = []

    if IS_VERCEL and RESEARCH_UI_SECRET == DEFAULT_SECRET:
        errors.append("Set RESEARCH_UI_SECRET before deploying to Vercel.")

    if IS_VERCEL and IS_SQLITE:
        errors.append(
            "SQLite is not durable on Vercel. Set RESEARCH_UI_DATABASE_URL or attach Vercel Postgres."
        )

    bootstrap_username = RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME
    bootstrap_password = RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD
    if bool(bootstrap_username) != bool(bootstrap_password):
        errors.append(
            "Set both RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME and RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD together."
        )

    if (
        IS_VERCEL
        and not RESEARCH_UI_ALLOW_UNINVITED_FIRST_PARENT
        and not RESEARCH_UI_PARENT_INVITE_CODE
        and not (bootstrap_username and bootstrap_password)
    ):
        errors.append(
            "Configure parent access before deploy: either set RESEARCH_UI_PARENT_INVITE_CODE, "
            "enable RESEARCH_UI_ALLOW_UNINVITED_FIRST_PARENT, or provide bootstrap parent credentials."
        )

    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Research UI configuration is incomplete:\n{joined}")
