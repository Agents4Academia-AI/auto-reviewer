"""Thin wrapper around the Anthropic SDK for the reviewer pipeline.

Key design choices:
- The paper PDF is sent as a cached document block so it stays warm across all 10 stages.
- We use adaptive thinking + `effort` to balance quality and cost.
- Each stage returns JSON, tolerantly parsed: fenced/prose wrapping is stripped and
  trailing commas are repaired losslessly; a still-unparseable response triggers a
  single bounded retry (resample at the ceiling if truncated, else a stricter-JSON
  reminder) before the caller hard-fails.
- Stage 4 (novelty) may use the server-side `web_search_20260209` tool.
"""

from __future__ import annotations

import json
import os
import re
import random
import time
from typing import Any

import anthropic
import httpx

from config import Config
from prompts import REVIEWER_SYSTEM


def _resolve_ca_bundle() -> str | bool:
    """Pick a CA bundle that trusts the local network's TLS chain.

    Corporate networks often MITM TLS with a self-signed root that lives in the
    OS trust store but not in certifi's bundle (which httpx uses by default).
    Honor the usual env vars first, then fall back to the system bundle.
    """
    for var in ("REVIEWER_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        path = os.getenv(var)
        if path and os.path.isfile(path):
            return path
    for path in ("/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt"):
        if os.path.isfile(path):
            return path
    return True


STRICT_JSON_SUFFIX = (
    "\n\nIMPORTANT: your previous reply could not be parsed as JSON. Reply with "
    "ONLY a single valid JSON object and nothing else — no markdown fences, no "
    "commentary before or after. Inside every string value escape all double "
    'quotes as \\", newlines as \\n, tabs as \\t, and backslashes as \\\\ '
    "(this includes any LaTeX such as \\alpha or \\frac). Do not use trailing "
    "commas or smart/curly quotes."
)


def build_user_content(paper_document: dict[str, Any], user_prompt: str) -> list[dict[str, Any]]:
    """User content with the cached PDF document before the stage prompt.

    Claude's PDF support analyzes extracted text plus page images, preserving
    visual information such as tables, charts, diagrams, equations, and layout.
    """
    return [
        paper_document,
        {"type": "text", "text": user_prompt},
    ]


class ReviewerLLM:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        for var in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
            os.environ.pop(var, None)
        self.client = anthropic.Anthropic(
            api_key=cfg.api_key,
            base_url="https://api.anthropic.com",
            http_client=httpx.Client(verify=_resolve_ca_bundle()),
        )

    def run_stage(
        self,
        paper_document: dict[str, Any],
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
            "system": REVIEWER_SYSTEM,
            "messages": [
                {
                    "role": "user",
                    "content": build_user_content(paper_document, user_prompt),
                }
            ],
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
        retried = False

        if self._is_parse_failure(parsed):
            if response.stop_reason == "max_tokens":
                # Truncated: Resample once at ceiling if not already at ceiling
                ceiling = self.cfg.max_tokens_long
                if kwargs["max_tokens"] < ceiling:
                    retry_kwargs = dict(kwargs, max_tokens=ceiling)
                    response = self._create_with_retry(**retry_kwargs)
                    text = self._extract_text(response)
                    parsed = self._parse_json(text)
                    retried = True
            else:
                # Malformed but complete: one bounded retry, stricter instruction.
                retry_kwargs = self._with_strict_json_instruction(kwargs)
                response = self._create_with_retry(**retry_kwargs)
                text = self._extract_text(response)
                parsed = self._parse_json(text)
                retried = True

        return {
            "stage": stage_name,
            "raw_text": text,
            "parsed": parsed,
            "retried": retried,
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

    @staticmethod
    def _is_parse_failure(parsed: Any) -> bool:
        return parsed is None or (
            isinstance(parsed, dict) and bool(parsed.get("_parse_error"))
        )

    def _with_strict_json_instruction(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Copy of kwargs with a strict-JSON reminder appended to the user prompt.

        Same context, stronger instruction, fresh sample — this is the safe form of
        the one-shot retry (we do NOT feed the broken output back)."""
        rk = dict(kwargs)
        msgs = [dict(m) for m in kwargs["messages"]]
        last = dict(msgs[-1])
        content = [dict(b) if isinstance(b, dict) else b for b in last["content"]]
        for b in reversed(content):
            if isinstance(b, dict) and b.get("type") == "text":
                b["text"] = b["text"] + STRICT_JSON_SUFFIX
                break
        last["content"] = content
        msgs[-1] = last
        rk["messages"] = msgs
        return rk

    _MAX_ATTEMPTS = 6

    def _create_with_retry(self, **kwargs) -> Any:
        """Stream the call (SDK requires streaming for large max_tokens) and
        return the accumulated final Message.

        Retries transient failures with exponential backoff + jitter: 429 rate
        limits (likely once several workers call the API at once), 5xx, and
        connection errors. Honors the server's Retry-After when present. The
        jitter keeps multiple workers from retrying in lockstep.
        """
        for attempt in range(self._MAX_ATTEMPTS):
            try:
                with self.client.messages.stream(**kwargs) as stream:
                    return stream.get_final_message()
            except (
                anthropic.RateLimitError,
                anthropic.APIStatusError,
                anthropic.APIConnectionError,
            ) as e:
                status = getattr(e, "status_code", None)
                retryable = (
                    isinstance(e, (anthropic.RateLimitError, anthropic.APIConnectionError))
                    or (status is not None and status >= 500)
                )
                if not retryable or attempt == self._MAX_ATTEMPTS - 1:
                    raise
                time.sleep(self._retry_delay(e, attempt))

    @staticmethod
    def _retry_delay(exc: Exception, attempt: int) -> float:
        """Seconds to wait before the next attempt. Prefer the server's
        Retry-After header; otherwise exponential backoff (1,2,4,…,60) + jitter."""
        resp = getattr(exc, "response", None)
        if resp is not None:
            retry_after = resp.headers.get("retry-after")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        return min(2 ** attempt, 60) + random.uniform(0, 1)

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
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            # Conservative, lossless repair: drop trailing commas before } or ].
            # (Deliberately NOT touching quotes/backslashes/newlines — those are
            # ambiguous and a bad "fix" silently corrupts content. Let retry handle them.)
            repaired = re.sub(r",(\s*[}\]])", r"\1", candidate)
            if repaired != candidate:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

        return {"_parse_error": True, "_raw": text}
