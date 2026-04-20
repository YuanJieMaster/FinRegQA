"""
金融知识库系统 - 使用示例
Financial Knowledge Base System - Usage Example

演示如何使用MySQL+Milvus构建金融知识库
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from app.services.knowledge_base import KnowledgeBaseService as FinancialKnowledgeBase
from app.services.text_processor import (
    TextSplitterService as FinancialRegulationSplitter,
    load_financial_document,
)
from dotenv import load_dotenv
load_dotenv()

_DEFAULT_KB = None


def get_default_kb() -> FinancialKnowledgeBase:
    """
    获取（并缓存）默认 FinancialKnowledgeBase 实例。

    连接参数可通过环境变量覆盖：
    - FINREGQA_DB_HOST / FINREGQA_DB_PORT / FINREGQA_DB_NAME / FINREGQA_DB_USER / FINREGQA_DB_PASSWORD
    - FINREGQA_EMBEDDING_MODEL / FINREGQA_MILVUS_HOST / FINREGQA_MILVUS_PORT / FINREGQA_EMBEDDING_DIM
    """

    global _DEFAULT_KB
    if _DEFAULT_KB is not None:
        return _DEFAULT_KB

    _DEFAULT_KB = FinancialKnowledgeBase(
        db_host=os.getenv("FINREGQA_DB_HOST", "localhost"),
        db_port=int(os.getenv("FINREGQA_DB_PORT", "3306")),
        db_name=os.getenv("FINREGQA_DB_NAME", "finregqa"),
        db_user=os.getenv("FINREGQA_DB_USER", "root"),
        db_password=os.getenv("FINREGQA_DB_PASSWORD", "root_password"),
        embedding_model=os.getenv("FINREGQA_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
        embedding_dim=int(os.getenv("FINREGQA_EMBEDDING_DIM", "768")),
    )
    return _DEFAULT_KB


def close_default_kb() -> None:
    """关闭默认 KB 连接池（如果已创建）。"""

    global _DEFAULT_KB
    if _DEFAULT_KB is not None:
        _DEFAULT_KB.close()
        _DEFAULT_KB = None


_CHAPTER_RE = re.compile(r"(第[零一二三四五六七八九十百千\d]+章)")
_ARTICLE_RE = re.compile(r"(第[零一二三四五六七八九十百千\d]+条)")
_SECTION_RE = re.compile(r"(第[零一二三四五六七八九十百千\d]+款)")


def _extract_regulation_structure(
    chunk: str, current_chapter: Optional[str]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    从 chunk 中抽取“章/条/款”结构，并返回更新后的 current_chapter。

    说明：
    - 分块器在 keep_separator=True 时通常会把“第X章/第Y条”保留在 chunk 内；这里用正则做容错抽取。
    - 金融法规存在跨 chunk 的上下文（例如章标题在上一个 chunk），因此章节用状态机方式沿用。
    """

    text = (chunk or "").strip()
    if not text:
        return current_chapter, None, None

    chapter = current_chapter
    m_chapter = _CHAPTER_RE.search(text[:50])
    if m_chapter:
        chapter = m_chapter.group(1)

    m_article = _ARTICLE_RE.search(text[:60])
    article = m_article.group(1) if m_article else None

    m_section = _SECTION_RE.search(text[:80])
    section = m_section.group(1) if m_section else None

    return chapter, article, section


def ingest_regulation_file(
    file_path: str,
    category: str,
    regulation_type: str,
    *,
    region: Optional[str] = None,
    source: Optional[str] = None,
    min_chunk_size: int = 1,
    keep_separator: bool = True,
    batch_size: int = 100,
    kb: Optional[FinancialKnowledgeBase] = None,
) -> Dict:
    """
    金融分块器 → 知识库：一键导入单个监管文件（PDF/DOCX/TXT）。

    1. 使用 load_financial_document + FinancialRegulationSplitter 分块
    2. 为每个 chunk 生成 metadata（章节名、条款号、款号等）
    3. 调用 FinancialKnowledgeBase.add_document + add_knowledge_batch 写入

    Args:
        file_path: 文件路径（.pdf/.docx/.txt）
        category: 默认分类
        regulation_type: 监管类型（写入 knowledge.regulation_type）
        region: 地区（可选；当前用于文档来源信息补充）
        source: 文档来源（document.source）；不传则默认使用 file_path
        min_chunk_size: 过滤短片段阈值（字符数）
        keep_separator: 是否保留“第X章/第X条”等结构标识
        batch_size: 写入批大小（knowledge_base.add_knowledge_batch）
        kb: 可选：传入现成的 FinancialKnowledgeBase；不传则使用 get_default_kb()

    Returns:
        导入结果：包含 document_id / chunk_count / success / failed 等统计
    """

    if not file_path or not str(file_path).strip():
        raise ValueError("file_path 不能为空")

    kb = kb or get_default_kb()

    doc = load_financial_document(file_path, clean_text=True)
    splitter = FinancialRegulationSplitter(
        min_chunk_size=min_chunk_size,
        keep_separator=keep_separator,
    )
    chunks = splitter.split_text(doc.page_content)

    file_name = doc.metadata.get("file_name") or os.path.basename(file_path)
    file_type = (doc.metadata.get("file_type") or "").lstrip(".")
    base_source = source or doc.metadata.get("source") or file_path
    doc_source = f"{base_source} | 地区: {region}" if region else base_source

    document_id = kb.add_document(
        name=file_name,
        source=doc_source,
        file_type=file_type or None,
    )

    knowledge_items: List[Dict] = []

    for chunk in chunks:
        # 仅存储“条”（第X条）。识别到“章”（第X章）则丢弃，不写入任何字段，也不跨 chunk 沿用。
        _ignored_chapter, article_number, _ignored_section_number = _extract_regulation_structure(
            chunk, None
        )

        # 分类字段始终使用调用方传入的 category；
        item_category = category

        knowledge_items.append(
            {
                "content": chunk.strip(),
                "category": item_category,
                "region": region,
                "regulation_type": regulation_type,
                "article_number": article_number,
                "section_number": None,
            }
        )

    success, failed = kb.add_knowledge_batch(
        document_id=document_id,
        knowledge_items=knowledge_items,
        batch_size=batch_size,
    )

    return {
        "document_id": document_id,
        "file_name": file_name,
        "file_type": file_type,
        "chunk_count": len(chunks),
        "success": success,
        "failed": failed,
    }


def answer_question(question: str, region: Optional[str] = None) -> dict:
    """
    输入用户问题，返回：
    - answer: 生成的自然语言答案（优先走大模型RAG生成）
    - references: 用到的知识片段（content、article_number、document_name 等）
    - raw_results: 原始检索结果
    """

    q = (question or "").strip()
    if not q:
        return {
            "answer": "问题为空：请提供一个具体的金融监管问题。",
            "references": [],
            "raw_results": [],
        }

    kb = get_default_kb()

    # 检索参数：优先从环境变量读，便于调参；不给则使用合理默认值
    top_k = int(os.getenv("FINREGQA_TOP_K", "8"))
    threshold = float(os.getenv("FINREGQA_THRESHOLD", "0.05"))

    normalized_region = (region or "").strip() or None

    # 可选地区过滤：先按地区检索，结果不足时回退到全局检索补足
    raw_results = kb.search(query=q, top_k=top_k, threshold=threshold, region=normalized_region)
    # if normalized_region and len(raw_results) < max(2, min(top_k, 5)):
    if normalized_region == "全国":
        fallback_results = kb.search(query=q, top_k=top_k, threshold=threshold)
        existing_ids = {r.get("knowledge_id") for r in raw_results}
        for item in fallback_results:
            kid = item.get("knowledge_id")
            if kid not in existing_ids:
                raw_results.append(item)
                existing_ids.add(kid)
            if len(raw_results) >= top_k:
                break

    references = [
        {
            "knowledge_id": r.get("knowledge_id"),
            "document_name": r.get("document_name"),
            "category": r.get("category"),
            "region": r.get("region"),
            "regulation_type": r.get("regulation_type"),
            "article_number": r.get("article_number"),
            "section_number": r.get("section_number"),
            "similarity": r.get("similarity"),
            "content": r.get("content"),
        }
        for r in raw_results
    ]

    if not raw_results:
        return {
            "answer": (
                "未检索到足够相关的法规依据，无法可靠回答。"
                "你可以尝试更具体的关键词（如“核心一级资本充足率”“流动性覆盖率”）或降低检索阈值（FINREGQA_THRESHOLD）。"
            ),
            "references": [],
            "raw_results": raw_results,
        }

    # 优先尝试大模型 RAG 生成（LangChain）；失败时回退到下方抽取式回答
    top_refs = references[: min(5, len(references))]
    llm_model = os.getenv("FINREGQA_LLM_MODEL", "gpt-4o-mini")
    llm_temperature = float(os.getenv("FINREGQA_LLM_TEMPERATURE", "0.1"))
    llm_base_url = os.getenv("FINREGQA_LLM_BASE_URL")
    llm_api_key = os.getenv("FINREGQA_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        context_lines = []
        for i, ref in enumerate(top_refs, 1):
            doc = ref.get("document_name") or "未知文档"
            art = ref.get("article_number") or "未标明条款"
            sec = ref.get("section_number") or ""
            sim = ref.get("similarity")
            sim_text = f"{sim:.3f}" if isinstance(sim, (int, float)) else "N/A"
            content = (ref.get("content") or "").strip()
            if len(content) > 500:
                content = content[:500] + "…"
            context_lines.append(
                f"【依据{i}】文档：{doc}｜条款：{art} {sec}｜相似度：{sim_text}\n{content}"
            )

        context_text = "\n\n".join(context_lines)

        prompt = ChatPromptTemplate.from_template(
            """
你是一名严谨的金融监管问答助手。请严格基于“法规依据”回答，不得编造。

回答规则：
1. 只允许使用提供的法规依据。

3. 先给出结论，再给出依据说明。
4. 涉及比例、数值、期限时，必须在依据中指出来源条款。

用户问题：
{question}

法规依据：
{context}

请按以下格式输出：
【结论】
...

【依据说明】
...

【适用边界/风险提示】
...
""".strip()
        )

        llm_kwargs = {
            "model": llm_model,
            "temperature": llm_temperature,
        }
        if llm_base_url:
            llm_kwargs["base_url"] = llm_base_url
        if llm_api_key:
            llm_kwargs["api_key"] = llm_api_key

        llm = ChatOpenAI(**llm_kwargs)
        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke({"question": q, "context": context_text})

        return {
            "answer": answer,
            "references": top_refs,
            "raw_results": raw_results,
        }
    except Exception:
        # 打印错误
        import sys
        print(f"Error: {e}", file=sys.stderr)

    # 生成一个“可控”的答案：把最相关的 1-3 条依据拼接，并明确来源
    top_refs = references[: min(3, len(references))]
    lines = []
    lines.append(f"问题：{q}")
    lines.append("基于已检索到的法规片段，相关依据如下：")
    for i, ref in enumerate(top_refs, 1):
        doc = ref.get("document_name") or "未知文档"
        art = ref.get("article_number") or ""
        sec = ref.get("section_number") or ""
        sim = ref.get("similarity")
        sim_text = f"{sim:.3f}" if isinstance(sim, (int, float)) else "N/A"
        snippet = (ref.get("content") or "").strip()
        if len(snippet) > 240:
            snippet = snippet[:240] + "…"
        lines.append(f"{i}) [{doc}] {art} {sec}（相似度 {sim_text}）：{snippet}")

    lines.append("结论：以上为检索到的条款依据摘要；如需严格合规结论，请以原文条款为准并补充更具体问题。")

    return {
        "answer": "\n".join(lines),
        "references": top_refs,
        "raw_results": raw_results,
    }


def example_basic_usage():
    """基本使用示例"""
    print("=" * 80)
    print("示例1: 基本使用")
    print("=" * 80)
    
    # 初始化知识库
    kb = FinancialKnowledgeBase(
        db_host="localhost",
        db_port=3306,
        db_name="finregqa",
        db_user="root",
        db_password="root_password",
        embedding_model="BAAI/bge-small-zh-v1.5",
        embedding_dim=768
    )
    
    # 添加文档
    doc_id = kb.add_document(
        name="商业银行监管规则",
        source="中国银保监会",
        file_type="txt"
    )
    print(f"✓ 文档已添加 (ID: {doc_id})")
    
    # 准备知识点数据
    knowledge_items = [
        {
            'content': '商业银行应当建立健全风险管理体系，包括风险识别、计量、监测和控制等环节。',
            'category': '风险管理',
            'regulation_type': '商业银行监管',
            'article_number': '第一条',
            'section_number': '第一款'
        },
        {
            'content': '银行资本充足率不得低于8%，其中核心一级资本充足率不得低于4.5%。',
            'category': '资本管理',
            'regulation_type': '资本充足率',
            'article_number': '第二条',
            'section_number': '第一款'
        },
        {
            'content': '流动性覆盖率应当不低于100%，净稳定融资比率应当不低于100%。',
            'category': '流动性管理',
            'regulation_type': '流动性监管',
            'article_number': '第三条',
            'section_number': '第一款'
        },
        {
            'content': '银行应当建立有效的内部控制制度，确保业务活动的合规性和有效性。',
            'category': '内部控制',
            'regulation_type': '合规管理',
            'article_number': '第四条',
            'section_number': '第一款'
        },
        {
            'content': '信息披露应当真实、准确、完整、及时，不得有虚假记载或误导性陈述。',
            'category': '信息披露',
            'regulation_type': '披露要求',
            'article_number': '第五条',
            'section_number': '第一款'
        },
    ]
    
    # 批量导入知识点
    success_count, fail_count = kb.add_knowledge_batch(
        document_id=doc_id,
        knowledge_items=knowledge_items,
        batch_size=10
    )
    print(f"✓ 知识点导入完成: {success_count}个成功, {fail_count}个失败")
    
    # 执行检索
    print("\n执行检索...")
    results = kb.search(query="风险管理", top_k=3, threshold=0.6)
    
    print(f"\n检索结果 (查询: '风险管理'):")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. 相似度: {result['similarity']:.4f}")
        print(f"   分类: {result['category']}")
        print(f"   内容: {result['content'][:60]}...")
        print(f"   条款: {result['article_number']} {result['section_number']}")
    
    # 获取统计信息
    stats = kb.get_statistics()
    print(f"\n知识库统计:")
    print(f"  - 文档数: {stats['document_count']}")
    print(f"  - 知识点数: {stats['knowledge_count']}")
    print(f"  - Milvus向量数: {stats.get('milvus_vector_count', 'N/A')}")
    print(f"  - 分类分布: {stats['category_distribution']}")
    
    kb.close()


def example_batch_import():
    """批量导入示例"""
    print("\n" + "=" * 80)
    print("示例2: 批量导入大规模数据")
    print("=" * 80)
    
    kb = FinancialKnowledgeBase(
        db_host="localhost",
        db_port=3306,
        db_name="finregqa",
        db_user="root",
        db_password="root_password",
        embedding_model="BAAI/bge-small-zh-v1.5"
    )
    
    # 添加文档
    doc_id = kb.add_document(
        name="金融监管条例汇编",
        source="监管部门",
        file_type="pdf"
    )
    
    # 生成大量知识点
    knowledge_items = []
    categories = ['风险管理', '资本管理', '流动性管理', '内部控制', '信息披露']
    regulation_types = ['商业银行监管', '资本要求', '流动性要求', '合规要求', '披露要求']
    
    for i in range(100):
        knowledge_items.append({
            'content': f'这是第{i+1}个金融监管知识点，涉及{categories[i % len(categories)]}方面的要求',
            'category': categories[i % len(categories)],
            'regulation_type': regulation_types[i % len(regulation_types)],
            'article_number': f'第{i+1}条',
            'section_number': f'第{(i % 5) + 1}款'
        })
    
    # 批量导入
    success_count, fail_count = kb.add_knowledge_batch(
        document_id=doc_id,
        knowledge_items=knowledge_items,
        batch_size=20
    )
    
    print(f"✓ 批量导入完成: {success_count}个知识点")
    
    # 多个查询测试
    queries = ['风险', '资本', '流动性', '内部', '信息']
    print(f"\n执行{len(queries)}个查询测试:")
    
    for query in queries:
        results = kb.search(query=query, top_k=3)
        print(f"  - '{query}': {len(results)}个结果")
    
    kb.close()


def example_error_handling():
    """异常处理示例"""
    print("\n" + "=" * 80)
    print("示例3: 异常处理")
    print("=" * 80)
    
    try:
        kb = FinancialKnowledgeBase(
            db_host="localhost",
            db_port=3306,
            db_name="finregqa",
            db_user="root",
            db_password="root_password"
        )
        
        # 测试无效查询
        print("测试无效查询...")
        results = kb.search(query="", top_k=5)
        print(f"✓ 空查询处理成功: {len(results)}个结果")
        
        # 测试特殊字符
        results = kb.search(query="@#$%^&*()", top_k=5)
        print(f"✓ 特殊字符查询处理成功: {len(results)}个结果")
        
        kb.close()
    
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_performance_test():
    """性能测试示例"""
    print("\n" + "=" * 80)
    print("示例4: 性能测试")
    print("=" * 80)
    
    import time
    
    kb = FinancialKnowledgeBase(
        db_host="localhost",
        db_port=3306,
        db_name="finregqa",
        db_user="root",
        db_password="root_password",
        embedding_model="BAAI/bge-small-zh-v1.5"
    )
    
    # 添加文档
    doc_id = kb.add_document(
        name="性能测试文档",
        source="测试",
        file_type="txt"
    )
    
    # 生成知识点
    print("生成500个知识点...")
    knowledge_items = [
        {
            'content': f'知识点{i}: 这是关于金融监管的第{i}个知识点，包含重要的监管要求',
            'category': f'分类_{i % 10}',
            'regulation_type': f'类型_{i % 5}',
            'article_number': f'第{i}条',
            'section_number': f'第{i % 20}款'
        }
        for i in range(500)
    ]
    
    # 测试导入性能
    print("测试导入性能...")
    start_time = time.time()
    success_count, fail_count = kb.add_knowledge_batch(
        document_id=doc_id,
        knowledge_items=knowledge_items,
        batch_size=50
    )
    import_time = time.time() - start_time
    
    print(f"✓ 导入性能:")
    print(f"  - 导入数量: {success_count}个")
    print(f"  - 耗时: {import_time:.2f}秒")
    print(f"  - 吞吐量: {success_count/import_time:.0f}个/秒")
    
    # 测试检索性能
    print("\n测试检索性能...")
    queries = ['风险', '资本', '流动性', '内部', '信息', '监管', '要求', '制度']
    response_times = []
    
    for query in queries:
        start_time = time.time()
        results = kb.search(query=query, top_k=10)
        response_time = time.time() - start_time
        response_times.append(response_time)
        print(f"  - '{query}': {response_time:.3f}秒 ({len(results)}个结果)")
    
    avg_time = sum(response_times) / len(response_times)
    print(f"\n✓ 检索性能统计:")
    print(f"  - 平均响应时间: {avg_time:.3f}秒")
    print(f"  - 最大响应时间: {max(response_times):.3f}秒")
    print(f"  - 最小响应时间: {min(response_times):.3f}秒")
    
    kb.close()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("金融知识库系统 - 使用示例")
    print("=" * 80)
    print("\n注意: 请确保MySQL已启动并配置正确的连接参数")
    print("=" * 80)
    
    try:
        # 运行示例
        # example_basic_usage()
        # example_batch_import()
        # example_error_handling()
        # example_performance_test()

        # 测试导入
        # ingest_regulation_file("商业银行资本管理办法.pdf", "商业银行资本管理办法", "商业银行资本管理办法")
        # ingest_regulation_file("1.关于加强浙江省打击保险领域违法犯罪协调配合工作的通知.docx", "保险监管", "监管类型")

        # 测试问答
        results = answer_question("商业银行资本充足率最低要求是多少？")
        print("answer:\n")
        print(results["answer"])
        print("references:\n")
        print(results["references"])
        print("raw_results:\n")
        print(results["raw_results"])
    
    except Exception as e:
        print(f"\n✗ 执行出错: {e}")
        print("\n请检查:")
        print("1. MySQL服务是否正在运行")
        print("2. 数据库连接参数是否正确")
        print("3. 所有依赖包是否已安装 (pip install -r requirements.txt)")
