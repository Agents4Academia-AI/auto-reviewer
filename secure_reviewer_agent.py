"""Hardened CLI entry point: Phase 0 injection screening + the 10-stage review.

ADDITIVE wrapper around the original reviewer_agent.py. It does NOT modify any
original file. It adds the Master Review Prompt v3 "Phase 0 (Sanitization)"
stage in front of the unchanged ReviewerPipeline.

Usage:
    python secure_reviewer_agent.py /path/to/paper.pdf
    python secure_reviewer_agent.py paper.pdf --phase0-mode sanitize
    python secure_reviewer_agent.py paper.pdf --block-on-injection
    python secure_reviewer_agent.py paper.pdf --no-llm-detector --no-web-search

Run modes (--phase0-mode):
    harden   (default) Detect + quarantine + report, then run the pipeline on
             the ORIGINAL PDF with a security preamble injected into every
             stage. Keeps full PDF fidelity (figures/tables/equations); the
             injected bytes still reach the model but are neutralized by the
             preamble + the detectors' report. This is the only mode that fully
             matches the original code's I/O.
    sanitize Detect + remove flagged spans, then run the pipeline on the
             SANITIZED TEXT (true byte-level removal). The model never sees the
             quarantined content — but also loses page images, so figures /
             tables / equations / layout are NOT available to the review. Best
             for text-only papers or when injection risk dominates.
    off      Skip Phase 0 entirely (equivalent to the original agent, but still
             routed through this wrapper).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from config import Config
from llm_client import ReviewerLLM
from pdf_parser import load_paper
from pipeline import ReviewerPipeline
from reviewer_agent import render_markdown  # reused, unchanged

from hardened_llm import HardenedReviewerLLM, build_text_document_block
from injection_detection import run_phase0, summarize_for_user, severity_at_least


MODE_DESC = {
    "harden": ("detect + quarantine + report, then review the ORIGINAL PDF with "
               "a security preamble on every stage (full PDF fidelity kept; "
               "injected bytes neutralized by the preamble, not removed)."),
    "sanitize": ("detect + REMOVE flagged spans, then review the SANITIZED TEXT "
                 "(true byte-level removal; no page images, so figures/tables/"
                 "equations are NOT available to the review)."),
    "off": "skip Phase 0 entirely (behaves like the original reviewer_agent.py).",
}


def _phase0_markdown(res) -> str:
    if not res.extraction_ok:
        return (
            "\n---\n## Phase 0 — Prompt-Injection Screening\n\n"
            f"> **SKIPPED** — PDF text extraction failed ({res.extraction_error}). "
            "The review ran on the unscreened PDF.\n"
        )
    lines = [
        "\n---\n",
        "## Phase 0 — Prompt-Injection Screening\n",
        f"- Lines scanned: {res.line_count}\n",
        f"- IJ1 (pattern matcher): {len(res.ij1.findings)} raw matches"
        + ("" if res.ij1.ran else " — NOT RUN") + "\n",
        f"- IJ2 (semantic analyzer): {len(res.ij2.findings)} findings"
        + ("" if res.ij2.ran else f" — NOT RUN ({res.ij2.error})") + "\n",
        f"- Segments flagged (merged): {res.num_flagged}\n",
        f"- Segments removed (>= {res.severity_threshold}): {res.num_removed}\n",
        f"- Full audit trail: `{res.workdir}`\n",
    ]
    if res.num_flagged:
        lines.append("\n### Flagged segments (severity >= medium)\n")
        shown = [f for f in res.merged if severity_at_least(f.severity, "medium")]
        if not shown:
            lines.append("_All flags were below medium severity._\n")
        for f in shown[:40]:
            rng = f"L{f.line_start}" if f.line_start == f.line_end else f"L{f.line_start}–L{f.line_end}"
            lines.append(f"- **{f.severity}** {rng} ({f.agent}) — {f.trimmed(140).excerpt}\n")
    else:
        lines.append("\n_No injection patterns detected._\n")
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hardened deep-learning paper auto-reviewer (Phase 0 + pipeline)"
    )
    parser.add_argument("pdf", help="Path to the paper PDF")
    parser.add_argument("--out", default="./reviews", help="Output directory")
    parser.add_argument("--no-web-search", action="store_true",
                        help="Disable web search in Stage 4 (novelty)")
    parser.add_argument("--effort",
                        choices=["low", "medium", "high", "xhigh", "max"],
                        default=None, help="Override effort level")
    parser.add_argument("--phase0-mode", choices=["harden", "sanitize", "off"],
                        default="harden", help="Phase 0 behavior (see module docstring)")
    parser.add_argument("--severity-threshold",
                        choices=["informational", "low", "medium", "high", "critical"],
                        default="low",
                        help="Minimum severity to quarantine/remove (default: low)")
    parser.add_argument("--no-llm-detector", action="store_true",
                        help="Skip IJ2 (run IJ1 pattern matcher only)")
    parser.add_argument("--block-on-injection", action="store_true",
                        help="Abort before the review if any segment >= medium is found")
    args = parser.parse_args()

    cfg = Config()
    if args.no_web_search:
        cfg.enable_web_search = False
    if args.effort:
        cfg.effort = args.effort

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.pdf).stem

    print("=" * 72, flush=True)
    print(f"Hardened auto-reviewer  |  Phase 0 mode: {args.phase0_mode.upper()}", flush=True)
    print(f"  {MODE_DESC[args.phase0_mode]}", flush=True)
    if args.phase0_mode != "off":
        detectors = "IJ1 (pattern, offline)" + (
            "" if args.no_llm_detector else " + IJ2 (semantic, LLM)")
        print(f"  detectors: {detectors}  |  remove >= {args.severity_threshold}"
              + ("  |  block-on-injection" if args.block_on_injection else ""),
              flush=True)
    print("=" * 72, flush=True)

    print(f"Loading PDF document: {args.pdf}", flush=True)
    paper = load_paper(args.pdf)  # original loader, unchanged
    print(f"  loaded {paper['num_bytes']} bytes", flush=True)

    # ---- Phase 0 -----------------------------------------------------------
    phase0_res = None
    paper_document = paper["document"]  # default: original PDF block

    if args.phase0_mode != "off":
        # A plain (non-hardened) client for IJ2 so its detector brief is the
        # sole authority for that call.
        ij2_llm = None
        if not args.no_llm_detector:
            try:
                ij2_llm = ReviewerLLM(cfg)
            except Exception as e:  # noqa: BLE001
                print(f"  [phase0] could not init LLM for IJ2: {e}", flush=True)

        workdir = out_dir / "_phase0" / stem
        phase0_res = run_phase0(
            pdf_path=args.pdf,
            workdir=workdir,
            llm=ij2_llm,
            build_text_document_block=build_text_document_block,
            severity_threshold=args.severity_threshold,
            run_ij2=not args.no_llm_detector,
        )

        print("\n" + summarize_for_user(phase0_res) + "\n", flush=True)

        if not phase0_res.extraction_ok:
            print("*** WARNING: Phase 0 was SKIPPED — could not extract text from "
                  f"the PDF ({phase0_res.extraction_error}).", flush=True)
            print("    The review will run on the UNSCREENED PDF; no injection "
                  "detection was possible.", flush=True)
            if args.block_on_injection:
                print("Aborting: --block-on-injection is set but the paper could "
                      "not be screened (failing closed).", flush=True)
                return 2
            if args.phase0_mode == "sanitize":
                print("    sanitize mode was requested, but with no sanitized "
                      "text it falls back to the original PDF + preamble.",
                      flush=True)
            # paper_document stays the original PDF block.
        else:
            if args.block_on_injection and phase0_res.has_injection:
                print("Aborting: --block-on-injection set and injection(s) "
                      f">= medium detected. See {workdir}", flush=True)
                return 2
            if args.phase0_mode == "sanitize":
                print("  [phase0] mode=sanitize: pipeline will read SANITIZED "
                      "TEXT (no page images — figures/tables/equations "
                      "unavailable).", flush=True)
                paper_document = build_text_document_block(phase0_res.sanitized_text)

    # ---- Review pipeline (UNCHANGED ReviewerPipeline) ----------------------
    if args.phase0_mode == "off":
        llm = ReviewerLLM(cfg)
    else:
        llm = HardenedReviewerLLM(cfg)  # security preamble on every stage

    pipeline = ReviewerPipeline(llm=llm, paper_document=paper_document)
    print(f"Running 10-stage pipeline with model={cfg.model}, effort={cfg.effort}, "
          f"phase0={args.phase0_mode}", flush=True)
    results = pipeline.run_all()

    # ---- Persist outputs ---------------------------------------------------
    json_path = out_dir / f"{stem}.review.json"
    md_path = out_dir / f"{stem}.review.md"

    serializable = {
        "paper": {
            "filename": paper["filename"],
            "path": paper["path"],
            "num_bytes": paper["num_bytes"],
            "input_mode": "sanitized_text" if args.phase0_mode == "sanitize" else "pdf_document",
        },
        "config": {"model": cfg.model, "effort": cfg.effort,
                   "web_search": cfg.enable_web_search},
        "phase0": _phase0_serializable(phase0_res, args) if phase0_res else {"mode": "off"},
        "stages": {k: {"parsed": v["parsed"], "usage": v["usage"],
                       "stop_reason": v["stop_reason"]} for k, v in results.items()},
        "total_usage": pipeline.total_usage(),
    }
    json_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2))
    print(f"\nFull JSON written to: {json_path}", flush=True)

    md = render_markdown(results["stage_10"]["parsed"], paper)
    if phase0_res:
        md += _phase0_markdown(phase0_res)
    md_path.write_text(md)
    print(f"Markdown report written to: {md_path}", flush=True)

    totals = pipeline.total_usage()
    print(
        f"\nTotal token usage — input={totals['input_tokens']} "
        f"output={totals['output_tokens']} "
        f"cache_read={totals['cache_read_input_tokens']} "
        f"cache_write={totals['cache_creation_input_tokens']}",
        flush=True,
    )
    return 0


def _phase0_serializable(res, args) -> dict:
    return {
        "mode": args.phase0_mode,
        "extraction_ok": res.extraction_ok,
        "extraction_error": res.extraction_error,
        "severity_threshold": res.severity_threshold,
        "line_count": res.line_count,
        "ij1_ran": res.ij1.ran,
        "ij2_ran": res.ij2.ran,
        "ij2_error": res.ij2.error,
        "num_flagged": res.num_flagged,
        "num_removed": res.num_removed,
        "has_injection_ge_medium": res.has_injection,
        "workdir": res.workdir,
        "merged_findings": [
            {
                "pattern_class": f.pattern_class,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "severity": f.severity,
                "recommended_action": f.recommended_action,
                "agent": f.agent,
                "excerpt": f.trimmed(160).excerpt,
            }
            for f in res.merged
        ],
    }


if __name__ == "__main__":
    sys.exit(main())
