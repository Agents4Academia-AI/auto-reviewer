"""CLI entry point: review a deep learning paper PDF end-to-end.

Usage:
    python reviewer_agent.py /path/to/paper.pdf
    python reviewer_agent.py /path/to/paper.pdf --out ./reviews
    python reviewer_agent.py /path/to/paper.pdf --no-web-search
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from config import Config
from llm_client import ReviewerLLM
from pdf_parser import load_paper
from pipeline import ReviewerPipeline


def _safe_get(obj, *keys, default=None):
    for k in keys:
        if not isinstance(obj, dict):
            return default
        if k not in obj:
            return default
        obj = obj[k]
    return obj if obj is not None else default


def render_markdown(final_stage_parsed: dict, paper_meta: dict) -> str:
    """Render the Stage 10 final review as a human-readable markdown report."""
    fr = _safe_get(final_stage_parsed, "final_review", default={})
    score = _safe_get(fr, "score_card", default={})

    def _list(label: str, items):
        if not items:
            return ""
        body = "\n".join(f"- {x}" for x in items)
        return f"### {label}\n{body}\n\n"

    lines = []
    lines.append(f"# Reviewer Agent Report\n")
    lines.append(f"**Paper file:** `{paper_meta.get('filename', '')}`  ")
    lines.append(f"**Generated:** {datetime.utcnow().isoformat()}Z\n")
    lines.append("---\n")
    lines.append("## Summary of the Paper\n")
    lines.append((_safe_get(fr, "summary_of_paper", default="(no summary)") or "") + "\n")
    lines.append("## Recommendation\n")
    lines.append(
        f"**{_safe_get(fr, 'overall_recommendation', default='unspecified')}**  "
        f"(confidence {_safe_get(fr, 'reviewer_confidence_1_to_5', default='?')}/5)\n"
    )
    lines.append("### Score Card\n")
    lines.append(
        f"- Soundness: {_safe_get(score, 'soundness_1_to_4', default='?')}/4\n"
        f"- Presentation: {_safe_get(score, 'presentation_1_to_4', default='?')}/4\n"
        f"- Contribution: {_safe_get(score, 'contribution_1_to_4', default='?')}/4\n"
        f"- Overall: {_safe_get(score, 'overall_1_to_10', default='?')}/10\n"
    )
    lines.append(_list("Main Strengths", _safe_get(fr, "main_strengths", default=[])))
    lines.append(_list("Main Weaknesses", _safe_get(fr, "main_weaknesses", default=[])))
    lines.append(_list("Detailed Comments", _safe_get(fr, "detailed_comments", default=[])))
    lines.append(_list("Questions for Authors", _safe_get(fr, "questions_for_authors", default=[])))
    lines.append(_list("Suggestions for Improvement", _safe_get(fr, "suggestions_for_improvement", default=[])))
    lines.append(
        _list(
            "Improvement Checklist",
            _safe_get(final_stage_parsed, "author_facing_improvement_checklist", default=[]),
        )
    )
    return "".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Deep learning paper auto-reviewer agent")
    parser.add_argument("pdf", help="Path to the paper PDF")
    parser.add_argument(
        "--out",
        default="./reviews",
        help="Output directory (default: ./reviews)",
    )
    parser.add_argument(
        "--no-web-search",
        action="store_true",
        help="Disable the web search tool in Stage 4 (novelty check)",
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        default=None,
        help="Override effort level",
    )
    parser.add_argument(
        "--backend",
        choices=["api", "sdk"],
        default=None,
        help="LLM backend: 'api' (ANTHROPIC_API_KEY, default) or 'sdk' "
        "(Claude Agent SDK — uses a Claude subscription, no API key needed)",
    )
    args = parser.parse_args()

    cfg = Config(backend=args.backend or os.getenv("REVIEWER_BACKEND", "api"))
    if args.no_web_search:
        cfg.enable_web_search = False
    if args.effort:
        cfg.effort = args.effort

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading PDF document: {args.pdf}", flush=True)
    paper = load_paper(args.pdf)
    print(f"  loaded {paper['num_bytes']} bytes", flush=True)

    if cfg.backend == "sdk":
        from llm_client_sdk import ReviewerSDKLLM

        llm = ReviewerSDKLLM(cfg, pdf_path=args.pdf)
    else:
        llm = ReviewerLLM(cfg)
    pipeline = ReviewerPipeline(llm=llm, paper_document=paper["document"])

    print(
        f"Running 10-stage pipeline with backend={cfg.backend}, model={cfg.model}, effort={cfg.effort}",
        flush=True,
    )
    results = pipeline.run_all()

    stem = Path(paper["filename"]).stem
    json_path = out_dir / f"{stem}.review.json"
    md_path = out_dir / f"{stem}.review.md"

    # Persist all stage outputs
    serializable = {
        "paper": {
            "filename": paper["filename"],
            "path": paper["path"],
            "num_bytes": paper["num_bytes"],
            "input_mode": "pdf_document",
        },
        "config": {"model": cfg.model, "effort": cfg.effort, "web_search": cfg.enable_web_search},
        "stages": {k: {"parsed": v["parsed"], "usage": v["usage"], "stop_reason": v["stop_reason"]} for k, v in results.items()},
        "total_usage": pipeline.total_usage(),
    }
    json_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2))
    print(f"\nFull JSON written to: {json_path}", flush=True)

    final_parsed = results["stage_10"]["parsed"]
    md = render_markdown(final_parsed, paper)
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


if __name__ == "__main__":
    main()
