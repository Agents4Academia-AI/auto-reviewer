#!/usr/bin/env python3
"""Aggregate the batch review run into an accept-vs-reject report.

Reads:  reviews/papers/{accepted,rejected}/*.review.json
Writes: reviews/papers/SUMMARY.md, reviews/papers/SUMMARY.csv

Bucketing rule:
  score_card.overall_1_to_10 >= 6  -> accept   (weak_accept and above)
  score_card.overall_1_to_10 <= 5  -> reject   (includes borderline, weak_reject, ...)

The free-form `overall_recommendation` field is too unreliable to bucket on
(reviewer model returns mixed casing, full sentences, etc.). The numeric
score is the deterministic signal that matches the user-specified cutoff.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEWS = ROOT / "reviews" / "papers"


def _g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d if d is not None else default


# Order matters: longer / more-specific patterns come first so "weak accept"
# is matched before bare "accept".
_REC_PATTERNS = [
    ("strong accept", "strong_accept"),
    ("weak accept", "weak_accept"),
    ("strong reject", "strong_reject"),
    ("weak reject", "weak_reject"),
    ("borderline", "borderline"),
    ("accept", "accept"),
    ("reject", "reject"),
]


def parse_recommendation(text) -> str:
    """Normalize a free-form recommendation string to a canonical label."""
    if not isinstance(text, str):
        return "?"
    head = re.split(r"[.\n;—-]", text.strip().lower(), maxsplit=1)[0]
    head = head.replace("-", " ").replace("_", " ")
    for pat, canon in _REC_PATTERNS:
        if pat in head:
            return canon
    return "?"


def bucket(overall) -> str:
    """overall >= 6 -> accept; otherwise (including missing) -> reject."""
    if isinstance(overall, (int, float)) and overall >= 6:
        return "accept"
    return "reject"


def load_rows(label: str) -> list[dict]:
    rows = []
    in_dir = REVIEWS / label
    if not in_dir.exists():
        return rows
    for jp in sorted(in_dir.glob("*.review.json")):
        data = json.loads(jp.read_text())
        fr = _g(data, "stages", "stage_10", "parsed", "final_review", default={}) or {}
        sc = _g(fr, "score_card", default={}) or {}
        s4 = _g(data, "stages", "stage_4", "parsed", default={}) or {}
        usage = _g(data, "total_usage", default={}) or {}

        rec_raw = fr.get("overall_recommendation", "?")
        rec = parse_recommendation(rec_raw)
        overall = sc.get("overall_1_to_10", "?")
        verdict = bucket(overall)
        truth = "accept" if label == "accepted" else "reject"
        correct = "correct" if verdict == truth else "wrong"

        rows.append(
            {
                "label": label,
                "paper": jp.name.replace(".review.json", ""),
                "recommendation": rec,
                "overall": overall,
                "soundness": sc.get("soundness_1_to_4", "?"),
                "presentation": sc.get("presentation_1_to_4", "?"),
                "contribution": sc.get("contribution_1_to_4", "?"),
                "confidence": fr.get("reviewer_confidence_1_to_5", "?"),
                "novelty": s4.get("novelty_assessment", "?"),
                "verdict": verdict,
                "correct": correct,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_read": usage.get("cache_read_input_tokens", 0),
                "cache_write": usage.get("cache_creation_input_tokens", 0),
            }
        )
    return rows


def _mean(vals) -> str:
    nums = [v for v in vals if isinstance(v, (int, float))]
    if not nums:
        return "?"
    return f"{sum(nums) / len(nums):.2f}"


def main():
    accepted = load_rows("accepted")
    rejected = load_rows("rejected")
    all_rows = accepted + rejected

    out: list[str] = []
    out.append("# Reviewer Benchmark Summary\n\n")
    out.append(f"- Accepted papers reviewed: **{len(accepted)}** / 5\n")
    out.append(f"- Rejected papers reviewed: **{len(rejected)}** / 5\n")
    out.append("- Bucketing: `overall_1_to_10 >= 6` -> accept, otherwise -> reject.\n\n")

    cm = {(gt, pr): 0 for gt in ("accepted", "rejected") for pr in ("accept", "reject")}
    for r in all_rows:
        cm[(r["label"], r["verdict"])] += 1

    out.append("## Confusion matrix\n\n")
    out.append("| ground truth \\ predicted | accept | reject |\n")
    out.append("| --- | --- | --- |\n")
    out.append(
        f"| **accepted** | {cm[('accepted', 'accept')]} | {cm[('accepted', 'reject')]} |\n"
    )
    out.append(
        f"| **rejected** | {cm[('rejected', 'accept')]} | {cm[('rejected', 'reject')]} |\n\n"
    )
    correct_n = cm[("accepted", "accept")] + cm[("rejected", "reject")]
    total = sum(cm.values())
    if total:
        out.append(f"- Accuracy: **{correct_n}/{total}** = {correct_n / total:.0%}\n\n")

    out.append("## Aggregate scores (mean)\n\n")
    out.append("| group | overall/10 | soundness/4 | presentation/4 | contribution/4 | confidence/5 |\n")
    out.append("| --- | --- | --- | --- | --- | --- |\n")
    for name, rows in (("accepted", accepted), ("rejected", rejected)):
        out.append(
            f"| {name} | "
            f"{_mean([r['overall'] for r in rows])} | "
            f"{_mean([r['soundness'] for r in rows])} | "
            f"{_mean([r['presentation'] for r in rows])} | "
            f"{_mean([r['contribution'] for r in rows])} | "
            f"{_mean([r['confidence'] for r in rows])} |\n"
        )
    out.append("\n")

    out.append("## Token usage (sum)\n\n")
    out.append(f"- input: {sum(r['input_tokens'] for r in all_rows):,}\n")
    out.append(f"- output: {sum(r['output_tokens'] for r in all_rows):,}\n")
    out.append(f"- cache_read: {sum(r['cache_read'] for r in all_rows):,}\n")
    out.append(f"- cache_write: {sum(r['cache_write'] for r in all_rows):,}\n")

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
