"""Claude Agent SDK backend for the reviewer pipeline.

Runs the same 10-stage pipeline through the Claude Agent SDK
(https://github.com/anthropics/claude-agent-sdk-python), so it can use a
Claude subscription (the same login as Claude Code) instead of a metered
ANTHROPIC_API_KEY.

Differences from the API backend (`llm_client.ReviewerLLM`):
- The PDF is read by the agent's Read tool from disk at the start of each
  stage instead of riding along as a cached document block, so there is no
  cross-stage prompt cache. Page images (figures, tables, layout) are still
  seen — Claude Code's Read renders PDF pages visually.
- Stage 4's novelty check uses the agent's WebSearch tool rather than the
  server-side web_search tool.
- Usage numbers come from the SDK's per-turn accounting; costs show as 0 on
  a subscription.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

from config import Config
from llm_client import ReviewerLLM
from prompts import REVIEWER_SYSTEM

_PDF_PREAMBLE = """\
The paper under review is the PDF at: {pdf_path}

Read it (in page chunks if it is long) before answering. Use both the text and
the page-level visual information — figures, tables, equations, layout.

Reply with ONLY the output the task below asks for — no preamble, no notes
about reading the file.

"""


class ReviewerSDKLLM:
    """Drop-in replacement for ReviewerLLM backed by the Claude Agent SDK."""

    def __init__(self, cfg: Config, pdf_path: str | Path):
        self.cfg = cfg
        self.pdf_path = str(Path(pdf_path).resolve())

    def run_stage(
        self,
        paper_document: dict[str, Any],
        user_prompt: str,
        stage_name: str,
        use_web_search: bool = False,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run a pipeline stage and return parsed JSON (same shape as ReviewerLLM)."""
        del paper_document, max_tokens  # PDF comes from disk; output length is the SDK's default
        prompt = _PDF_PREAMBLE.format(pdf_path=self.pdf_path) + user_prompt

        allowed_tools = ["Read"]
        if use_web_search and self.cfg.enable_web_search:
            allowed_tools.append("WebSearch")

        options = ClaudeAgentOptions(
            system_prompt=REVIEWER_SYSTEM,
            model=model or self.cfg.model,
            allowed_tools=allowed_tools,
            disallowed_tools=["Bash", "Edit", "Write", "NotebookEdit", "WebFetch"],
            permission_mode="bypassPermissions",
            extra_args={"effort": self.cfg.effort},
        )

        text, usage = asyncio.run(self._query(prompt, options))
        parsed = ReviewerLLM._parse_json(text)
        if isinstance(parsed, dict) and parsed.get("_parse_error"):
            # One retry with an explicit JSON-only nudge; some models wrap or
            # truncate long JSON on the first attempt.
            retry_prompt = (
                prompt
                + "\n\nIMPORTANT: your entire reply must be a single valid JSON object —"
                " no prose, no markdown fences, nothing before or after it."
            )
            text, retry_usage = asyncio.run(self._query(retry_prompt, options))
            for key in usage:
                usage[key] += retry_usage[key]
            parsed = ReviewerLLM._parse_json(text)

        return {
            "stage": stage_name,
            "raw_text": text,
            "parsed": parsed,
            "stop_reason": "end_turn",
            "usage": usage,
        }

    async def _query(self, prompt: str, options: ClaudeAgentOptions) -> tuple[str, dict[str, int]]:
        parts: list[str] = []
        final: str | None = None
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                parts.extend(b.text for b in message.content if isinstance(b, TextBlock))
            elif isinstance(message, ResultMessage):
                # ResultMessage.result is the complete final reply — prefer it
                # over reassembling assistant messages (long replies can span
                # several, interleaved with tool-use turns).
                if message.result:
                    final = message.result
                if message.usage:
                    for key in usage:
                        usage[key] = int(message.usage.get(key, 0) or 0)
        return (final if final is not None else "\n".join(parts)).strip(), usage
