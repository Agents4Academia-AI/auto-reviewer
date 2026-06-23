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
def login_submit(request: Request, password: str = Form(...)):
    if auth.password_ok(password):
        resp = RedirectResponse(url="/", status_code=303)
        auth.issue_cookie(resp)
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
    recent = jobs.list_recent(limit=20)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "jobs": [j.as_dict() for j in recent],
            "max_pages": settings.MAX_PDF_PAGES,
            "max_mb": settings.MAX_UPLOAD_BYTES // (1024 * 1024),
        },
    )


@app.get("/review/{job_id}", response_class=HTMLResponse, dependencies=[Depends(auth.require_auth)])
def review_page(request: Request, job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return templates.TemplateResponse(
        request, "review.html", {"job": job.as_dict(), "total_stages": TOTAL_STAGES}
    )


# --- upload ----------------------------------------------------------------

@app.post("/upload", dependencies=[Depends(auth.require_auth)])
async def upload(file: UploadFile, web_search: str | None = Form(default=None)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file.")

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
    job_id = jobs.create_job(filename=file.filename, use_web_search=use_web_search)
    storage.save_upload(job_id, data)
    return RedirectResponse(url=f"/review/{job_id}", status_code=303)


# --- json api (polled by the frontend) -------------------------------------

@app.get("/api/review/{job_id}", dependencies=[Depends(auth.require_auth)])
def api_status(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Review not found")
    d = job.as_dict()
    d["stage_index"] = stage_index(job.current_stage)
    d["total_stages"] = TOTAL_STAGES
    return JSONResponse(d)


@app.post("/api/review/{job_id}/cancel", dependencies=[Depends(auth.require_auth)])
def api_cancel(job_id: str):
    if jobs.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Review not found")
    outcome = jobs.request_cancel(job_id)  # cancelled | cancelling | noop
    return JSONResponse({"outcome": outcome})


@app.get("/api/review/{job_id}/markdown", dependencies=[Depends(auth.require_auth)])
def api_markdown(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if not storage.result_exists(job_id, "md"):
        raise HTTPException(status_code=409, detail="Review not ready yet.")
    return Response(storage.read_result(job_id, "md"), media_type="text/markdown")


@app.get("/health")
def health():
    return {"ok": True}
