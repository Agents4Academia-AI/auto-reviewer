"""Thin wrapper around the Anthropic SDK for the reviewer pipeline.

Key design choices:
- Paper content is sent as a cached system block so it stays warm across all 10 stages.
- We use adaptive thinking + `effort` to balance quality and cost.
- JSON-typed stages go through `messages.create` with `output_config.format`.
- Stage 4 (novelty) may use the server-side `web_search_20260209` tool.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from config import Config
from prompts import REVIEWER_SYSTEM


def build_system(paper_text: str) -> list[dict]:
    """System blocks with the paper content cached.

    The paper text is large and identical across stages — perfect prefix for
    prompt caching. Adding cache_control on the last block caches everything
    up to and including the paper.
    """
    return [
        {"type": "text", "text": REVIEWER_SYSTEM},
        {
            "type": "text",
            "text": "Below is the paper under review (raw text extracted from PDF):\n\n"
            + paper_text,
            "cache_control": {"type": "ephemeral"},
        },
    ]


class ReviewerLLM:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = anthropic.Anthropic(api_key=cfg.api_key)

    def run_stage(
        self,
        paper_text: str,
        user_prompt: str,
        stage_name: str,
        use_web_search: bool = False,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run a pipeline stage and return parsed JSON.

        Falls back to raw-text wrapping if the response isn't valid JSON.
        """
        kwargs: dict[str, Any] = {
            "model": model or self.cfg.model,
            "max_tokens": max_tokens or self.cfg.max_tokens_default,
            "system": build_system(paper_text),
            "messages": [{"role": "user", "content": user_prompt}],
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.cfg.effort},
        }

        if use_web_search and self.cfg.enable_web_search:
            kwargs["tools"] = [
                {"type": "web_search_20260209", "name": "web_search", "max_uses": 6}
            ]

        response = self._create_with_retry(**kwargs)
        text = self._extract_text(response)
        parsed = self._parse_json(text)

        return {
            "stage": stage_name,
            "raw_text": text,
            "parsed": parsed,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_creation_input_tokens": getattr(
                    response.usage, "cache_creation_input_tokens", 0
                ),
                "cache_read_input_tokens": getattr(
                    response.usage, "cache_read_input_tokens", 0
                ),
            },
        }

    def _create_with_retry(self, **kwargs) -> Any:
        """Stream the call (SDK requires streaming for large max_tokens) and
        return the accumulated final Message. Single retry on 5xx.
        """
        try:
            with self.client.messages.stream(**kwargs) as stream:
                return stream.get_final_message()
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                with self.client.messages.stream(**kwargs) as stream:
                    return stream.get_final_message()
            raise

    @staticmethod
    def _extract_text(response: Any) -> str:
        parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "\n".join(parts).strip()

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Try to parse JSON; tolerate fenced code blocks and surrounding prose."""
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strip markdown fences if present
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped
            if stripped.endswith("```"):
                stripped = stripped.rsplit("```", 1)[0]
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass

        # Find first { ... last } and try
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {"_parse_error": True, "_raw": text}
