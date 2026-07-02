"""FastAPI app: upload a paper, watch progress, read the review.

The web tier is stateless on purpose — it validates + stores the upload, writes
a job row, and returns. All heavy work happens in the separate worker process
(`python -m web.worker`). That separation is what lets this scale later.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader

from web import auth, jobs, settings
from web.progress import TOTAL_STAGES, stage_index
from web.storage import storage

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Paper Reviewer")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _static_v(name: str) -> int:
    """Cache-busting token for a static asset: its file mtime. Appended as a
    query string so browsers refetch the file whenever it changes (otherwise
    they may serve a stale cached copy without revalidating)."""
    try:
        return int((BASE_DIR / "static" / name).stat().st_mtime)
    except OSError:
        return 0


@app.on_event("startup")
def _startup() -> None:
    jobs.init_db()


# --- auth wiring -----------------------------------------------------------

@app.exception_handler(auth._RedirectToLogin)
async def _redirect_login(request: Request, exc: auth._RedirectToLogin):
    return auth.redirect_to_login()


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if not auth.auth_enabled() or auth.is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, name: str = Form(...), password: str = Form(...)):
    name = name.strip()
    if not name:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Please enter your name."}, status_code=400
        )
    if auth.password_ok(password):
        resp = RedirectResponse(url="/", status_code=303)
        auth.issue_cookie(resp, name)
        return resp
    return templates.TemplateResponse(
        request, "login.html", {"error": "Incorrect password."}, status_code=401
    )


@app.post("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    auth.clear_cookie(resp)
    return resp


# --- pages -----------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(auth.require_auth)])
def index(request: Request):
    me = auth.current_user(request)
    my_jobs = jobs.list_owned(owner=me, limit=20)
    public_jobs = jobs.list_public_by_others(owner=me, limit=20)
    used = jobs.count_by_owner(me)
    at_user_limit = used >= settings.MAX_REVIEWS_PER_USER
    site_full = jobs.total_count() >= settings.MAX_TOTAL_REVIEWS
    workers_free = max(0, settings.WORKER_COUNT - jobs.running_count())
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "my_jobs": [j.as_dict() for j in my_jobs],
            "public_jobs": [j.as_dict() for j in public_jobs],
            "me": me,
            "used": used,
            "per_user_limit": settings.MAX_REVIEWS_PER_USER,
            "at_user_limit": at_user_limit,
            "site_full": site_full,
            "upload_disabled": at_user_limit or site_full,
            "max_pages": settings.MAX_PDF_PAGES,
            "max_mb": settings.MAX_UPLOAD_BYTES // (1024 * 1024),
            "workers_free": workers_free,
            "worker_count": settings.WORKER_COUNT,
        },
    )


def _visible_or_404(job_id: str, request: Request) -> jobs.Job:
    """Fetch a job the current user is allowed to see (their own or public),
    else 404. Using 404 (not 403) avoids confirming a private review exists."""
    job = jobs.get_job(job_id)
    me = auth.current_user(request)
    if job is None or not (job.is_public or job.owner == me):
        raise HTTPException(status_code=404, detail="Review not found")
    return job


@app.get("/review/{job_id}", response_class=HTMLResponse, dependencies=[Depends(auth.require_auth)])
def review_page(request: Request, job_id: str):
    job = _visible_or_404(job_id, request)
    is_owner = job.owner == auth.current_user(request)
    return templates.TemplateResponse(
        request,
        "review.html",
        {
            "job": job.as_dict(),
            "total_stages": TOTAL_STAGES,
            "is_owner": is_owner,
            "app_js_v": _static_v("app.js"),
        },
    )


# --- upload ----------------------------------------------------------------

@app.post("/upload", dependencies=[Depends(auth.require_auth)])
async def upload(
    request: Request,
    file: UploadFile,
    web_search: str | None = Form(default=None),
    make_public: str | None = Form(default=None),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file.")

    # Quotas — checked before reading the upload so we fail fast. The site-wide
    # cap is the hard cost backstop; the per-user cap keeps any one person fair.
    if jobs.total_count() >= settings.MAX_TOTAL_REVIEWS:
        raise HTTPException(
            status_code=429,
            detail="This site has reached its total review limit. Please check back later.",
        )
    owner = auth.current_user(request)
    if jobs.count_by_owner(owner) >= settings.MAX_REVIEWS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Upload limit reached — each user can submit up to "
                f"{settings.MAX_REVIEWS_PER_USER} papers."
            ),
        )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (limit {settings.MAX_UPLOAD_BYTES // (1024*1024)} MB).",
        )

    # Page-count guard — bounds per-review token cost.
    try:
        pages = len(PdfReader(io.BytesIO(data)).pages)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read this PDF.")
    if pages > settings.MAX_PDF_PAGES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF has {pages} pages (limit {settings.MAX_PDF_PAGES}).",
        )

    if jobs.queued_count() >= settings.MAX_QUEUE_DEPTH:
        raise HTTPException(
            status_code=429,
            detail="The review queue is full right now. Please try again later.",
        )

    use_web_search = web_search is not None
    job_id = jobs.create_job(
        filename=file.filename,
        use_web_search=use_web_search,
        owner=owner,
        is_public=make_public is not None,
    )
    storage.save_upload(job_id, data)
    return RedirectResponse(url=f"/review/{job_id}", status_code=303)


# --- json api (polled by the frontend) -------------------------------------

@app.get("/api/review/{job_id}", dependencies=[Depends(auth.require_auth)])
def api_status(request: Request, job_id: str):
    job = _visible_or_404(job_id, request)
    d = job.as_dict()
    d["stage_index"] = stage_index(job.current_stage)
    d["total_stages"] = TOTAL_STAGES
    return JSONResponse(d)


@app.post("/api/review/{job_id}/cancel", dependencies=[Depends(auth.require_auth)])
def api_cancel(request: Request, job_id: str):
    job = _visible_or_404(job_id, request)
    # Only the owner may cancel — a public review isn't a shared control surface.
    if job.owner != auth.current_user(request):
        raise HTTPException(status_code=403, detail="Only the owner can cancel this review.")
    outcome = jobs.request_cancel(job_id)  # cancelled | cancelling | noop
    return JSONResponse({"outcome": outcome})


@app.get("/api/review/{job_id}/markdown", dependencies=[Depends(auth.require_auth)])
def api_markdown(request: Request, job_id: str):
    _visible_or_404(job_id, request)
    if not storage.result_exists(job_id, "md"):
        raise HTTPException(status_code=409, detail="Review not ready yet.")
    return Response(storage.read_result(job_id, "md"), media_type="text/markdown")


@app.get("/health")
def health():
    return {"ok": True}
