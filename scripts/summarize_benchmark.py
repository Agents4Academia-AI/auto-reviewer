#!/usr/bin/env python3
"""Aggregate the batch review run into an accept-vs-reject report.

Reads:  reviews/papers/{accepted,rejected}/*.review.json
Writes: reviews/papers/SUMMARY.md, reviews/papers/SUMMARY.csv
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEWS = ROOT / "reviews" / "papers"

ACCEPT_RECS = {"strong_accept", "accept", "weak_accept"}
REJECT_RECS = {"weak_reject", "reject", "strong_reject"}


def _g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d if d is not None else default


def _bucket(rec: str) -> str:
    if rec in ACCEPT_RECS:
        return "accept"
    if rec in REJECT_RECS:
        return "reject"
    return "borderline"


def load_rows(label: str) -> list[dict]:
    rows = []
    in_dir = REVIEWS / label
    if not in_dir.exists():
        return rows
    for jp in sorted(in_dir.glob("*.review.json")):
        data = json.loads(jp.read_text())
        fr = _g(data, "stages", "stage_10", "parsed", "final_review", default={})
        s4 = _g(data, "stages", "stage_4", "parsed", default={})
        usage = _g(data, "total_usage", default={})
        rec = _g(fr, "overall_recommendation", default="?")
        verdict = _bucket(rec)
        if verdict == label:
            correct = "correct"
        elif verdict == "borderline":
            correct = "borderline"
        else:
            correct = "wrong"
        rows.append(
            {
                "label": label,
                "paper": jp.name.replace(".review.json", ""),
                "recommendation": rec,
                "verdict": verdict,
                "correct": correct,
                "soundness": _g(fr, "score_card", "soundness_1_to_4", default="?"),
                "presentation": _g(fr, "score_card", "presentation_1_to_4", default="?"),
                "contribution": _g(fr, "score_card", "contribution_1_to_4", default="?"),
                "overall": _g(fr, "score_card", "overall_1_to_10", default="?"),
                "confidence": _g(fr, "reviewer_confidence_1_to_5", default="?"),
                "novelty": _g(s4, "novelty_assessment", default="?"),
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_read": usage.get("cache_read_input_tokens", 0),
                "cache_write": usage.get("cache_creation_input_tokens", 0),
            }
        )
    return rows


def _mean(vals) -> str:
    nums = [v for v in vals if isinstance(v, (int, float))]
    return f"{sum(nums) / len(nums):.2f}" if nums else "?"


def _table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "_(no reviews found)_\n\n"
    head = "| " + " | ".join(cols) + " |\n"
    sep = "| " + " | ".join("---" for _ in cols) + " |\n"
    body = "".join("| " + " | ".join(str(r[c]) for c in cols) + " |\n" for r in rows)
    return head + sep + body + "\n"


def main():
    accepted = load_rows("accepted")
    rejected = load_rows("rejected")
    all_rows = accepted + rejected

    out: list[str] = []
    out.append("# Reviewer Benchmark Summary\n\n")
    out.append(f"- Accepted papers reviewed: **{len(accepted)}** / 5\n")
    out.append(f"- Rejected papers reviewed: **{len(rejected)}** / 5\n\n")

    cm = {(gt, pr): 0 for gt in ("accepted", "rejected") for pr in ("accept", "borderline", "reject")}
    for r in all_rows:
        cm[(r["label"], r["verdict"])] += 1

    out.append("## Confusion matrix\n\n")
    out.append("Ground truth (rows) vs reviewer verdict (cols).\n\n")
    out.append("| ground truth \\ predicted | accept | borderline | reject |\n")
    out.append("| --- | --- | --- | --- |\n")
    out.append(
        f"| **accepted** | {cm[('accepted', 'accept')]} | "
        f"{cm[('accepted', 'borderline')]} | {cm[('accepted', 'reject')]} |\n"
    )
    out.append(
        f"| **rejected** | {cm[('rejected', 'accept')]} | "
        f"{cm[('rejected', 'borderline')]} | {cm[('rejected', 'reject')]} |\n\n"
    )

    correct = cm[("accepted", "accept")] + cm[("rejected", "reject")]
    wrong = cm[("accepted", "reject")] + cm[("rejected", "accept")]
    borderline = cm[("accepted", "borderline")] + cm[("rejected", "borderline")]
    total = correct + wrong + borderline
    if total:
        out.append(
            f"- Strict accuracy (excludes borderline): "
            f"**{correct}/{correct + wrong}** "
            f"= {correct / max(correct + wrong, 1):.0%}\n"
        )
        out.append(f"- Borderline calls: {borderline}/{total}\n\n")

    out.append("## Aggregate scores (mean)\n\n")
    out.append("| group | overall/10 | soundness/4 | presentation/4 | contribution/4 | confidence/5 |\n")
    out.append("| --- | --- | --- | --- | --- | --- |\n")
    for name, rows in (("accepted", accepted), ("rejected", rejected)):
        out.append(
            f"| {name} | {_mean([r['overall'] for r in rows])} | "
            f"{_mean([r['soundness'] for r in rows])} | "
            f"{_mean([r['presentation'] for r in rows])} | "
            f"{_mean([r['contribution'] for r in rows])} | "
            f"{_mean([r['confidence'] for r in rows])} |\n"
        )
    out.append("\n")

    cols = [
        "paper",
        "recommendation",
        "correct",
        "overall",
        "soundness",
        "presentation",
        "contribution",
        "confidence",
        "novelty",
    ]
    out.append("## Accepted papers (ground truth)\n\n")
    out.append(_table(accepted, cols))
    out.append("## Rejected papers (ground truth)\n\n")
    out.append(_table(rejected, cols))

    total_in = sum(r["input_tokens"] for r in all_rows)
    total_out = sum(r["output_tokens"] for r in all_rows)
    total_cr = sum(r["cache_read"] for r in all_rows)
    total_cw = sum(r["cache_write"] for r in all_rows)
    out.append("## Token usage (sum)\n\n")
    out.append(f"- input: {total_in:,}\n")
    out.append(f"- output: {total_out:,}\n")
    out.append(f"- cache_read: {total_cr:,}\n")
    out.append(f"- cache_write: {total_cw:,}\n")

    REVIEWS.mkdir(parents=True, exist_ok=True)
    md_path = REVIEWS / "SUMMARY.md"
    md_path.write_text("".join(out))
    print("".join(out))
    print(f"\nWritten: {md_path}")

    if all_rows:
        csv_path = REVIEWS / "SUMMARY.csv"
        with csv_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        print(f"Written: {csv_path}")


if __name__ == "__main__":
    main()
