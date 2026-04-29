"""
AI问答对生成API路由
提供AI辅助生成问答对和人工核验的REST API接口
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import os

from app.services.qa_generator import (
    get_qa_generator,
    GeneratedQAPair,
    UNIVERSAL_QA_TEMPLATES,
)
from app.services.document_analyzer import DocumentStructureAnalyzer

router = APIRouter(prefix="/qa-generation", tags=["问答对生成"])


# ============================================================================
# 请求/响应模型
# ============================================================================

class DocumentQAGenerationRequest(BaseModel):
    """文档问答对生成请求"""
    document_content: str                    # 文档内容
    document_name: str = "未命名文档"         # 文档名称
    count: int = 10                          # 生成数量
    custom_instructions: str = ""            # 自定义指令


class UniversalQAGenerationRequest(BaseModel):
    """通用问答对生成请求"""
    count: int = 10                          # 生成数量
    category: str = ""                       # 类别筛选
    difficulty: str = ""                     # 难度筛选


class QAReviewRequest(BaseModel):
    """问答对核验请求"""
    index: int                               # 问答对索引
    approved: bool                           # 是否通过
    reviewer_notes: str = ""                 # 核验备注


class BatchReviewRequest(BaseModel):
    """批量核验请求"""
    reviews: List[dict]                      # [{"index": 0, "approved": true, "notes": ""}]
    batch_name: str = ""                     # 批次名称


class GeneratedQAResponse(BaseModel):
    """生成的问答对响应"""
    success: bool
    total_generated: int = 0
    pending_review_file: str = ""
    message: str = ""
    qa_pairs: List[dict] = []


class QAReviewResponse(BaseModel):
    """核验响应"""
    success: bool
    question: str = ""
    review_status: str = ""
    message: str = ""


class BatchReviewResponse(BaseModel):
    """批量核验响应"""
    success: bool
    approved: List[str] = []
    rejected: List[str] = []
    failed: List[dict] = []
    message: str = ""


class QAStatisticsResponse(BaseModel):
    """统计信息响应"""
    pending_review: int
    approved: int
    difficulty_distribution: dict
    type_distribution: dict
    total: int


class QAPendingReviewResponse(BaseModel):
    """待核验问答对响应"""
    success: bool
    batch_name: str = ""
    total_count: int = 0
    qa_pairs: List[dict] = []


class UniversalTemplateResponse(BaseModel):
    """通用模板响应"""
    template: str
    answer_guidance: str
    question_type: str
    difficulty: str
    applicable_regulations: List[str]
    keywords: List[str]


# ============================================================================
# API 端点
# ============================================================================

@router.get("/", response_model=dict)
async def get_qa_generation_info():
    """获取问答对生成功能信息"""
    generator = get_qa_generator()
    stats = generator.get_statistics()
    templates = UNIVERSAL_QA_TEMPLATES

    return {
        "name": "AI辅助问答对生成系统",
        "version": "1.0.0",
        "description": "使用AI为金融监管文档生成问答对，支持人工核验",
        "statistics": stats,
        "available_templates_count": len(templates),
        "features": [
            "针对文档生成专门问答对",
            "生成通用金融监管问答对",
            "多难度级别支持(easy/medium/hard)",
            "多种问题类型(definition/numeric/procedure/principle/comparison/requirement)",
            "人工核验工作流",
            "导出为评估格式"
        ]
    }


@router.post("/generate/document", response_model=GeneratedQAResponse)
async def generate_qa_for_document(req: DocumentQAGenerationRequest):
    """
    针对文档生成问答对

    使用AI分析文档内容，生成针对性的问答对。
    生成的问答对需要人工核验后才能用于评估。

    - **document_content**: 文档内容（支持TXT格式）
    - **document_name**: 文档名称
    - **count**: 生成数量（默认10个）
    - **custom_instructions**: 自定义指令（可选）
    """
    if not req.document_content.strip():
        raise HTTPException(status_code=400, detail="文档内容不能为空")

    generator = get_qa_generator()

    try:
        result = generator.generate_and_save(
            document_content=req.document_content,
            document_name=req.document_name,
            count=req.count,
            is_universal=False,
            batch_name=f"doc_{req.document_name.replace('.', '_')}"
        )

        if result.get("success"):
            return GeneratedQAResponse(
                success=True,
                total_generated=result.get("total_generated", 0),
                pending_review_file=result.get("pending_review_file", ""),
                message="问答对生成成功，请进行人工核验",
                qa_pairs=result.get("qa_pairs", [])
            )
        else:
            return GeneratedQAResponse(
                success=False,
                message=result.get("error", "生成失败")
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate/document/file", response_model=GeneratedQAResponse)
async def generate_qa_for_document_file(
    file: UploadFile = File(...),
    count: int = 10,
    custom_instructions: str = ""
):
    """
    上传文档文件生成问答对

    支持上传TXT文件，AI将分析文档内容并生成问答对。
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="仅支持TXT格式文件")

    # 读取文件内容
    content = await file.read()
    try:
        document_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            document_content = content.decode('gbk')
        except:
            raise HTTPException(status_code=400, detail="文件编码不支持，请使用UTF-8或GBK编码")

    generator = get_qa_generator()

    try:
        result = generator.generate_and_save(
            document_content=document_content,
            document_name=file.filename,
            count=count,
            is_universal=False,
            batch_name=f"file_{file.filename.replace('.', '_').replace(' ', '_')}"
        )

        if result.get("success"):
            return GeneratedQAResponse(
                success=True,
                total_generated=result.get("total_generated", 0),
                pending_review_file=result.get("pending_review_file", ""),
                message=f"文档 {file.filename} 问答对生成成功，请进行人工核验",
                qa_pairs=result.get("qa_pairs", [])
            )
        else:
            return GeneratedQAResponse(
                success=False,
                message=result.get("error", "生成失败")
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate/universal", response_model=GeneratedQAResponse)
async def generate_universal_qa(req: UniversalQAGenerationRequest):
    """
    生成通用金融监管问答对

    基于预定义的通用模板，生成覆盖常见金融监管场景的问答对。
    适用于系统首次部署或定期补充测试用例。

    - **count**: 生成数量（默认10个）
    - **category**: 类别筛选（可选），如"风险管理"、"合规管理"
    - **difficulty**: 难度筛选（可选），可选值: easy, medium, hard
    """
    generator = get_qa_generator()

    try:
        result = generator.generate_and_save(
            count=req.count,
            is_universal=True,
            batch_name="universal"
        )

        if result.get("success"):
            return GeneratedQAResponse(
                success=True,
                total_generated=result.get("total_generated", 0),
                pending_review_file=result.get("pending_review_file", ""),
                message="通用问答对生成成功，请进行人工核验",
                qa_pairs=result.get("qa_pairs", [])
            )
        else:
            return GeneratedQAResponse(
                success=False,
                message=result.get("error", "生成失败")
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.get("/templates", response_model=List[UniversalTemplateResponse])
async def list_universal_templates():
    """
    获取通用问答模板列表

    查看可用的通用金融监管问答模板及其说明。
    """
    templates = UNIVERSAL_QA_TEMPLATES

    return [
        UniversalTemplateResponse(
            template=t.template,
            answer_guidance=t.answer_guidance,
            question_type=t.question_type,
            difficulty=t.difficulty,
            applicable_regulations=t.applicable_regulations,
            keywords=t.keywords
        )
        for t in templates
    ]


@router.get("/pending", response_model=QAPendingReviewResponse)
async def get_pending_review(batch_name: str = ""):
    """
    获取待核验的问答对

    查看已生成但尚未人工核验的问答对列表。

    - **batch_name**: 批次名称（可选，不指定则获取最新批次）
    """
    generator = get_qa_generator()
    qa_pairs = generator.load_pending_review(batch_name)

    if not qa_pairs:
        raise HTTPException(status_code=404, detail="没有待核验的问答对")

    # 获取批次名
    from app.services.qa_generator import QA_PENDING_REVIEW_DIR
    from pathlib import Path
    files = sorted(QA_PENDING_REVIEW_DIR.glob("qa_batch_*.json"), reverse=True)
    current_batch = batch_name
    if not current_batch and files:
        current_batch = files[0].stem.replace("qa_batch_", "")

    return QAPendingReviewResponse(
        success=True,
        batch_name=current_batch,
        total_count=len(qa_pairs),
        qa_pairs=[asdict(qa) for qa in qa_pairs]
    )


@router.post("/review", response_model=QAReviewResponse)
async def review_qa_pair(req: QAReviewRequest, batch_name: str = ""):
    """
    核验单个问答对

    对生成的问答对进行人工核验，标记为通过或拒绝。

    - **index**: 问答对索引
    - **approved**: 是否通过（true=通过，false=拒绝）
    - **reviewer_notes**: 核验备注（可选）
    - **batch_name**: 批次名称（可选）
    """
    generator = get_qa_generator()

    # 如果未指定批次，获取最新批次
    if not batch_name:
        from app.services.qa_generator import QA_PENDING_REVIEW_DIR
        files = sorted(QA_PENDING_REVIEW_DIR.glob("qa_batch_*.json"), reverse=True)
        if files:
            batch_name = files[0].stem.replace("qa_batch_", "")

    result = generator.review_qa_pair(
        index=req.index,
        approved=req.approved,
        reviewer_notes=req.reviewer_notes,
        batch_name=batch_name
    )

    if result.get("success"):
        return QAReviewResponse(
            success=True,
            question=result.get("question", ""),
            review_status=result.get("review_status", ""),
            message=f"问答对已标记为 {result.get('review_status', '')}"
        )
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "核验失败"))


@router.post("/review/batch", response_model=BatchReviewResponse)
async def batch_review_qa(req: BatchReviewRequest, batch_name: str = ""):
    """
    批量核验问答对

    一次性对多个问答对进行核验。

    - **reviews**: 核验列表，每项包含 index, approved, notes
    - **batch_name**: 批次名称（可选）
    """
    generator = get_qa_generator()

    # 如果未指定批次，获取最新批次
    if not batch_name:
        from app.services.qa_generator import QA_PENDING_REVIEW_DIR
        files = sorted(QA_PENDING_REVIEW_DIR.glob("qa_batch_*.json"), reverse=True)
        if files:
            batch_name = files[0].stem.replace("qa_batch_", "")

    result = generator.batch_review(
        reviews=req.reviews,
        batch_name=batch_name
    )

    return BatchReviewResponse(
        success=True,
        approved=result.get("approved", []),
        rejected=result.get("rejected", []),
        failed=result.get("failed", []),
        message=f"批量核验完成：通过 {len(result.get('approved', []))}，拒绝 {len(result.get('rejected', []))}"
    )


@router.get("/approved", response_model=dict)
async def get_approved_qa_pairs():
    """
    获取已批准的问答对

    查看通过人工核验的问答对列表。
    这些问答对可直接用于评估测试。
    """
    generator = get_qa_generator()
    approved_pairs = generator.get_approved_qa_pairs()

    return {
        "success": True,
        "total_count": len(approved_pairs),
        "qa_pairs": [
            {
                "question": qa.question,
                "ground_truth_answer": qa.ground_truth_answer,
                "keywords": qa.keywords,
                "difficulty": qa.difficulty,
                "question_type": qa.question_type,
                "source_document": qa.source_document,
                "reviewer_notes": qa.reviewer_notes
            }
            for qa in approved_pairs
        ]
    }


@router.get("/statistics", response_model=QAStatisticsResponse)
async def get_statistics():
    """
    获取问答对统计信息

    查看问答对的生成、核验、分类统计。
    """
    generator = get_qa_generator()
    stats = generator.get_statistics()

    return QAStatisticsResponse(**stats)


@router.post("/export", response_model=dict)
async def export_qa_pairs(file_path: str = ""):
    """
    导出问答对

    将已批准的问答对导出为评估格式。

    - **file_path**: 导出文件路径（可选，默认导出到评估目录）
    """
    generator = get_qa_generator()

    if not file_path:
        from app.services.qa_generator import QA_APPROVED_DIR
        file_path = str(QA_APPROVED_DIR / "export" / f"evaluation_qa_{datetime.now().strftime('%Y%m%d')}.json")

    try:
        eval_format = generator.export_to_evaluation_format(file_path)

        return {
            "success": True,
            "exported_count": len(eval_format),
            "file_path": file_path,
            "message": "导出成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/analyze/generate", response_model=dict)
async def analyze_and_generate(
    file: UploadFile = File(...),
    count: int = 10
):
    """
    分析文档结构并生成问答对

    一站式完成文档分析和问答对生成。

    - **file**: 上传的文档文件
    - **count**: 生成数量
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="仅支持TXT格式文件")

    # 读取文件
    content = await file.read()
    try:
        document_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            document_content = content.decode('gbk')
        except:
            raise HTTPException(status_code=400, detail="文件编码不支持")

    # 分析文档结构
    analyzer = DocumentStructureAnalyzer()
    doc_structure = analyzer.analyze(document_content, file.filename)

    # 生成问答对
    generator = get_qa_generator()

    try:
        result = generator.generate_and_save(
            document_content=document_content,
            document_name=file.filename,
            count=count,
            is_universal=False,
            batch_name=f"analyze_{file.filename.replace('.', '_').replace(' ', '_')}"
        )

        return {
            "success": True,
            "document_analysis": {
                "document_name": doc_structure.document_name,
                "document_type": doc_structure.document_type.value,
                "complexity": doc_structure.complexity.value,
                "total_articles": doc_structure.total_articles,
                "total_chapters": doc_structure.total_chapters,
                "predicted_chunk_range": {
                    "min": doc_structure.predicted_chunk_count_min,
                    "max": doc_structure.predicted_chunk_count_max,
                    "expected": doc_structure.predicted_chunk_count_expected
                },
                "structure_features": doc_structure.structure_features
            },
            "qa_generation": {
                "total_generated": result.get("total_generated", 0),
                "pending_review_file": result.get("pending_review_file", ""),
                "qa_pairs": result.get("qa_pairs", [])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


# 辅助函数
from datetime import datetime


def asdict(qa: GeneratedQAPair) -> dict:
    """将GeneratedQAPair转换为字典"""
    return {
        "question": qa.question,
        "ground_truth_answer": qa.ground_truth_answer,
        "question_type": qa.question_type,
        "difficulty": qa.difficulty,
        "keywords": qa.keywords,
        "source_context": qa.source_context,
        "source_document": qa.source_document,
        "generation_reason": qa.generation_reason,
        "ai_confidence": qa.ai_confidence,
        "needs_review": qa.needs_review,
        "reviewer_notes": qa.reviewer_notes,
        "review_status": qa.review_status,
        "created_at": qa.created_at
    }
