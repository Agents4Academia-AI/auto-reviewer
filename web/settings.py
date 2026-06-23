"""Web-app settings, read from environment with sensible defaults.

Kept separate from the pipeline's `config.Config` (which owns the Anthropic
side) so the web layer has one obvious place for its own knobs.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Where runtime data lives. Everything here is gitignored.
DATA_DIR = Path(os.getenv("REVIEWER_DATA_DIR", "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
REVIEW_DIR = DATA_DIR / "reviews"
DB_PATH = DATA_DIR / "jobs.db"
DB_URL = os.getenv("REVIEWER_DB_URL", f"sqlite:///{DB_PATH}")

# Shared-password gate (Phase 6). If unset, auth is disabled (handy in dev).
SITE_PASSWORD = os.getenv("REVIEWER_SITE_PASSWORD", "")
# Secret used to sign the session cookie. Falls back to the password so a
# single env var is enough to get started; set explicitly in production.
SECRET_KEY = os.getenv("REVIEWER_SECRET_KEY", SITE_PASSWORD or "dev-insecure-key")
SESSION_COOKIE = "reviewer_session"

# Upload guardrails — these bound per-review cost and abuse.
MAX_UPLOAD_BYTES = int(os.getenv("REVIEWER_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.getenv("REVIEWER_MAX_PDF_PAGES", "60"))
MAX_QUEUE_DEPTH = int(os.getenv("REVIEWER_MAX_QUEUE_DEPTH", "20"))

# Polling cadence used by the worker loop and surfaced to the frontend.
WORKER_POLL_SECONDS = float(os.getenv("REVIEWER_WORKER_POLL_SECONDS", "2"))


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
