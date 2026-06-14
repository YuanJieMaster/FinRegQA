"""
FinRegQA Services模块
Business logic services
"""
from .knowledge_base import KnowledgeBaseService
from .text_processor import TextSplitterService, clean_financial_text, load_financial_document
from .llm_chunking import (
    LLMChunkingService,
    TextChunk,
    ChunkingResult,
    get_default_llm_chunker,
    chunk_text_with_llm,
    chunk_document_with_llm,
)

__all__ = [
    # 原模块
    "KnowledgeBaseService",
    "TextSplitterService",
    "clean_financial_text",
    "load_financial_document",
    # LLM 分块模块
    "LLMChunkingService",
    "TextChunk",
    "ChunkingResult",
    "get_default_llm_chunker",
    "chunk_text_with_llm",
    "chunk_document_with_llm",
]
