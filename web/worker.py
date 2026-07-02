"""Background worker: drain the job queue and run the review pipeline.

Run as its own process:  python -m web.worker

It holds no web state — it only talks to the DB (queue + status) and storage
(PDF in, results out). Scaling throughput later = run more of these processes;
on Postgres `claim_next_job` keeps them from colliding.
"""

from __future__ import annotations

import json
import time
from datetime import datetime

from config import Config
from llm_client import ReviewerLLM
from pdf_parser import load_paper
from pipeline import ReviewerPipeline
from reviewer_agent import _safe_get, render_markdown

from web import jobs, settings
from web.progress import make_logger
from web.storage import storage


def _serializable(paper: dict, cfg: Config, results: dict) -> dict:
    """Mirror reviewer_agent.main's on-disk JSON shape for parity with the CLI."""
    return {
        "paper": {
            "filename": paper["filename"],
            "path": paper["path"],
            "num_bytes": paper["num_bytes"],
            "input_mode": "pdf_document",
        },
        "config": {
            "model": cfg.model,
            "effort": cfg.effort,
            "web_search": cfg.enable_web_search,
        },
        "stages": {
            k: {"parsed": v["parsed"], "usage": v["usage"], "stop_reason": v["stop_reason"]}
            for k, v in results.items()
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def run_one(job: jobs.Job) -> None:
    cfg = Config()
    cfg.enable_web_search = bool(job.use_web_search)

    paper = load_paper(storage.upload_path(job.id))
    llm = ReviewerLLM(cfg)
    pipeline = ReviewerPipeline(
        llm=llm,
        paper_document=paper["document"],
        logger=make_logger(job.id),
    )

    results = pipeline.run_all()

    # Persist the full JSON and the rendered markdown report.
    final_parsed = results["stage_10"]["parsed"]
    storage.save_result(job.id, "json", json.dumps(_serializable(paper, cfg, results),
                                                    ensure_ascii=False, indent=2))
    storage.save_result(job.id, "md", render_markdown(final_parsed, paper))

    # Denormalize headline fields for the recent-jobs list view.
    fr = _safe_get(final_parsed, "final_review", default={})
    recommendation = _safe_get(fr, "overall_recommendation", default=None)
    # Ensure recommendation is a string or None for jobs.finish_job typing.
    if recommendation is not None and not isinstance(recommendation, str):
        recommendation = str(recommendation)
    score = _safe_get(fr, "score_card", "overall_1_to_10", default=None)
    score = int(score) if isinstance(score, (int, float)) else None
    jobs.finish_job(job.id, recommendation, score)


def main() -> None:
    jobs.init_db()
    jobs.reset_orphans()
    print("worker: ready, polling for jobs...", flush=True)
    while True:
        job = jobs.claim_next_job()
        if job is None:
            time.sleep(settings.WORKER_POLL_SECONDS)
            continue
        print(f"worker: claimed {job.id} ({job.filename})", flush=True)
        try:
            run_one(job)
            print(f"worker: done {job.id}", flush=True)
        except jobs.JobCancelled:  # user asked to stop
            jobs.mark_cancelled(job.id)
            print(f"worker: cancelled {job.id}", flush=True)
        except Exception as e:  # one bad job must not kill the worker
            jobs.fail_job(job.id, f"{type(e).__name__}: {e}")
            print(f"worker: FAILED {job.id}: {e}", flush=True)


if __name__ == "__main__":
    main()
