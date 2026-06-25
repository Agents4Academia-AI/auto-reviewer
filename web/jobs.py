"""Job store: a SQLite-backed `jobs` table that doubles as the work queue.

Why the DB is the queue: a single atomic `UPDATE ... WHERE status='queued'`
lets any number of worker processes pull work without stepping on each other.
On SQLite that atomicity comes from the write lock; the same query upgrades to
PostgreSQL's `FOR UPDATE SKIP LOCKED` later with no caller changes.

All access goes through SQLAlchemy so swapping SQLite -> Postgres is just a URL.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, create_engine, event, func, select, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from web import settings


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class JobCancelled(Exception):
    """Raised inside the worker when a running job has been asked to cancel."""


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    filename: Mapped[str] = mapped_column(String(512))
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.queued, index=True)
    current_stage: Mapped[str | None] = mapped_column(String(32), default=None)
    use_web_search: Mapped[bool] = mapped_column(default=True)
    # Display name of whoever submitted the review (from the signed auth cookie).
    owner: Mapped[str | None] = mapped_column(String(128), default=None, index=True)
    # When True, the review shows up in everyone's recent list; otherwise only
    # the owner sees it.
    is_public: Mapped[bool] = mapped_column(default=False)
    # Cooperative cancellation flag: the web tier sets it, the worker checks it
    # at each stage boundary and stops.
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    # Liveness signal: stamped when a worker claims the job and at each stage
    # boundary. A `running` job whose heartbeat is stale is treated as orphaned
    # (its worker died) so it can be reclaimed without killing live jobs.
    heartbeat: Mapped[datetime | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(String(2000), default=None)
    recommendation: Mapped[str | None] = mapped_column(String(64), default=None)
    overall_score: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "use_web_search": self.use_web_search,
            "owner": self.owner,
            "is_public": self.is_public,
            "cancel_requested": self.cancel_requested,
            "error": self.error,
            "recommendation": self.recommendation,
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


# SQLite needs check_same_thread=False because the web process and worker
# processes each open their own connection to the same file. `timeout` is the
# busy timeout (seconds): a writer waits for the lock instead of immediately
# raising "database is locked" when another process holds it.
_is_sqlite = settings.DB_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}
_engine = create_engine(settings.DB_URL, connect_args=_connect_args, future=True)


if _is_sqlite:
    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
        """WAL lets readers and a single writer run concurrently (vs. the default
        rollback journal, which locks the whole file on every write) — essential
        once the web tier and multiple workers share one database file."""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()


def init_db() -> None:
    """Create the schema. Safe to call repeatedly (web + worker both call it)."""
    settings.ensure_dirs()
    Base.metadata.create_all(_engine)
    _migrate()


def _migrate() -> None:
    """Tiny additive migration: `create_all` won't add columns to a table that
    already exists, so add columns introduced after the first deploy to
    pre-existing SQLite databases.
    """
    if not settings.DB_URL.startswith("sqlite"):
        return
    with _engine.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(jobs)")}
        if "cancel_requested" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE jobs ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT 0"
            )
        if "owner" not in cols:
            conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN owner VARCHAR(128)")
        if "is_public" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE jobs ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT 0"
            )
        if "heartbeat" not in cols:
            conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN heartbeat DATETIME")


def create_job(
    filename: str,
    use_web_search: bool = True,
    owner: str | None = None,
    is_public: bool = False,
) -> str:
    with Session(_engine) as s:
        job = Job(
            filename=filename,
            use_web_search=use_web_search,
            owner=owner,
            is_public=is_public,
        )
        s.add(job)
        s.commit()
        return job.id


def get_job(job_id: str) -> Job | None:
    with Session(_engine) as s:
        return s.get(Job, job_id)


def _recent(stmt, limit: int) -> list[Job]:
    with Session(_engine) as s:
        rows = s.scalars(stmt.order_by(Job.created_at.desc()).limit(limit)).all()
        # Detach so callers can read attributes after the session closes.
        for r in rows:
            s.expunge(r)
        return list(rows)


def list_owned(owner: str | None, limit: int = 20) -> list[Job]:
    """This user's own recent reviews (public and private)."""
    return _recent(select(Job).where(Job.owner == owner), limit)


def list_public_by_others(owner: str | None, limit: int = 20) -> list[Job]:
    """Recent public reviews submitted by other users."""
    return _recent(
        select(Job).where(Job.is_public.is_(True), Job.owner != owner), limit
    )


def queued_count() -> int:
    with Session(_engine) as s:
        return s.scalar(
            select(func.count()).select_from(Job).where(Job.status == JobStatus.queued)
        ) or 0


def count_by_owner(owner: str | None) -> int:
    """How many reviews this user has against their quota. Failed and cancelled
    runs don't count — only queued/running/done."""
    with Session(_engine) as s:
        return s.scalar(
            select(func.count())
            .select_from(Job)
            .where(
                Job.owner == owner,
                Job.status.not_in([JobStatus.failed, JobStatus.cancelled]),
            )
        ) or 0


def total_count() -> int:
    """Site-wide review count against the global cap. Same rule as
    count_by_owner: queued/running/done count; failed and cancelled don't."""
    with Session(_engine) as s:
        return s.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.status.not_in([JobStatus.failed, JobStatus.cancelled]))
        ) or 0


def claim_next_job() -> Job | None:
    """Atomically claim the oldest queued job, flipping it to `running`.

    The two-statement form (claim by id, then read) keeps this race-safe on
    SQLite, where the UPDATE takes the database write lock so two workers can
    never claim the same row. On Postgres this becomes a single
    `... FOR UPDATE SKIP LOCKED` for true multi-worker concurrency.
    """
    with Session(_engine) as s:
        # Pick the oldest queued id.
        job_id = s.scalar(
            select(Job.id)
            .where(Job.status == JobStatus.queued)
            .order_by(Job.created_at.asc())
            .limit(1)
        )
        if job_id is None:
            return None

        # Flip exactly that row, but only if it's still queued. rowcount tells
        # us whether we won the race against another worker.
        result = s.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.queued)
            .values(status=JobStatus.running, current_stage=None, heartbeat=_now())
        )
        if result.rowcount != 1:
            s.rollback()
            return None
        s.commit()

        job = s.get(Job, job_id)
        if job is not None:
            s.expunge(job)
        return job


def set_stage(job_id: str, stage: str) -> None:
    # Doubles as the liveness heartbeat: each stage boundary proves the worker
    # is still alive, so reset_orphans won't reclaim a slow-but-running job.
    with Session(_engine) as s:
        s.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(current_stage=stage, heartbeat=_now())
        )
        s.commit()


def request_cancel(job_id: str) -> str:
    """Cancel a job. Returns the outcome so the UI can message accordingly.

    A queued job is cancelled outright (the worker never claims it). A running
    job is flagged; the worker notices at the next stage boundary and stops.
    Terminal jobs (done/failed/cancelled) are left untouched.
    """
    with Session(_engine) as s:
        # Queued -> cancel immediately. The WHERE clause makes this race-safe
        # against a worker claiming the row at the same instant.
        if s.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.queued)
            .values(status=JobStatus.cancelled, finished_at=_now())
        ).rowcount == 1:
            s.commit()
            return "cancelled"

        # Running -> ask it to stop cooperatively.
        if s.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.running)
            .values(cancel_requested=True)
        ).rowcount == 1:
            s.commit()
            return "cancelling"

        s.rollback()
        return "noop"


def is_cancel_requested(job_id: str) -> bool:
    with Session(_engine) as s:
        return bool(
            s.scalar(select(Job.cancel_requested).where(Job.id == job_id))
        )


def mark_cancelled(job_id: str) -> None:
    with Session(_engine) as s:
        s.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.cancelled, finished_at=_now())
        )
        s.commit()


def finish_job(job_id: str, recommendation: str | None, overall_score: int | None) -> None:
    with Session(_engine) as s:
        s.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.done,
                recommendation=recommendation,
                overall_score=overall_score,
                finished_at=_now(),
            )
        )
        s.commit()


def fail_job(job_id: str, error: str) -> None:
    with Session(_engine) as s:
        s.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.failed, error=error[:2000], finished_at=_now())
        )
        s.commit()


def reset_orphans() -> None:
    """Reclaim jobs whose worker died mid-run, leaving them stuck in `running`.

    With multiple workers we can't assume every `running` job is dead — another
    worker may be actively processing it. So we only fail jobs whose heartbeat
    is stale (older than ORPHAN_TIMEOUT_SECONDS) or never set. A live worker
    refreshes its heartbeat at every stage boundary, so its job is left alone.
    (Queued jobs are fine — they simply get picked up again.)
    """
    cutoff = _now() - timedelta(seconds=settings.ORPHAN_TIMEOUT_SECONDS)
    with Session(_engine) as s:
        s.execute(
            update(Job)
            .where(
                Job.status == JobStatus.running,
                (Job.heartbeat.is_(None)) | (Job.heartbeat < cutoff),
            )
            .values(
                status=JobStatus.failed,
                error="Worker died while this job was running.",
                finished_at=_now(),
            )
        )
        s.commit()
