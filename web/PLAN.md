# Web App Design — Paper Upload & Review Site

Design notes for the website that wraps the 10-stage reviewer pipeline. Scope:
personal / small-team tool, structured so it can scale later without a rewrite.

## Architecture

```
FastAPI (stateless) ─writes─▶ SQLite (SQLAlchemy) ◀─claims─ worker process
        │                        ▲                                │
LocalStorage(disk) ──────────────┴─────────────  ReviewerPipeline.run_all()
```

Two processes share one SQLite database:

- **Web tier** (`web/app.py`) — validates uploads, stores the PDF, writes a job
  row, returns. Holds no in-memory state.
- **Worker** (`web/worker.py`) — a separate process that claims queued jobs and
  runs the pipeline.

The pipeline itself is unchanged; the worker calls `ReviewerPipeline.run_all()`
and `reviewer_agent.render_markdown()` and passes a `logger` callback for
progress.

## Design principles

1. **Stateless web tier + separate worker process.** The web process only
   reads/writes the DB and enqueues jobs. All long work happens in the worker.
   Scaling = run more web or worker processes, no code change.
2. **DB as the queue.** The `jobs` table is the queue; workers claim work with
   one atomic `UPDATE`. SQLite now → Postgres (`FOR UPDATE SKIP LOCKED`) later →
   Redis only if genuinely needed.
3. **Everything behind a small interface.** DB via SQLAlchemy, blobs via a
   `Storage` class, queue via `claim_next_job()`. Swap the backend, not the
   callers.
4. **Reuse the pipeline untouched.** The worker only adds a `logger` callback.

## Components

| File | Responsibility |
| --- | --- |
| `web/settings.py` | Env-driven config: data paths, password, upload limits, DB URL. |
| `web/jobs.py` | SQLAlchemy `Job` model + job store. `claim_next_job()` is the atomic queue claim. |
| `web/storage.py` | `Storage` protocol + `LocalStorage` (disk) implementation. |
| `web/progress.py` | Parses pipeline log lines (`[stage_6] running...`) into per-job stage updates. |
| `web/worker.py` | Poll loop: claim job → run pipeline → save JSON + markdown → mark done/failed. |
| `web/auth.py` | Shared-password signed-cookie auth (disabled when no password set). |
| `web/app.py` | FastAPI routes: upload, status API, pages, login/logout. |
| `web/templates/` | Jinja2 pages: `index`, `review`, `login`, `base`. |
| `web/static/` | `app.js` (status polling + client-side markdown render), `style.css`. |

## Data model — `jobs` table

| column | purpose |
| --- | --- |
| `id` | uuid hex, primary key, also the storage filename stem |
| `filename` | original PDF name |
| `status` | `queued` / `running` / `done` / `failed` |
| `current_stage` | e.g. `stage_6`, set by the progress hook |
| `use_web_search` | per-job toggle for the Stage 4 novelty search |
| `error` | message when failed |
| `recommendation`, `overall_score` | denormalized from Stage 10 for the list view |
| `created_at`, `finished_at` | timestamps |

Result blobs live on disk keyed by `id` (`data/reviews/<id>.json` / `.md`); the
uploaded PDF is `data/uploads/<id>.pdf`. The DB stays small.

## Request flow

1. `POST /upload` — validate extension, size, and page count (`pypdf`); enforce
   the queue-depth cap; store the PDF; insert a `queued` job; redirect to
   `/review/{id}`.
2. Worker `claim_next_job()` flips the row to `running`, runs the pipeline, and
   writes the JSON + markdown results, then `finish_job()` (or `fail_job()`).
3. Frontend polls `GET /api/review/{id}` every ~3s for status + stage, then
   fetches `GET /api/review/{id}/markdown` once `done` and renders it.

On worker startup, `reset_orphans()` marks any job left `running` (from a crash)
as failed.

## Safety limits

- Max upload size and max page count — bound per-review cost.
- Queue-depth cap — reject new uploads past N pending.
- API key stays server-side (`config.py`).
- Per-job `--no-web-search` equivalent exposed as a checkbox.

All configurable via env vars (see README Configuration table).

## Scaling path (no caller changes)

- SQLite → Postgres: set `REVIEWER_DB_URL`; `claim_next_job` becomes
  `... FOR UPDATE SKIP LOCKED` for multi-worker concurrency.
- `LocalStorage` → S3: add an `S3Storage` with the same four methods, swap the
  `storage` instance.
- 1 worker → N workers: run more `python -m web.worker` processes.
- Shared password → real accounts: replace `web/auth.py`.

## Deliberately out of scope

Real accounts/OAuth, Redis/Celery, Docker/k8s, autoscaling, metrics dashboards,
WebSockets (polling is sufficient; SSE/WS is a drop-in upgrade later).
