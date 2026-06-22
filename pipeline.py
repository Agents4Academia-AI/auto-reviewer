"""Orchestrate the 10-stage reviewer pipeline.

Each stage receives the structured outputs of relevant prior stages, formatted
as JSON strings interpolated into the prompt. The paper PDF is sent as a cached
document block on every stage.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any, Callable

from llm_client import ReviewerLLM
from prompts import (
    STAGE_0_PARSE,
    STAGE_1_OVERALL,
    STAGE_2_SECTIONS,
    STAGE_3_CLAIMS,
    STAGE_4_NOVELTY,
    STAGE_5_SIGNIFICANCE,
    STAGE_6_RIGOR,
    STAGE_7_PLAN,
    STAGE_8_DRAFT,
    STAGE_9_CRITIQUE,
    STAGE_10_FINAL,
)


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _fill(template: str, **subs: str) -> str:
    """Substitute {stage_N} placeholders without touching the JSON braces in
    the template's schema examples (which would confuse str.format)."""
    result = template
    for key, value in subs.items():
        result = result.replace("{" + key + "}", value)
    return result


def _review_date() -> str:
    return datetime.now(UTC).date().isoformat()


class ReviewerPipeline:
    def __init__(
        self,
        llm: ReviewerLLM,
        paper_document: dict[str, Any],
        logger: Callable[[str], None] | None = None,
    ):
        self.llm = llm
        self.paper_document = paper_document
        self.log = logger or (lambda msg: print(msg, flush=True))
        self.results: dict[str, dict] = {}

    def _run(
        self,
        key: str,
        prompt: str,
        use_web_search: bool = False,
        max_tokens: int | None = None,
    ) -> dict:
        self.log(f"[{key}] running...")
        t0 = time.time()
        result = self.llm.run_stage(
            paper_document=self.paper_document,
            user_prompt=prompt,
            stage_name=key,
            use_web_search=use_web_search,
            max_tokens=max_tokens,
        )
        parsed = result.get("parsed")
        if parsed is None or (isinstance(parsed, dict) and parsed.get("_parse_error")):
            raise ValueError(
                f"{key} did not return valid JSON. "
                "Stopping instead of passing malformed context to later stages."
            )
        if (
            key == "stage_4"
            and use_web_search
            and getattr(self.llm.cfg, "enable_web_search", True)
            and isinstance(parsed, dict)
            and parsed.get("source_of_judgment") != "web_search"
        ):
            raise ValueError(
                "stage_4 was run with web search enabled but did not cite "
                "web_search as source_of_judgment. Stopping so novelty claims "
                "are not based on unverified model knowledge."
            )
        dt = time.time() - t0
        u = result["usage"]
        self.log(
            f"[{key}] done in {dt:.1f}s — "
            f"in={u['input_tokens']} out={u['output_tokens']} "
            f"cache_read={u['cache_read_input_tokens']} cache_write={u['cache_creation_input_tokens']}"
        )
        self.results[key] = result
        return result

    def _parsed(self, key: str) -> Any:
        return self.results[key]["parsed"]

    def run_all(self) -> dict[str, dict]:
        # Stage 0
        self._run("stage_0", STAGE_0_PARSE, max_tokens=self.llm.cfg.max_tokens_long)

        # Stage 1
        self._run(
            "stage_1",
            _fill(STAGE_1_OVERALL, stage_0=_dump(self._parsed("stage_0"))),
        )

        # Stage 2
        self._run(
            "stage_2",
            _fill(STAGE_2_SECTIONS, stage_0=_dump(self._parsed("stage_0"))),
            max_tokens=self.llm.cfg.max_tokens_long,
        )

        # Stage 3
        self._run(
            "stage_3",
            _fill(STAGE_3_CLAIMS, stage_1=_dump(self._parsed("stage_1"))),
        )

        # Stage 4 — web search if enabled
        self._run(
            "stage_4",
            _fill(
                STAGE_4_NOVELTY,
                stage_3=_dump(self._parsed("stage_3")),
                review_date=_review_date(),
            ),
            use_web_search=True,
        )

        # Stage 5
        self._run(
            "stage_5",
            _fill(STAGE_5_SIGNIFICANCE, stage_1=_dump(self._parsed("stage_1"))),
            max_tokens=self.llm.cfg.max_tokens_long,
        )

        # Stage 6
        self._run(
            "stage_6",
            _fill(
                STAGE_6_RIGOR,
                stage_3=_dump(self._parsed("stage_3")),
                stage_2=_dump(self._parsed("stage_2")),
            ),
            max_tokens=self.llm.cfg.max_tokens_long,
        )

        # Stage 7
        self._run(
            "stage_7",
            _fill(
                STAGE_7_PLAN,
                stage_1=_dump(self._parsed("stage_1")),
                stage_3=_dump(self._parsed("stage_3")),
                stage_5=_dump(self._parsed("stage_5")),
                stage_6=_dump(self._parsed("stage_6")),
            ),
        )

        # Stage 8
        self._run(
            "stage_8",
            _fill(
                STAGE_8_DRAFT,
                stage_7=_dump(self._parsed("stage_7")),
                stage_1=_dump(self._parsed("stage_1")),
            ),
        )

        # Stage 9
        self._run(
            "stage_9",
            _fill(STAGE_9_CRITIQUE, stage_8=_dump(self._parsed("stage_8"))),
        )

        # Stage 10
        self._run(
            "stage_10",
            _fill(
                STAGE_10_FINAL,
                stage_8=_dump(self._parsed("stage_8")),
                stage_9=_dump(self._parsed("stage_9")),
            ),
        )

        return self.results

    def total_usage(self) -> dict[str, int]:
        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        for r in self.results.values():
            for k in totals:
                totals[k] += r["usage"].get(k, 0)
        return totals
