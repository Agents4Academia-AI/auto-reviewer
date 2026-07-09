import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = os.getenv("REVIEWER_MODEL", "claude-opus-4-7")
    fast_model: str = os.getenv("REVIEWER_FAST_MODEL", "claude-sonnet-4-6")
    backend: str = os.getenv("REVIEWER_BACKEND", "api")  # "api" or "sdk"
    max_tokens_default: int = 16000
    max_tokens_long: int = 32000
    enable_web_search: bool = True
    effort: str = "high"

    def __post_init__(self):
        if self.backend == "api" and not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill it in, "
                "or run with --backend sdk to use a Claude subscription instead."
            )
