"""Bridge the pipeline's log lines into per-job progress in the DB.

`ReviewerPipeline` takes a `logger(msg)` callback and emits lines like
`[stage_6] running...`. We parse the stage token out of those lines and write
it to the job row, so the frontend can show "Stage 6 of 10" live. The pipeline
itself stays unchanged — we only hand it this callback.
"""

from __future__ import annotations

import re
from typing import Callable

from web import jobs

_STAGE_RE = re.compile(r"\[(stage_\d+)\]")

# Order matters for the progress bar; index + 1 = "stage N of TOTAL".
STAGE_ORDER = [f"stage_{i}" for i in range(11)]
TOTAL_STAGES = len(STAGE_ORDER)


def make_logger(job_id: str) -> Callable[[str], None]:
    def logger(msg: str) -> None:
        # Always echo to stdout so the worker's terminal still shows progress.
        print(f"[{job_id[:8]}] {msg}", flush=True)
        m = _STAGE_RE.search(msg)
        if m and "running" in msg:
            # Stage boundary: this is our cooperative cancellation checkpoint.
            # Raising here unwinds out of pipeline.run_all() before the next
            # (expensive) stage starts.
            if jobs.is_cancel_requested(job_id):
                raise jobs.JobCancelled()
            jobs.set_stage(job_id, m.group(1))

    return logger


def stage_index(stage: str | None) -> int:
    """1-based position of a stage for display; 0 if unknown/not started."""
    if stage in STAGE_ORDER:
        return STAGE_ORDER.index(stage) + 1
    return 0
