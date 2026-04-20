"""Unified LLM client for Qwen and compatible providers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

from .cache import build_cache_key, get_cached_response, set_cached_response
from .config import LLMConfig, load_llm_config
from .prompts import (
    ANSWER_SYSTEM_PROMPT,
    RERANK_SYSTEM_PROMPT,
    build_answer_user_prompt,
    build_context_block,
    build_rerank_user_prompt,
)


@dataclass
class LLMResponse:
    """Normalized response object shared across callers."""

    content: str
    model: str
    raw: Any
    usage: Optional[dict[str, Any]] = None
    reasoning_content: Optional[str] = None


@dataclass
class LLMStreamChunk:
    """Structured streaming chunk from the LLM."""

    channel: str
    text: str


def _messages_to_cache_payload(
    messages: Sequence[Mapping[str, str] | Any],
    cfg: LLMConfig,
) -> dict[str, Any]:
    """Serialize request inputs into a stable cache payload."""

    serialized_messages: list[dict[str, str]] = []
    for message in messages:
        if isinstance(message, Mapping):
            serialized_messages.append(
                {
                    "role": str(message.get("role", "user")),
                    "content": str(message.get("content", "")),
                }
            )
            continue

        msg_type = getattr(message, "type", None) or message.__class__.__name__
        serialized_messages.append(
            {
                "role": str(msg_type).lower(),
                "content": str(getattr(message, "content", "")),
            }
        )

    return {
        "model": cfg.model,
        "base_url": cfg.base_url,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "enable_thinking": cfg.enable_thinking,
        "messages": serialized_messages,
    }


def _load_langchain_components() -> tuple[Any, Any, Any, Any, Any]:
    """Import LangChain dependencies only when they are actually needed."""

    try:
        from langchain_core.messages import (
            AIMessage,
            BaseMessage,
            HumanMessage,
            SystemMessage,
        )
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "LLM runtime dependencies are missing. Run `pip install -r requirements.txt` "
            "before invoking model calls."
        ) from exc

    return AIMessage, BaseMessage, HumanMessage, SystemMessage, ChatOpenAI


def get_llm_client(config: Optional[LLMConfig] = None) -> Any:
    """Create a ChatOpenAI client with repo-level defaults."""

    _, _, _, _, ChatOpenAI = _load_langchain_components()
    cfg = config or load_llm_config()
    if not cfg.api_key:
        raise ValueError(
            "Missing LLM API key. Set FINREGQA_LLM_API_KEY or DASHSCOPE_API_KEY."
        )

    kwargs: dict[str, Any] = {
        "model": cfg.model,
        "api_key": cfg.api_key,
        "base_url": cfg.base_url,
        "temperature": cfg.temperature,
        "timeout": cfg.timeout,
        "max_retries": cfg.max_retries,
    }
    if cfg.max_tokens is not None:
        kwargs["max_tokens"] = cfg.max_tokens
    if cfg.enable_thinking:
        kwargs["extra_body"] = {"enable_thinking": True}

    return ChatOpenAI(**kwargs)


def _normalize_messages(messages: Sequence[Mapping[str, str] | Any]) -> list[Any]:
    """Convert dict-based messages to LangChain message objects."""

    AIMessage, BaseMessage, HumanMessage, SystemMessage, _ = _load_langchain_components()

    normalized: list[Any] = []
    for message in messages:
        if isinstance(message, BaseMessage):
            normalized.append(message)
            continue

        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", ""))
        if role == "system":
            normalized.append(SystemMessage(content=content))
        elif role == "assistant":
            normalized.append(AIMessage(content=content))
        else:
            normalized.append(HumanMessage(content=content))
    return normalized


def invoke_chat(
    messages: Sequence[BaseMessage | Mapping[str, str]],
    *,
    config: Optional[LLMConfig] = None,
) -> LLMResponse:
    """Call the configured chat model and return normalized content."""

    cfg = config or load_llm_config()
    cache_key = build_cache_key(_messages_to_cache_payload(messages, cfg))
    client = get_llm_client(cfg)

    try:
        response = client.invoke(_normalize_messages(messages))
    except Exception:
        if cfg.cache_enabled and cfg.use_cache_on_error:
            cached = get_cached_response(cache_key)
            if cached:
                return LLMResponse(
                    content=str(cached.get("content", "")),
                    model=str(cached.get("model", cfg.model)),
                    raw=None,
                    usage=cached.get("usage"),
                    reasoning_content=cached.get("reasoning_content"),
                )
        raise

    usage = None
    reasoning_content = None
    if getattr(response, "response_metadata", None):
        usage = response.response_metadata.get("token_usage")
    if getattr(response, "additional_kwargs", None):
        reasoning_content = response.additional_kwargs.get("reasoning_content")

    result = LLMResponse(
        content=str(response.content),
        model=client.model_name,
        raw=response,
        usage=usage,
        reasoning_content=reasoning_content,
    )
    if cfg.cache_enabled:
        set_cached_response(
            cache_key,
            {
                "content": result.content,
                "model": result.model,
                "usage": result.usage,
                "reasoning_content": result.reasoning_content,
            },
        )
    return result


def _extract_stream_chunks(chunk: Any) -> list[LLMStreamChunk]:
    """Split a provider stream chunk into reasoning and answer events."""

    events: list[LLMStreamChunk] = []

    additional_kwargs = getattr(chunk, "additional_kwargs", {}) or {}
    reasoning = additional_kwargs.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning:
        events.append(LLMStreamChunk(channel="reasoning", text=reasoning))
    elif isinstance(reasoning, list):
        for item in reasoning:
            if isinstance(item, dict) and item.get("text"):
                events.append(
                    LLMStreamChunk(channel="reasoning", text=str(item["text"]))
                )

    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        if content:
            events.append(LLMStreamChunk(channel="answer", text=content))
        return events

    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue

            text = item.get("text")
            if not text:
                continue

            item_type = str(item.get("type", "")).lower()
            channel = "reasoning" if "reason" in item_type else "answer"
            events.append(LLMStreamChunk(channel=channel, text=str(text)))
        return events

    if content:
        events.append(LLMStreamChunk(channel="answer", text=str(content)))

    return events


def stream_chat(
    messages: Sequence[BaseMessage | Mapping[str, str]],
    *,
    config: Optional[LLMConfig] = None,
) -> Iterator[LLMStreamChunk]:
    """Stream reasoning and answer chunks from the configured chat model."""

    cfg = config or load_llm_config()
    cache_key = build_cache_key(_messages_to_cache_payload(messages, cfg))
    client = get_llm_client(cfg)

    reasoning_parts: list[str] = []
    answer_parts: list[str] = []

    try:
        for chunk in client.stream(_normalize_messages(messages)):
            for event in _extract_stream_chunks(chunk):
                if event.channel == "reasoning":
                    reasoning_parts.append(event.text)
                elif event.channel == "answer":
                    answer_parts.append(event.text)
                yield event
    except Exception:
        if cfg.cache_enabled and cfg.use_cache_on_error:
            cached = get_cached_response(cache_key)
            if cached:
                reasoning_text = str(cached.get("reasoning_content") or "")
                answer_text = str(cached.get("content") or "")
                if reasoning_text:
                    yield LLMStreamChunk(channel="reasoning", text=reasoning_text)
                if answer_text:
                    yield LLMStreamChunk(channel="answer", text=answer_text)
                return
        raise

    if cfg.cache_enabled and (reasoning_parts or answer_parts):
        set_cached_response(
            cache_key,
            {
                "content": "".join(answer_parts),
                "model": cfg.model,
                "usage": None,
                "reasoning_content": "".join(reasoning_parts) or None,
            },
        )


def generate_rag_answer(
    question: str,
    references: Iterable[Mapping[str, object]],
    *,
    config: Optional[LLMConfig] = None,
    max_context_chars: int = 800,
) -> LLMResponse:
    """Generate a grounded answer from retrieved knowledge snippets."""

    refs = list(references)
    if not refs:
        return LLMResponse(
            content="未检索到可用参考材料，暂时无法生成基于制度文本的答案。",
            model=(config.model if config else load_llm_config().model),
            raw=None,
            usage=None,
        )

    context_block = build_context_block(refs, max_chars=max_context_chars)
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content": build_answer_user_prompt(question, context_block)},
    ]
    return invoke_chat(messages, config=config)


def stream_rag_answer(
    question: str,
    references: Iterable[Mapping[str, object]],
    *,
    config: Optional[LLMConfig] = None,
    max_context_chars: int = 800,
) -> Iterator[LLMStreamChunk]:
    """Stream reasoning and answer chunks from retrieved knowledge snippets."""

    refs = list(references)
    if not refs:
        yield LLMStreamChunk(
            channel="answer",
            text="未检索到可用参考材料，暂时无法生成基于制度文本的答案。",
        )
        return

    context_block = build_context_block(refs, max_chars=max_context_chars)
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content": build_answer_user_prompt(question, context_block)},
    ]
    yield from stream_chat(messages, config=config)


def rerank_references(
    question: str,
    references: Sequence[Mapping[str, object]],
    *,
    top_k: Optional[int] = None,
    config: Optional[LLMConfig] = None,
    max_context_chars: int = 500,
) -> list[Mapping[str, object]]:
    """Use the LLM to rerank retrieved snippets.

    Falls back to the original order if parsing fails.
    """

    if not references:
        return []

    numbered_refs = []
    for idx, ref in enumerate(references, start=1):
        item = dict(ref)
        item["candidate_id"] = idx
        numbered_refs.append(item)

    context_block = build_context_block(numbered_refs, max_chars=max_context_chars)
    messages = [
        {"role": "system", "content": RERANK_SYSTEM_PROMPT},
        {"role": "user", "content": build_rerank_user_prompt(question, context_block)},
    ]

    try:
        response = invoke_chat(messages, config=config)
        payload = json.loads(response.content)
        ranked_ids = payload.get("ranked_ids") or []
        ranked_map = {idx: ref for idx, ref in enumerate(references, start=1)}
        ranked = [ranked_map[idx] for idx in ranked_ids if idx in ranked_map]

        if len(ranked) < len(references):
            used_ids = set(ranked_ids)
            ranked.extend(
                ref for idx, ref in enumerate(references, start=1) if idx not in used_ids
            )
    except Exception:
        ranked = list(references)

    if top_k is not None:
        return ranked[:top_k]
    return ranked
