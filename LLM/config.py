"""LLM configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MODEL = "qwen3.5-plus"


@dataclass(frozen=True)
class LLMConfig:
    """Normalized runtime config for LLM calls."""

    provider: str = "qwen"
    model: str = DEFAULT_QWEN_MODEL
    api_key: Optional[str] = None
    base_url: str = DEFAULT_QWEN_BASE_URL
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    timeout: float = 60.0
    max_retries: int = 2
    enable_thinking: bool = False
    cache_enabled: bool = True
    use_cache_on_error: bool = True


def load_llm_config() -> LLMConfig:
    """Load model configuration from environment variables.

    Supported env vars:
    - FINREGQA_LLM_PROVIDER
    - FINREGQA_LLM_MODEL
    - FINREGQA_LLM_API_KEY
    - FINREGQA_LLM_BASE_URL
    - FINREGQA_LLM_TEMPERATURE
    - FINREGQA_LLM_MAX_TOKENS
    - FINREGQA_LLM_TIMEOUT
    - FINREGQA_LLM_MAX_RETRIES
    - FINREGQA_LLM_ENABLE_THINKING
    - FINREGQA_LLM_CACHE_ENABLED
    - FINREGQA_LLM_USE_CACHE_ON_ERROR
    - DASHSCOPE_API_KEY
    - OPENAI_API_KEY
    """

    provider = os.getenv("FINREGQA_LLM_PROVIDER", "qwen").strip().lower()
    model = os.getenv("FINREGQA_LLM_MODEL", DEFAULT_QWEN_MODEL).strip()
    api_key = (
        os.getenv("FINREGQA_LLM_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    base_url = os.getenv("FINREGQA_LLM_BASE_URL", "").strip()

    if not base_url and provider == "qwen":
        base_url = DEFAULT_QWEN_BASE_URL

    max_tokens_raw = os.getenv("FINREGQA_LLM_MAX_TOKENS", "").strip()
    enable_thinking = (
        os.getenv("FINREGQA_LLM_ENABLE_THINKING", "false").strip().lower() == "true"
    )
    cache_enabled = (
        os.getenv("FINREGQA_LLM_CACHE_ENABLED", "true").strip().lower() == "true"
    )
    use_cache_on_error = (
        os.getenv("FINREGQA_LLM_USE_CACHE_ON_ERROR", "true").strip().lower() == "true"
    )

    return LLMConfig(
        provider=provider,
        model=model or DEFAULT_QWEN_MODEL,
        api_key=api_key,
        base_url=base_url or DEFAULT_QWEN_BASE_URL,
        temperature=float(os.getenv("FINREGQA_LLM_TEMPERATURE", "0.1")),
        max_tokens=int(max_tokens_raw) if max_tokens_raw else None,
        timeout=float(os.getenv("FINREGQA_LLM_TIMEOUT", "60")),
        max_retries=int(os.getenv("FINREGQA_LLM_MAX_RETRIES", "2")),
        enable_thinking=enable_thinking,
        cache_enabled=cache_enabled,
        use_cache_on_error=use_cache_on_error,
    )
