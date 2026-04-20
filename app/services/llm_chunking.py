"""
FinRegQA LLM 智能分块服务
LLM-powered Text Chunking Service

使用 LLM 识别金融法规文档的语义边界，生成高质量的文本块。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, List, Mapping, Optional, Sequence

from app.services.text_processor import (
    clean_financial_text,
    load_financial_document,
)
from LLM.cache import build_cache_key, get_cached_response, set_cached_response
from LLM.client import LLMConfig, load_llm_config
from LLM.prompts import build_context_block


# ============================================================================
# Prompt Templates
# ============================================================================

CHUNKING_SYSTEM_PROMPT = """你是一名金融监管文档结构化分析专家。

你的任务是：
1. 分析输入文本的语义结构
2. 识别语义完整的法规条款或段落
3. 提取每个分块的元数据（条款号、章节、款号等）

重要规则：
- 每块内容必须是语义完整的最小单元，不能截断完整的法规表述
- 保持"第X条"作为独立块的开始
- 如果某条内容过长（超过1000字），可以拆分为多个子块
- 提取的元数据要准确，特别是条款编号
- 忽略页眉页脚、水印、内部资料标识等干扰信息
"""


def build_chunking_user_prompt(text: str, min_chunk_size: int = 50, max_chunk_size: int = 800) -> str:
    """构建分块任务的用户提示"""
    return f"""请分析以下金融监管文档，将其分割成语义完整的块。

要求：
- 每个块必须是语义完整的最小单元
- 最小块大小：{min_chunk_size} 字符
- 最大块大小：{max_chunk_size} 字符（超过时拆分）
- 保持条款编号的完整性

文档内容：
---
{text}
---

请返回 JSON 格式结果：
{{
    "chunks": [
        {{
            "content": "块的实际内容",
            "article_number": "第一条"（如果识别到）,
            "section_number": "第一款"（如果识别到）,
            "chapter": "第一章"（如果识别到）,
            "reason": "分块理由简述"
        }}
    ],
    "total_chars": 总字符数,
    "chunk_count": 分块数量,
    "summary": "整体结构概述"
}}
"""


def build_contextual_chunking_prompt(
    text: str,
    document_name: str = "",
    category: str = "",
    region: str = "",
    max_chunk_chars: int = 600,
) -> str:
    """构建上下文增强的分块提示（适用于已有标题/结构的文档）"""
    context_parts = []
    if document_name:
        context_parts.append(f"文档名称：{document_name}")
    if category:
        context_parts.append(f"文档类别：{category}")
    if region:
        context_parts.append(f"适用地区：{region}")

    context_text = "\n".join(context_parts) if context_parts else "未提供文档元数据"

    return f"""你是一名金融监管文档分块专家。请根据文档结构和语义将文本分割成高质量的块。

【文档上下文】
{context_text}

【分块规则】
1. 每块包含语义完整的法规内容
2. 优先在以下位置分割：
   - "第X条"（条款级别）
   - "第X款"（款项级别，如果款的内容独立完整）
   - 段落之间（空行处）
3. 块大小控制在 {max_chunk_chars} 字符以内
4. 如果某条内容过长（>800字），在自然子句处拆分
5. 保留关键结构标识（第X条、第X款等）

【待处理文本】
---
{text}
---

返回格式（严格 JSON）：
{{
    "chunks": [
        {{
            "content": "块内容（保留完整条款表述）",
            "article_number": "第一条"（无则填 null）,
            "section_number": "第一款"（无则填 null）,
            "metadata": {{
                "is_first_article": true/false,
                "has_sub_clauses": true/false,
                "estimated_importance": "high/medium/low"
            }}
        }}
    ],
    "structure_summary": "文档整体结构描述",
    "recommendations": ["建议1", "建议2"]
}}
"""


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ChunkMetadata:
    """分块元数据"""
    article_number: Optional[str] = None
    section_number: Optional[str] = None
    chapter: Optional[str] = None
    is_first_article: bool = False
    has_sub_clauses: bool = False
    estimated_importance: str = "medium"
    reason: str = ""


@dataclass
class TextChunk:
    """文本块"""
    content: str
    metadata: ChunkMetadata
    index: int = 0
    char_count: int = field(default=0)

    def __post_init__(self):
        if self.char_count == 0:
            self.char_count = len(self.content)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式（用于知识库）"""
        return {
            "content": self.content,
            "article_number": self.metadata.article_number,
            "section_number": self.metadata.section_number,
            "chapter": self.metadata.chapter,
        }


@dataclass
class ChunkingResult:
    """分块结果"""
    chunks: List[TextChunk]
    total_chars: int
    total_chunks: int
    structure_summary: str = ""
    raw_llm_response: Optional[str] = None

    def to_knowledge_items(self) -> List[dict[str, Any]]:
        """转换为知识库导入格式"""
        return [chunk.to_dict() for chunk in self.chunks]


# ============================================================================
# LLM Chunking Service
# ============================================================================

class LLMChunkingService:
    """基于 LLM 的智能分块服务"""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        min_chunk_size: int = 50,
        max_chunk_size: int = 800,
        enable_cache: bool = True,
    ):
        """
        初始化 LLM 分块服务

        Args:
            config: LLM 配置（不传则使用默认配置）
            min_chunk_size: 最小块大小（字符数）
            max_chunk_size: 最大块大小（字符数）
            enable_cache: 是否启用缓存
        """
        self.config = config or load_llm_config()
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.enable_cache = enable_cache

        # 备用规则分块器
        # self._fallback_splitter = _FallbackTextSplitter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        *,
        document_name: str = "",
        category: str = "",
        region: str = "",
    ) -> ChunkingResult:
        """
        将文本分块

        Args:
            text: 原始文本
            document_name: 文档名称（可选，用于上下文增强）
            category: 文档类别
            region: 适用地区

        Returns:
            ChunkingResult: 分块结果
        """
        cleaned_text = clean_financial_text(text)

        # 尝试缓存
        if self.enable_cache:
            cache_key = self._build_cache_key(cleaned_text, document_name, category, region)
            cached = get_cached_response(cache_key)
            if cached:
                return self._cached_to_result(cached)

        # 调用 LLM 分块
        try:
            result = self._chunk_with_llm(
                cleaned_text,
                document_name=document_name,
                category=category,
                region=region,
            )
        except Exception as e:
            # LLM 失败时回退到规则分块
            result = self._chunk_with_fallback(cleaned_text)

        # 缓存结果
        if self.enable_cache:
            set_cached_response(cache_key, self._result_to_cache(result))

        return result

    def chunk_document(
        self,
        file_path: str,
        *,
        category: str = "",
        region: str = "",
    ) -> ChunkingResult:
        """
        将文档文件分块

        Args:
            file_path: 文档路径（支持 .pdf, .docx, .txt）
            category: 文档类别
            region: 适用地区

        Returns:
            ChunkingResult: 分块结果
        """
        doc = load_financial_document(file_path, clean_text=True)
        document_name = doc.metadata.get("file_name", "")

        return self.chunk_text(
            doc.page_content,
            document_name=document_name,
            category=category,
            region=region,
        )

    def stream_chunk_text(
        self,
        text: str,
        *,
        document_name: str = "",
        category: str = "",
        region: str = "",
    ) -> Iterator[TextChunk]:
        """
        流式返回分块（边生成边返回）

        Yields:
            TextChunk: 文本块
        """
        cleaned_text = clean_financial_text(text)
        total_chars = len(cleaned_text)

        # 如果文本较短，直接返回整块
        if total_chars <= self.max_chunk_size:
            yield TextChunk(
                content=cleaned_text,
                metadata=ChunkMetadata(reason="文本较短，整块返回"),
                index=0,
                char_count=total_chars,
            )
            return

        # 文本较长时，分段处理
        segments = self._split_into_segments(cleaned_text, segment_size=3000)

        for seg_idx, segment in enumerate(segments):
            if len(segment) <= self.max_chunk_size:
                yield TextChunk(
                    content=segment,
                    metadata=ChunkMetadata(reason=f"段落 {seg_idx + 1}，直接返回"),
                    index=seg_idx,
                    char_count=len(segment),
                )
            else:
                # 逐块生成
                sub_chunks = self._chunk_with_llm(segment)
                for chunk in sub_chunks.chunks:
                    chunk.index = seg_idx
                    yield chunk

    # ------------------------------------------------------------------
    # Private Methods
    # ------------------------------------------------------------------

    def _chunk_with_llm(
        self,
        text: str,
        *,
        document_name: str = "",
        category: str = "",
        region: str = "",
    ) -> ChunkingResult:
        """使用 LLM 进行分块"""
        from LLM.client import invoke_chat

        # 动态选择提示模板
        if document_name or category:
            user_prompt = build_contextual_chunking_prompt(
                text,
                document_name=document_name,
                category=category,
                region=region,
                max_chunk_chars=self.max_chunk_size,
            )
        else:
            user_prompt = build_chunking_user_prompt(
                text,
                min_chunk_size=self.min_chunk_size,
                max_chunk_size=self.max_chunk_size,
            )

        messages = [
            {"role": "system", "content": CHUNKING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = invoke_chat(messages, config=self.config)
        return self._parse_llm_response(response.content, text)

    def _chunk_with_fallback(self, text: str) -> ChunkingResult:
        """回退到规则分块"""
        chunks = self._fallback_splitter.split_text(text)

        text_chunks = []
        for idx, chunk_content in enumerate(chunks):
            article_num, section_num, chapter = self._fallback_splitter.extract_metadata(chunk_content)
            text_chunks.append(
                TextChunk(
                    content=chunk_content,
                    metadata=ChunkMetadata(
                        article_number=article_num,
                        section_number=section_num,
                        chapter=chapter,
                        reason="规则分块回退",
                    ),
                    index=idx,
                    char_count=len(chunk_content),
                )
            )

        return ChunkingResult(
            chunks=text_chunks,
            total_chars=len(text),
            total_chunks=len(text_chunks),
            structure_summary="使用规则分块器生成",
        )

    def _parse_llm_response(self, llm_output: str, original_text: str) -> ChunkingResult:
        """解析 LLM 响应"""
        try:
            # 提取 JSON（处理可能的 markdown 代码块）
            json_str = llm_output.strip()
            if json_str.startswith("```"):
                json_str = re.sub(r"```(?:json)?\s*", "", json_str)
                json_str = re.sub(r"\s*```$", "", json_str)
            json_str = json_str.strip()

            data = json.loads(json_str)
            chunks_data = data.get("chunks", [])

            text_chunks = []
            for idx, chunk_data in enumerate(chunks_data):
                content = str(chunk_data.get("content", "")).strip()
                if len(content) < self.min_chunk_size:
                    continue

                meta_data = chunk_data.get("metadata", {}) or {}
                text_chunks.append(
                    TextChunk(
                        content=content,
                        metadata=ChunkMetadata(
                            article_number=chunk_data.get("article_number"),
                            section_number=chunk_data.get("section_number"),
                            chapter=chunk_data.get("chapter"),
                            is_first_article=meta_data.get("is_first_article", False),
                            has_sub_clauses=meta_data.get("has_sub_clauses", False),
                            estimated_importance=meta_data.get("estimated_importance", "medium"),
                            reason=chunk_data.get("reason", ""),
                        ),
                        index=idx,
                        char_count=len(content),
                    )
                )

            return ChunkingResult(
                chunks=text_chunks,
                total_chars=data.get("total_chars", len(original_text)),
                total_chunks=data.get("chunk_count", len(text_chunks)),
                structure_summary=data.get("structure_summary", "") or data.get("summary", ""),
                raw_llm_response=llm_output,
            )

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 响应 JSON 解析失败: {e}") from e

    def _split_into_segments(self, text: str, segment_size: int = 3000) -> List[str]:
        """将长文本分割成段（减少 LLM 处理压力）"""
        segments = []
        for i in range(0, len(text), segment_size):
            segments.append(text[i:i + segment_size])
        return segments

    def _build_cache_key(
        self,
        text: str,
        document_name: str,
        category: str,
        region: str,
    ) -> str:
        """构建缓存键"""
        import hashlib
        content = f"{text}:{document_name}:{category}:{region}:{self.min_chunk_size}:{self.max_chunk_size}"
        return hashlib.md5(content.encode()).hexdigest()

    def _result_to_cache(self, result: ChunkingResult) -> dict[str, Any]:
        """将结果转换为缓存格式"""
        return {
            "chunks": [
                {
                    "content": c.content,
                    "article_number": c.metadata.article_number,
                    "section_number": c.metadata.section_number,
                    "chapter": c.metadata.chapter,
                    "reason": c.metadata.reason,
                }
                for c in result.chunks
            ],
            "total_chars": result.total_chars,
            "total_chunks": result.total_chunks,
            "structure_summary": result.structure_summary,
        }

    def _cached_to_result(self, cached: dict[str, Any]) -> ChunkingResult:
        """从缓存恢复结果"""
        chunks = []
        for idx, chunk_data in enumerate(cached.get("chunks", [])):
            chunks.append(
                TextChunk(
                    content=chunk_data["content"],
                    metadata=ChunkMetadata(
                        article_number=chunk_data.get("article_number"),
                        section_number=chunk_data.get("section_number"),
                        chapter=chunk_data.get("chapter"),
                        reason=chunk_data.get("reason", ""),
                    ),
                    index=idx,
                    char_count=len(chunk_data["content"]),
                )
            )
        return ChunkingResult(
            chunks=chunks,
            total_chars=cached.get("total_chars", 0),
            total_chunks=cached.get("total_chunks", len(chunks)),
            structure_summary=cached.get("structure_summary", ""),
        )


# ============================================================================
# Fallback Rule-based Splitter
# ============================================================================

class _FallbackTextSplitter:
    """备用规则分块器（LLM 不可用时使用）"""

    
    ARTICLE_PATTERN = re.compile(r"(第[零一二三四五六七八九十百千零\d]+条)")
    SECTION_PATTERN = re.compile(r"(第[零一二三四五六七八九十百千零\d]+款)")
    CHAPTER_PATTERN = re.compile(r"(第[零一二三四五六七八九十百千零\d]+章)")
    NUMBERED_PATTERN = re.compile(r"^([零一二三四五六七八九十百千\d]+[、.])")

    def __init__(self, separators: Optional[List[str]] = None):
        self.separators = separators or [
            r"第[零一二三四五六七八九十百千零\d]+条",
            r"第[零一二三四五六七八九十百千零\d]+款",
            r"第[零一二三四五六七八九十百千零\d]+章",
            r"[零一二三四五六七八九十百千\d]+[、.]",
            r"\n\n+",
        ]

    def split_text(self, text: str) -> List[str]:
        """分割文本"""
        chunks = []
        current_chunk = ""
        current_chapter = None

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是新条款开始
            article_match = self.ARTICLE_PATTERN.search(line)
            if article_match:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line
                continue

            # 检查是否是新编号项开始（一、二、三、... 或 1. 2. 3.）
            numbered_match = self.NUMBERED_PATTERN.match(line)
            if numbered_match:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line
                continue

            # 检查章节
            chapter_match = self.CHAPTER_PATTERN.search(line)
            if chapter_match:
                current_chapter = chapter_match.group(1)

            # 累积内容
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [c for c in chunks if c]

    def extract_metadata(self, text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """提取元数据"""
        article = self.ARTICLE_PATTERN.search(text)
        section = self.SECTION_PATTERN.search(text)
        chapter = self.CHAPTER_PATTERN.search(text)

        return (
            article.group(1) if article else None,
            section.group(1) if section else None,
            chapter.group(1) if chapter else None,
        )


# ============================================================================
# Singleton Instance
# ============================================================================

_default_llm_chunker: Optional[LLMChunkingService] = None


def get_default_llm_chunker() -> LLMChunkingService:
    """获取默认的 LLM 分块服务实例"""
    global _default_llm_chunker
    if _default_llm_chunker is None:
        _default_llm_chunker = LLMChunkingService()
    return _default_llm_chunker


def chunk_text_with_llm(
    text: str,
    *,
    document_name: str = "",
    category: str = "",
    region: str = "",
    config: Optional[LLMConfig] = None,
) -> ChunkingResult:
    """
    便捷函数：使用 LLM 分块文本

    Args:
        text: 待分块文本
        document_name: 文档名称
        category: 文档类别
        region: 适用地区
        config: LLM 配置

    Returns:
        ChunkingResult: 分块结果
    """
    chunker = LLMChunkingService(config=config) if config else get_default_llm_chunker()
    return chunker.chunk_text(
        text,
        document_name=document_name,
        category=category,
        region=region,
    )


def chunk_document_with_llm(
    file_path: str,
    *,
    category: str = "",
    region: str = "",
    config: Optional[LLMConfig] = None,
) -> ChunkingResult:
    """
    便捷函数：使用 LLM 分块文档文件

    Args:
        file_path: 文档路径
        category: 文档类别
        region: 适用地区
        config: LLM 配置

    Returns:
        ChunkingResult: 分块结果
    """
    chunker = LLMChunkingService(config=config) if config else get_default_llm_chunker()
    return chunker.chunk_document(
        file_path,
        category=category,
        region=region,
    )
