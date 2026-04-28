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
2. 保留关键结构标识（第X条、第X款等）

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
        print("cleaned_text：", cleaned_text)

        # 尝试缓存
        # if self.enable_cache:
        #     cache_key = self._build_cache_key(cleaned_text, document_name, category, region)
        #     cached = get_cached_response(cache_key)
        #     if cached:
        #         return self._cached_to_result(cached)

        # 调用 LLM 分块
        print("调用 LLM 分块")
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
        # if self.enable_cache:
        #     set_cached_response(cache_key, self._result_to_cache(result))

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
            print("使用上下文增强分块提示")
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
        print("LLM 分块响应：", response.content)
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


# ============================================================================
# Simple Test
# ============================================================================

def _run_simple_test():
    """简单的分块测试（直接运行此文件时执行）"""
    sample_text = """
    中国银监会浙江监管局关于深化“五水共治”
金融服务的指导意见



浙银监发〔2014〕152号 


机关各处室、各银监分局、各直辖监管办，各政策性银行浙江省分行（营业部）、各国有商业银行浙江省分行（营业部），浙商银行、各股份制商业银行杭州分行，各金融资产管理公司浙江分公司（杭州办事处），邮储银行浙江省分行、杭州市分行，杭州银行、各城市商业银行杭州分行，省农信联社、杭州辖内各农村中小金融机构，各信托公司、财务公司（浙江分公司）、金融租赁公司，省银行业协会:
为切实贯彻落实浙江省委、省政府关于“五水共治”的重大战略部署，充分发挥银行业金融机构支持“五水共治”的金融服务功能，推动浙江生态文明建设和经济转型升级，现提出如下意见：
 一、充分认识金融支持“五水共治”的重要意义
（一）金融支持是“五水共治”战略顺利推进的重要保障，也是浙江银行业服务实体经济、践行绿色金融、履行社会责任的具体要求和重要载体。“五水共治”是浙江以治水为突破口，全面深化改革，实现调结构、促转型、优环境、惠民生的重大战略举措，是“建设美好浙江、创造美好生活”的重要工作抓手。浙江银行业金融机构要深刻领会“五水共治”的战略意义，认真贯彻浙江省委、省政府的战略部署，强化金融要素保障，以支持“五水共治”为着力点，进一步优化信贷结构、转变经营模式、深化金融创新，持续提升金融服务水平和核心竞争力，实现经济与金融的协调、可持续发展。
 二、找准切入点，加大信贷支持力度
（二）积极支持“五水共治”重点项目建设。银行业金融机构要围绕“411”重大项目计划和“十百千万治水大行动”，结合自身业务定位和现实条件，有侧重、分层次地提供差异化信贷支持。政策性银行应当充分发挥政策性金融功能，在业务范围内主动对接战略性、基础性水利建设项目，积极开展水利建设中长期政策性贷款业务。大型商业银行应当利用资金规模优势，积极介入符合市场化运作要求的“五水共治”重大项目，加强对优质大型客户的信贷支持力度，并延伸带动上下游中小企业金融服务。中小商业银行要充分发挥机制灵活优势，综合运用表内外融资工具和创新产品组合，提供适合“五水共治”项目特点的个性化融资服务。农村中小金融机构应当积极支持具备商业化运作条件的农村饮水安全工程、小型农田水利建设、农村水源污染治理等项目建设，加强对技术先进、经营良好、竞争力强的节能环保类中小企业的金融服务。信托公司、金融租赁公司要充分发挥功能优势，通过多元化金融工具，引导民间资本参与“五水共治”重大项目建设，加大对水务等民生领域的融资租赁投放力度。
（三）切实发挥绿色信贷倒逼转型升级作用。银行业金融机构应当将“五水共治”金融服务纳入绿色信贷发展战略，进一步丰富绿色信贷内涵，重点围绕“清三河、两覆盖、两转型”污水治理工程，提升绿色信贷工作的针对性和有效性。要按照区别对待、有保有控的原则，加大对污水治理、节排供水工程、节能环保技术改造和转型升级项目的信贷支持力度，在同等条件下优先支持污水处理、节能环保设备生产和环保服务型企业；对环评不达标项目、违法违规排污企业实行一票否决制，不得提供任何形式的新增授信；对拟关停淘汰的重污染高耗能企业，有序做好信贷压缩、退出和资产保全工作，合理运用金融杠杆倒逼企业转型升级。
（四）进一步强化“五水共治”信贷政策倾斜。银行业金融机构应当明确将“五水共治”作为当前及今后一个时期信贷投放的重点领域，通过盘活信贷存量、争取信贷规模倾斜、单列信贷计划等方式强化信贷保障工作。在风险可控、合规审慎的前提下，探索设立“五水共治”信贷审批绿色通道，对“五水共治”重点项目融资优先受理、优先评审、优先放贷，适当下放审批权限，优化审贷流程，提高业务审批效率。按照商业可持续原则，对“五水共治”优质项目和企业给予优惠利率支持。
 三、深化金融创新，拓宽融资渠道
（五）深化金融创新。银行业金融机构应当在有效控制风险和商业可持续的前提下，积极开展“五水共治”金融服务创新，完善和推广排污权质押、供水收费权质押等担保方式创新产品，探索开展“三权”抵押贷款支持农村污水治理。要充分利用好中央支持水利改革发展的有关政策，进一步拓宽水利建设项目贷款的抵（质）押物范围和还款来源。允许以水利、水电、供排水资产等作为合法担保物，探索开展水利项目收益权质押业务。允许水利建设贷款以项目自身收益、借款人其他经营性收入作为还款来源。经地方政府同意，地方水资源费、地方水利建设基金、土地出让收益中计提的用于农田水利建设的资金也可以作为水利建设项目贷款的还款来源。
（六）拓宽融资渠道。银行业金融机构应当加强同业协作，进一步加大对“五水共治”建设项目的银团贷款支持力度；加快发展投资银行业务，支持地方政府自主发债筹集“五水共治”建设资金，帮助符合条件的企业通过上市、发行债券和债务融资工具进行直接融资；积极稳妥开展并购贷款业务，支持重污染高耗能企业通过兼并重组实施转型升级。商业银行要加强与信托公司、金融租赁公司、证券、保险、基金等其他金融机构的合作，在合规经营、风险可控的前提下，创新金融服务模式，探索多样化融资方式对接“五水共治”领域合理的融资需求。
四、完善制度管理，落实保障措施
（七）制定发展规划。银行业金融机构应当根据自身发展战略、市场定位、体制机制、资金规模等实际情况，科学制定“五水共治”金融服务发展规划，明确支持方向、重点、目标和进度。银行业金融机构分支机构应及时向总行报告浙江“五水共治”重大战略决策和实施情况，积极争取信贷政策倾斜与配套资源支持。
（八）强化组织保障。银行业金融机构应当成立由单位负责人牵头的“五水共治”金融服务工作领导小组，落实责任部门，明确职责与权限，配备相应资源，组织开展与归口管理“五水共治”各项工作。要加强专业队伍建设，对相关管理、业务人员定期开展培训，切实提高“五水共治”金融服务能力。
（九）规范业务运作。银行业金融机构应当根据“五水共治”金融服务特点，制定专门的业务管理办法，或将与“五水共治”相关业务准入、退出标准嵌入现有授信业务流程，切实加强内控管理，确保合规有序开展相关业务。
（十）完善考核激励。银行业金融机构应当将“五水共治”金融服务开展情况纳入年度绩效考核体系，科学设定考核指标和办法，采取对分支机构和相关业务部门落实“五水共治”的激励约束措施，确保“五水共治”金融服务持续有效开展。
（十一）加强统计监测。银行业金融机构应当建立“五水共治”信贷统计监测制度，强化IT系统支持，定期监测包括银行贷款、票据融资、企业债券、信托计划、理财产品等在内的“五水共治”全口径资金支持情况。加强对金融支持“五水共治”经验做法的总结和宣传，并及时向监管部门报送相关情况。
 五、加强风险防控，严格执行政策要求
（十二）切实做好贷款“三查”和风险处置。银行业金融机构应当加强对贷款申请人及融资项目的尽职调查和授信审查，确保项目审批手续的合规性、有效性和完整性，科学测算项目现金流，合理设定贷款期限和还款方式。要切实加强贷后管理，持续跟踪项目建设和现金流动态变化情况。对于以地方财政资金为部分还款来源的项目，要综合考虑地方政府债务水平和还款能力，有效防范地方政府债务风险。对于因重污染高耗能企业关停淘汰造成的不良贷款，要采取多种方式加大处置力度。
（十三）认真执行宏观调控政策和监管要求。银行业金融机构在开展“五水共治”金融服务过程中，应当严格落实国务院关于金融支持经济结构调整和转型升级、化解产能严重过剩等政策要求，认真执行国家宏观调控政策和监管部门关于地方政府融资平台贷款、项目融资、理财同业业务等相关领域的监管政策，严格授信准入条件，坚持合规审慎经营，坚守风险底线，推动实现经济金融的长期可持续发展。
 六、强化监管引领，注重协同配合
（十四）充分发挥监管导向作用。各级监管部门应当加强对银行业金融机构“五水共治”金融服务的监测和评估，将评估结果作为银行业金融机构监管评级、机构准入、业务准入的依据，通过实施差异化监管政策，引导银行业金融机构积极稳妥推进“五水共治”金融服务工作。
（十五）加强与政府部门沟通协作。各级监管部门应当主动加强与相关政府部门的联系，积极争取地方政府支持，推动形成有利于“五水共治”金融服务的外部环境。努力构建常态化的信息共享机制，帮助银行业金融机构及时了解“五水共治”项目规划和建设情况，有针对性地落实融资安排。进一步推动政银企合作，引导银行业金融机构对接政府部门推荐的优质项目和企业。




                 中国银监会浙江监管局
                 2014年9月29日
    """

    print("=" * 60)
    print("LLM 智能分块测试")
    print("=" * 60)

    try:
        result = chunk_text_with_llm(
            sample_text,
            document_name="商业银行监管指导意见",
            category="银行监管",
            region="全国",
        )

        print(f"\n[OK] 分块成功!")
        print(f"  - 分块数量: {result.total_chunks}")
        print(f"  - 总字符数: {result.total_chars}")

        if result.structure_summary:
            print(f"  - 结构概述: {result.structure_summary[:100]}...")

        print(f"\n各分块详情:")
        for i, chunk in enumerate(result.chunks):
            article = chunk.metadata.article_number or "无"
            print(f"  块 {i + 1} [条款: {article}]: {chunk.content[:50]}...")

        return True

    except Exception as e:
        print(f"\n[FAIL] 分块失败: {e}")
        return False


if __name__ == "__main__":
    success = _run_simple_test()
    print("\n" + ("测试通过!" if success else "测试失败，请检查配置。"))
