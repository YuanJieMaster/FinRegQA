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
from .evaluation import (
    EvaluationService,
    get_evaluation_service,
    QAPair,
    MetricsCalculator,
    EvaluationReport,
    EvaluationResult,
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
    # 评估模块
    "EvaluationService",
    "get_evaluation_service",
    "QAPair",
    "MetricsCalculator",
    "EvaluationReport",
    "EvaluationResult",
]
