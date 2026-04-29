"""
评估API路由
提供评估功能的 REST API 接口

支持动态分块分析功能，可根据文档结构自动计算分块预期范围。
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List

from app.services.evaluation import (
    get_evaluation_service,
    QAPair,
    analyze_document_for_testing,
    get_ingest_test_case_for_file
)

router = APIRouter(prefix="/evaluation", tags=["评估"])


# ============================================================================
# 请求/响应模型
# ============================================================================

class QAPairRequest(BaseModel):
    """问答对请求"""
    question: str
    ground_truth_answer: str
    ground_truth_context: Optional[List[str]] = []
    keywords: Optional[List[str]] = []
    difficulty: str = "medium"
    source_regulation: str = ""
    notes: str = ""


class SingleEvalRequest(BaseModel):
    """单个评估请求"""
    question: str
    generated_answer: str
    retrieved_contexts: Optional[List[str]] = []
    ground_truth: Optional[str] = None


class BatchEvalRequest(BaseModel):
    """批量评估请求"""
    api_url: str = "http://localhost:8000"
    custom_test_cases: Optional[List[dict]] = None  # 自定义测试用例
    use_default_pairs: bool = True  # 是否使用默认问答对


class DocumentAnalysisRequest(BaseModel):
    """文档分析请求"""
    file_path: str  # 文档路径


class DocumentAnalysisResponse(BaseModel):
    """文档分析响应"""
    success: bool
    document_name: str = ""
    document_type: str = ""
    complexity: str = ""
    total_articles: int = 0
    total_chapters: int = 0
    text_length: int = 0
    predicted_chunk_range: dict = {}
    recommended_chunk_size: int = 0
    structure_features: List[str] = []
    error: str = ""


class ChunkAccuracyRequest(BaseModel):
    """分块准确率评估请求"""
    file_path: str
    actual_chunk_count: int
    api_url: str = "http://localhost:8000"


class QAPairResponse(BaseModel):
    """问答对响应"""
    question: str
    ground_truth_answer: str
    ground_truth_context: List[str]
    keywords: List[str]
    difficulty: str


class EvaluationMetricsResponse(BaseModel):
    """评估指标响应"""
    recall: float
    precision: float
    f1_score: float
    hit_rate: float
    mrr: float
    ndcg: float
    exact_match: float
    rouge_l: float
    keyword_coverage: float
    keyword_precision: float
    semantic_similarity: float
    length_ratio: float


class EvaluationResultResponse(BaseModel):
    """评估结果响应"""
    question: str
    generated_answer: str
    ground_truth: str
    retrieval_metrics: dict
    answer_metrics: dict
    response_time: float
    error: str = ""


class EvaluationReportResponse(BaseModel):
    """评估报告响应"""
    timestamp: str
    total_questions: int
    successful_tests: int
    failed_tests: int
    retrieval_metrics: dict
    answer_metrics: dict
    overall_score: float
    results: List[EvaluationResultResponse]


class ReportListItem(BaseModel):
    """报告列表项"""
    filename: str
    created: str
    size: int


# ============================================================================
# API 端点
# ============================================================================

@router.get("/", response_model=dict)
async def get_evaluation_info():
    """获取评估功能信息"""
    service = get_evaluation_service()
    qa_pairs = service.get_qa_pairs()

    return {
        "name": "FinRegQA 准确率评估系统",
        "version": "1.0.0",
        "description": "用于评估问答系统的检索和回答准确率",
        "qa_pairs_count": len(qa_pairs),
        "default_metrics": [
            "recall", "precision", "f1_score", "hit_rate", "mrr", "ndcg",
            "exact_match", "rouge_l", "keyword_coverage", "keyword_precision",
            "semantic_similarity", "length_ratio"
        ]
    }


@router.get("/qa-pairs", response_model=List[QAPairResponse])
async def list_qa_pairs():
    """获取问答对列表"""
    service = get_evaluation_service()
    qa_pairs = service.get_qa_pairs()

    return [
        QAPairResponse(
            question=qa.question,
            ground_truth_answer=qa.ground_truth_answer,
            ground_truth_context=qa.ground_truth_context,
            keywords=qa.keywords,
            difficulty=qa.difficulty
        )
        for qa in qa_pairs
    ]


@router.post("/qa-pairs", response_model=dict)
async def add_qa_pair(qa_pair: QAPairRequest):
    """添加问答对"""
    service = get_evaluation_service()

    new_qa = QAPair(
        question=qa_pair.question,
        ground_truth_answer=qa_pair.ground_truth_answer,
        ground_truth_context=qa_pair.ground_truth_context,
        keywords=qa_pair.keywords,
        difficulty=qa_pair.difficulty,
        source_regulation=qa_pair.source_regulation,
        notes=qa_pair.notes
    )

    service.add_qa_pair(new_qa)

    return {"message": "问答对添加成功", "question": qa_pair.question}


@router.delete("/qa-pairs/{index}", response_model=dict)
async def delete_qa_pair(index: int):
    """删除问答对"""
    service = get_evaluation_service()

    if service.remove_qa_pair(index):
        return {"message": f"问答对 {index} 删除成功"}
    else:
        raise HTTPException(status_code=404, detail="问答对不存在")


@router.post("/evaluate/single", response_model=EvaluationResultResponse)
async def evaluate_single(req: SingleEvalRequest):
    """评估单个问答结果"""
    service = get_evaluation_service()

    result = service.evaluate_single(
        question=req.question,
        generated_answer=req.generated_answer,
        retrieved_contexts=req.retrieved_contexts,
        ground_truth=req.ground_truth
    )

    return EvaluationResultResponse(
        question=result.question,
        generated_answer=result.generated_answer,
        ground_truth=result.ground_truth,
        retrieval_metrics={
            "recall": result.retrieval_metrics.recall,
            "precision": result.retrieval_metrics.precision,
            "f1_score": result.retrieval_metrics.f1_score,
            "hit_rate": result.retrieval_metrics.hit_rate,
            "mrr": result.retrieval_metrics.mrr,
            "ndcg": result.retrieval_metrics.ndcg
        },
        answer_metrics={
            "exact_match": result.answer_metrics.exact_match,
            "rouge_l": result.answer_metrics.rouge_l,
            "keyword_coverage": result.answer_metrics.keyword_coverage,
            "keyword_precision": result.answer_metrics.keyword_precision,
            "semantic_similarity": result.answer_metrics.semantic_similarity,
            "length_ratio": result.answer_metrics.length_ratio
        },
        response_time=result.response_time,
        error=result.error
    )


@router.post("/evaluate/batch", response_model=EvaluationReportResponse)
async def evaluate_batch(req: BatchEvalRequest):
    """
    批量评估

    使用配置的 API 地址运行批量测试
    """
    service = get_evaluation_service()

    # 准备测试用例
    if req.custom_test_cases:
        test_cases = req.custom_test_cases
    elif req.use_default_pairs:
        qa_pairs = service.get_qa_pairs()
        test_cases = [
            {
                "question": qa.question,
                "ground_truth": qa.ground_truth_answer,
                "expected_keywords": qa.keywords
            }
            for qa in qa_pairs
        ]
    else:
        raise HTTPException(status_code=400, detail="请提供测试用例或启用默认问答对")

    # 运行评估
    report = service.evaluate_batch(
        test_cases=test_cases,
        api_url=req.api_url
    )

    # 保存报告
    filepath = service.save_report(report)

    return EvaluationReportResponse(
        timestamp=report.timestamp,
        total_questions=report.total_questions,
        successful_tests=report.successful_tests,
        failed_tests=report.failed_tests,
        retrieval_metrics={
            "recall": report.retrieval_metrics.recall,
            "precision": report.retrieval_metrics.precision,
            "f1_score": report.retrieval_metrics.f1_score,
            "hit_rate": report.retrieval_metrics.hit_rate,
            "mrr": report.retrieval_metrics.mrr,
            "ndcg": report.retrieval_metrics.ndcg
        },
        answer_metrics={
            "exact_match": report.answer_metrics.exact_match,
            "rouge_l": report.answer_metrics.rouge_l,
            "keyword_coverage": report.answer_metrics.keyword_coverage,
            "keyword_precision": report.answer_metrics.keyword_precision,
            "semantic_similarity": report.answer_metrics.semantic_similarity,
            "length_ratio": report.answer_metrics.length_ratio
        },
        overall_score=report.overall_score,
        results=[
            EvaluationResultResponse(
                question=r.get("question", ""),
                generated_answer=r.get("generated_answer", ""),
                ground_truth=r.get("ground_truth", ""),
                retrieval_metrics=r.get("retrieval_metrics", {}),
                answer_metrics=r.get("answer_metrics", {}),
                response_time=r.get("response_time", 0),
                error=r.get("error", "")
            )
            for r in report.results
        ]
    )


# ============================================================================
# 文档导入评估 API
# ============================================================================

class IngestEvalRequest(BaseModel):
    """文档导入评估请求"""
    api_url: str = "http://localhost:8000"


class IngestResultResponse(BaseModel):
    """文档导入结果响应"""
    file_name: str
    file_type: str
    expected_chunks: int
    actual_chunks: int
    chunk_count_accuracy: float
    chunk_size_accuracy: float
    content_completeness: float
    keyword_retention: float
    field_accuracy: dict
    error: str = ""
    # 动态分析结果
    dynamic_analysis: Optional[dict] = None


class IngestReportResponse(BaseModel):
    """文档导入评估报告响应"""
    timestamp: str
    total_files: int
    successful_files: int
    failed_files: int
    avg_chunk_count_accuracy: float
    avg_chunk_size_accuracy: float
    avg_content_completeness: float
    avg_keyword_retention: float
    overall_score: float
    results: List[IngestResultResponse]
    # 新增：动态分析相关
    avg_dynamic_accuracy_score: float = 0.0
    dynamic_analysis_enabled: bool = True
    document_complexity_distribution: dict = {}


@router.post("/evaluate/ingest", response_model=IngestReportResponse)
async def evaluate_ingest(req: IngestEvalRequest):
    """
    评估文档导入准确率（支持动态分析）

    使用预置的测试文档进行导入测试，评估：
    - 分块数量准确率（基于动态分析的预期范围）
    - 分块大小准确率
    - 内容完整性
    - 关键词保留率
    - 动态准确率得分（根据文档结构特征计算）

    动态分析会自动检测文档的条款数、章节数等结构特征，
    计算出合理的分块预期范围，而非使用硬编码的固定值。
    """
    service = get_evaluation_service()

    # 获取测试用例
    test_cases = service.get_ingest_test_cases()

    # 运行批量评估（启用动态分析）
    report = service.evaluate_ingest_batch(
        api_url=req.api_url,
        test_cases=test_cases,
        enable_dynamic_analysis=True
    )

    return IngestReportResponse(
        timestamp=report.timestamp,
        total_files=report.total_files,
        successful_files=report.successful_files,
        failed_files=report.failed_files,
        avg_chunk_count_accuracy=report.avg_chunk_count_accuracy,
        avg_chunk_size_accuracy=report.avg_chunk_size_accuracy,
        avg_content_completeness=report.avg_content_completeness,
        avg_keyword_retention=report.avg_keyword_retention,
        overall_score=report.overall_score,
        results=[
            IngestResultResponse(
                file_name=r.get("file_name", ""),
                file_type=r.get("file_type", ""),
                expected_chunks=r.get("expected_chunks", 0),
                actual_chunks=r.get("actual_chunks", 0),
                chunk_count_accuracy=r.get("chunk_count_accuracy", 0),
                chunk_size_accuracy=r.get("chunk_size_accuracy", 0),
                content_completeness=r.get("content_completeness", 0),
                keyword_retention=r.get("keyword_retention", 0),
                field_accuracy=r.get("field_accuracy", {}),
                error=r.get("error", ""),
                dynamic_analysis=r.get("dynamic_analysis")
            )
            for r in report.results
        ],
        avg_dynamic_accuracy_score=report.avg_dynamic_accuracy_score,
        dynamic_analysis_enabled=report.dynamic_analysis_enabled,
        document_complexity_distribution=report.document_complexity_distribution
    )


@router.post("/analyze/document", response_model=DocumentAnalysisResponse)
async def analyze_document(req: DocumentAnalysisRequest):
    """
    分析文档结构

    分析指定文档的结构特征，返回：
    - 文档类型（法规、通知、指引等）
    - 复杂度等级
    - 条款数和章节数
    - 预测的分块数量范围
    - 推荐的块大小
    - 结构特征列表
    """
    result = analyze_document_for_testing(req.file_path)

    if result.get("success"):
        return DocumentAnalysisResponse(
            success=True,
            document_name=result.get("document_name", ""),
            document_type=result.get("document_type", ""),
            complexity=result.get("complexity", ""),
            total_articles=result.get("total_articles", 0),
            total_chapters=result.get("total_chapters", 0),
            text_length=result.get("text_length", 0),
            predicted_chunk_range=result.get("predicted_chunk_range", {}),
            recommended_chunk_size=result.get("recommended_chunk_size", 0),
            structure_features=result.get("structure_features", [])
        )
    else:
        return DocumentAnalysisResponse(
            success=False,
            error=result.get("error", "分析失败")
        )


@router.get("/evaluate/ingest/cases")
async def list_ingest_test_cases():
    """获取文档导入测试用例列表"""
    service = get_evaluation_service()
    test_cases = service.get_ingest_test_cases()

    return [
        {
            "file_name": tc.file_name,
            "expected_chunks": tc.expected_chunks,
            "expected_categories": tc.expected_categories,
            "expected_keywords": tc.expected_keywords,
            "min_chunk_size": tc.min_chunk_size,
            "max_chunk_size": tc.max_chunk_size
        }
        for tc in test_cases
    ]


@router.get("/reports", response_model=List[ReportListItem])
async def list_reports():
    """获取评估报告列表"""
    service = get_evaluation_service()
    return service.list_reports()


@router.get("/reports/{filename}", response_model=EvaluationReportResponse)
async def get_report(filename: str):
    """获取指定评估报告"""
    service = get_evaluation_service()

    try:
        report = service.load_report(filename)
        return EvaluationReportResponse(
            timestamp=report.timestamp,
            total_questions=report.total_questions,
            successful_tests=report.successful_tests,
            failed_tests=report.failed_tests,
            retrieval_metrics={
                "recall": report.retrieval_metrics.recall,
                "precision": report.retrieval_metrics.precision,
                "f1_score": report.retrieval_metrics.f1_score,
                "hit_rate": report.retrieval_metrics.hit_rate,
                "mrr": report.retrieval_metrics.mrr,
                "ndcg": report.retrieval_metrics.ndcg
            },
            answer_metrics={
                "exact_match": report.answer_metrics.exact_match,
                "rouge_l": report.answer_metrics.rouge_l,
                "keyword_coverage": report.answer_metrics.keyword_coverage,
                "keyword_precision": report.answer_metrics.keyword_precision,
                "semantic_similarity": report.answer_metrics.semantic_similarity,
                "length_ratio": report.answer_metrics.length_ratio
            },
            overall_score=report.overall_score,
            results=[
                EvaluationResultResponse(
                    question=r.get("question", ""),
                    generated_answer=r.get("generated_answer", ""),
                    ground_truth=r.get("ground_truth", ""),
                    retrieval_metrics=r.get("retrieval_metrics", {}),
                    answer_metrics=r.get("answer_metrics", {}),
                    response_time=r.get("response_time", 0),
                    error=r.get("error", "")
                )
                for r in report.results
            ]
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="报告不存在")


@router.post("/evaluate/with-ai-qa", response_model=EvaluationReportResponse)
async def evaluate_with_ai_generated_qa(api_url: str = "http://localhost:8000"):
    """
    使用AI生成的已批准问答对进行评估

    加载通过人工核验的问答对，运行批量评估测试。
    """
    from app.services.evaluation import evaluate_with_approved_qa_pairs

    report = evaluate_with_approved_qa_pairs(api_url=api_url)

    if report.total_questions == 0:
        return EvaluationReportResponse(
            timestamp=datetime.now().isoformat(),
            total_questions=0,
            successful_tests=0,
            failed_tests=0,
            retrieval_metrics={
                "recall": 0.0, "precision": 0.0, "f1_score": 0.0,
                "hit_rate": 0.0, "mrr": 0.0, "ndcg": 0.0
            },
            answer_metrics={
                "exact_match": 0.0, "rouge_l": 0.0, "keyword_coverage": 0.0,
                "keyword_precision": 0.0, "semantic_similarity": 0.0, "length_ratio": 0.0
            },
            overall_score=0.0,
            results=[]
        )

    return EvaluationReportResponse(
        timestamp=report.timestamp,
        total_questions=report.total_questions,
        successful_tests=report.successful_tests,
        failed_tests=report.failed_tests,
        retrieval_metrics={
            "recall": report.retrieval_metrics.recall,
            "precision": report.retrieval_metrics.precision,
            "f1_score": report.retrieval_metrics.f1_score,
            "hit_rate": report.retrieval_metrics.hit_rate,
            "mrr": report.retrieval_metrics.mrr,
            "ndcg": report.retrieval_metrics.ndcg
        },
        answer_metrics={
            "exact_match": report.answer_metrics.exact_match,
            "rouge_l": report.answer_metrics.rouge_l,
            "keyword_coverage": report.answer_metrics.keyword_coverage,
            "keyword_precision": report.answer_metrics.keyword_precision,
            "semantic_similarity": report.answer_metrics.semantic_similarity,
            "length_ratio": report.answer_metrics.length_ratio
        },
        overall_score=report.overall_score,
        results=[
            EvaluationResultResponse(
                question=r.get("question", ""),
                generated_answer=r.get("generated_answer", ""),
                ground_truth=r.get("ground_truth", ""),
                retrieval_metrics=r.get("retrieval_metrics", {}),
                answer_metrics=r.get("answer_metrics", {}),
                response_time=r.get("response_time", 0),
                error=r.get("error", "")
            )
            for r in report.results
        ]
    )


# ============================================================================
# 自定义测试 API
# ============================================================================

class CustomFileEvalRequest(BaseModel):
    """自定义文件评估请求"""
    file_name: str
    category: str = "测试分类"
    regulation_type: str = "测试法规"
    region: Optional[str] = "全国"
    min_chunk_size: int = 50
    max_chunk_size: int = 800


class CustomFileEvalResponse(BaseModel):
    """自定义文件评估响应"""
    success: bool
    file_name: str
    document_id: Optional[int] = None
    chunk_count: int = 0
    document_analysis: Optional[dict] = None
    accuracy_score: Optional[dict] = None
    error: str = ""
    processing_time: float = 0.0


class CustomQuestionEvalRequest(BaseModel):
    """自定义问题评估请求"""
    question: str
    ground_truth_answer: Optional[str] = None
    expected_keywords: Optional[List[str]] = None


class CustomQuestionEvalResponse(BaseModel):
    """自定义问题评估响应"""
    success: bool
    question: str
    answer: str
    references: List[dict] = []
    retrieval_metrics: dict = {}
    answer_metrics: dict = {}
    ground_truth: str = ""
    response_time: float = 0.0
    error: str = ""


class BatchCustomEvalRequest(BaseModel):
    """批量自定义评估请求"""
    questions: List[CustomQuestionEvalRequest]


@router.post("/evaluate/custom/file", response_model=CustomFileEvalResponse)
async def evaluate_custom_file(
    file: UploadFile,
    category: str = "测试分类",
    regulation_type: str = "测试法规",
    region: Optional[str] = "全国",
    min_chunk_size: int = 50,
    max_chunk_size: int = 800,
    api_url: str = "http://localhost:8000"
):
    """
    自定义文件准确率评估

    上传文件并测试其导入准确率，包括：
    - 文档结构分析
    - 分块效果评估
    - 动态准确率计算
    """
    import time
    import tempfile
    import requests as http_requests

    start_time = time.time()
    result = CustomFileEvalResponse(
        success=False,
        file_name=file.filename or "unknown"
    )

    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "").suffix) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        # 读取文件内容用于分析
        with open(tmp_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(tmp_file_path, "r", encoding="gbk") as f:
                file_content = f.read()
        except Exception:
            os.unlink(tmp_file_path)
            result.error = "无法读取文件编码"
            return result
    except Exception as e:
        os.unlink(tmp_file_path)
        result.error = f"读取文件失败: {str(e)}"
        return result

    # 分析文档结构
    try:
        analysis_result = analyze_document_for_testing(tmp_file_path)
        result.document_analysis = analysis_result
    except Exception as e:
        result.error = f"文档分析失败: {str(e)}"
        result.processing_time = time.time() - start_time
        os.unlink(tmp_file_path)
        return result

    # 调用导入 API
    try:
        with open(tmp_file_path, "rb") as f:
            files = {"file": (file.filename, f)}
            data = {
                "category": category,
                "regulation_type": regulation_type,
                "region": region or None,
                "source": "自定义准确率测试",
                "min_chunk_size": min_chunk_size,
                "keep_separator": True,
                "batch_size": 100,
            }

            response = http_requests.post(
                f"{api_url}/api/knowledge/ingest",
                files=files,
                data=data,
                timeout=300
            )

        if response.status_code == 200:
            ingest_result = response.json()
            result.document_id = ingest_result.get("document_id")
            result.chunk_count = ingest_result.get("chunk_count", 0)

            # 计算准确率
            if analysis_result.get("success") and result.chunk_count > 0:
                structure = analysis_result.get("document_analysis", {})
                predicted_range = structure.get("predicted_chunk_range", {})

                # 使用 analysis_result 中的结构信息
                doc_structure_data = analysis_result.get("document_analysis", {}).get("structure_summary", {})
                predicted_min = doc_structure_data.get("predicted_chunk_count_range", "0-0")
                if "-" in predicted_min:
                    try:
                        parts = predicted_min.split("-")
                        expected_min = int(parts[0])
                        expected_max = int(parts[1])
                        expected = (expected_min + expected_max) // 2

                        # 计算准确率
                        if expected_min <= result.chunk_count <= expected_max:
                            range_size = expected_max - expected_min if expected_max > expected_min else 1
                            distance = abs(result.chunk_count - expected)
                            score = 1.0 - (distance / range_size) * 0.3
                        else:
                            if result.chunk_count < expected_min:
                                deficit = expected_min - result.chunk_count
                                score = max(0, 0.5 - deficit / expected_min * 0.5)
                            else:
                                surplus = result.chunk_count - expected_max
                                score = max(0, 0.5 - surplus / (expected_max * 2) * 0.5)

                        result.accuracy_score = {
                            "score": round(score, 4),
                            "actual_chunks": result.chunk_count,
                            "expected_range": f"{expected_min}-{expected_max}",
                            "expected_value": expected,
                            "assessment": "准确率评估完成" if score > 0.6 else "准确率偏低，建议调整分块参数"
                        }
                    except Exception:
                        result.accuracy_score = {
                            "score": 0.5,
                            "actual_chunks": result.chunk_count,
                            "expected_range": "无法确定",
                            "assessment": "无法计算准确率"
                        }

            result.success = True
        else:
            result.error = f"导入失败: {response.status_code} - {response.text}"

    except Exception as e:
        result.error = f"导入过程出错: {str(e)}"

    finally:
        os.unlink(tmp_file_path)

    result.processing_time = round(time.time() - start_time, 2)
    return result


@router.post("/evaluate/custom/question", response_model=CustomQuestionEvalResponse)
async def evaluate_custom_question(req: CustomQuestionEvalRequest):
    """
    自定义问题检索准确率评估

    输入自定义问题，评估检索和回答质量。
    """
    import time
    import requests as http_requests

    result = CustomQuestionEvalResponse(
        success=False,
        question=req.question
    )

    start_time = time.time()

    try:
        response = requests.post(
            f"{get_api_url()}/api/knowledge/answer",
            json={"question": req.question},
            timeout=180
        )

        if response.status_code == 200:
            data = response.json()
            result.answer = data.get("answer", "")
            result.references = data.get("references", [])

            # 计算检索指标
            if req.expected_keywords and req.expected_keywords:
                matched_keywords = [kw for kw in req.expected_keywords
                                   if kw.lower() in result.answer.lower()]
                result.answer_metrics = {
                    "keyword_coverage": len(matched_keywords) / len(req.expected_keywords) if req.expected_keywords else 0,
                    "matched_keywords": matched_keywords,
                    "total_keywords": len(req.expected_keywords)
                }

            # 计算语义相似度（如果提供了参考答案）
            if req.ground_truth_answer:
                from app.services.evaluation import MetricsCalculator
                semantic_sim = MetricsCalculator.calculate_semantic_similarity(
                    req.ground_truth_answer, result.answer
                )
                rouge_l = MetricsCalculator.calculate_rouge_l(
                    req.ground_truth_answer, result.answer
                )
                result.answer_metrics.update({
                    "semantic_similarity": semantic_sim,
                    "rouge_l": rouge_l,
                    "ground_truth": req.ground_truth_answer
                })

            # 检索指标
            if result.references:
                avg_similarity = sum(
                    r.get("similarity", 0) for r in result.references
                ) / len(result.references)
                result.retrieval_metrics = {
                    "avg_similarity": avg_similarity,
                    "reference_count": len(result.references),
                    "top_similarity": result.references[0].get("similarity", 0) if result.references else 0
                }

            result.ground_truth = req.ground_truth_answer or ""
            result.success = True
        else:
            result.error = f"问答失败: {response.status_code}"

    except Exception as e:
        result.error = f"处理出错: {str(e)}"

    result.response_time = round(time.time() - start_time, 2)
    return result


@router.post("/evaluate/custom/questions/batch", response_model=dict)
async def evaluate_custom_questions_batch(req: BatchCustomEvalRequest):
    """
    批量自定义问题评估

    一次提交多个问题，返回所有评估结果。
    """
    import time

    results = []
    total_start = time.time()

    for i, q in enumerate(req.questions):
        single_req = CustomQuestionEvalRequest(
            question=q.question,
            ground_truth_answer=q.ground_truth_answer,
            expected_keywords=q.expected_keywords
        )
        result = await evaluate_custom_question(single_req)
        results.append({
            "index": i,
            "question": result.question,
            "success": result.success,
            "answer": result.answer,
            "retrieval_metrics": result.retrieval_metrics,
            "answer_metrics": result.answer_metrics,
            "response_time": result.response_time,
            "error": result.error
        })

    # 计算总体统计
    successful = sum(1 for r in results if r["success"])
    avg_response_time = sum(r["response_time"] for r in results) / len(results) if results else 0

    return {
        "total_questions": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "avg_response_time": round(avg_response_time, 2),
        "total_time": round(time.time() - total_start, 2),
        "results": results
    }


# 辅助导入
from datetime import datetime


def get_api_url() -> str:
    """获取 API URL（用于内部调用）"""
    from app.core.config.settings import settings
    return getattr(settings, "API_URL", "http://localhost:8000")
