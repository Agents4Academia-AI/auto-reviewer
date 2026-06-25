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
# Per-user upload cap. Counts a user's reviews that are queued/running/done
MAX_REVIEWS_PER_USER = int(os.getenv("REVIEWER_MAX_REVIEWS_PER_USER", "10"))
# Site-wide cap across all users
MAX_TOTAL_REVIEWS = int(os.getenv("REVIEWER_MAX_TOTAL_REVIEWS", "50"))

# Polling cadence used by the worker loop and surfaced to the frontend.
WORKER_POLL_SECONDS = float(os.getenv("REVIEWER_WORKER_POLL_SECONDS", "2"))

# A running job whose worker hasn't updated its heartbeat within this window is
# treated as orphaned (its worker died) and reset to failed on the next sweep.
# Must be comfortably longer than the slowest single pipeline stage.
ORPHAN_TIMEOUT_SECONDS = int(os.getenv("REVIEWER_ORPHAN_TIMEOUT_SECONDS", "900"))


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
