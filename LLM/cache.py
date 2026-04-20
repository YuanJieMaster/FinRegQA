"""Small file-based cache for LLM responses."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional


_CACHE_PATH = Path(__file__).resolve().parent / "llm_cache.json"


def _load_cache() -> dict[str, Any]:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    _CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_cache_key(payload: Any) -> str:
    """Create a stable cache key for a request payload."""

    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_response(key: str) -> Optional[dict[str, Any]]:
    """Load a cached response payload by key."""

    return _load_cache().get(key)


def set_cached_response(key: str, value: dict[str, Any]) -> None:
    """Persist a response payload by key."""

    cache = _load_cache()
    cache[key] = value
    _save_cache(cache)
