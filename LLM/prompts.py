"""Prompt builders for common FinRegQA LLM tasks."""

from __future__ import annotations

from typing import Iterable, Mapping


ANSWER_SYSTEM_PROMPT = """你是金融监管制度问答助手。

你的回答必须遵守以下规则：
1. 优先依据给定参考材料作答，不要凭空补充法规结论。
2. 回答要直接、专业、可读，适合业务人员查看。
3. 如果参考材料不足以支撑确定结论，要明确说明“根据当前检索结果无法确认”。
4. 如果引用了参考材料，要在回答中自然提及来源编号，如“参考材料1”。
5. 不要编造条款号、发布日期、监管要求或处罚结论。
"""


RERANK_SYSTEM_PROMPT = """你是金融监管检索结果重排助手。

请只根据“与问题的相关性、信息完整度、是否能直接支持回答”对候选片段排序。
返回 JSON，格式为：
{"ranked_ids":[1,3,2],"reason":"一句简短说明"}
不要输出额外解释。
"""


def build_context_block(references: Iterable[Mapping[str, object]], max_chars: int = 800) -> str:
    """Convert retrieved references into a compact context block."""

    blocks = []
    for idx, ref in enumerate(references, start=1):
        content = str(ref.get("content") or "").strip()
        if len(content) > max_chars:
            content = content[:max_chars].rstrip() + "..."

        title = str(ref.get("document_name") or ref.get("title") or "未命名文档")
        article = str(ref.get("article_number") or "").strip()
        section = str(ref.get("section_number") or "").strip()
        similarity = ref.get("similarity")
        similarity_text = (
            f"{similarity:.3f}" if isinstance(similarity, (int, float)) else "N/A"
        )

        meta_parts = [part for part in [article, section] if part]
        meta_text = " ".join(meta_parts) if meta_parts else "无条款编号"

        blocks.append(
            f"参考材料{idx}\n"
            f"文档: {title}\n"
            f"定位: {meta_text}\n"
            f"相似度: {similarity_text}\n"
            f"内容:\n{content}"
        )

    return "\n\n".join(blocks)


def build_answer_user_prompt(question: str, context_block: str) -> str:
    """Build the user prompt for answer generation."""

    return (
        f"用户问题:\n{question.strip()}\n\n"
        f"参考材料:\n{context_block.strip()}\n\n"
        "请输出三部分内容：\n"
        "1. 直接答案\n"
        "2. 依据说明\n"
        "3. 风险提示或信息不足说明"
    )


def build_rerank_user_prompt(question: str, context_block: str) -> str:
    """Build the user prompt for reranking."""

    return f"用户问题:\n{question.strip()}\n\n候选片段:\n{context_block.strip()}"
