"""
FinRegQA 知识库API路由
Knowledge base API endpoints
"""
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from pydantic import Field

from app.services.knowledge_base import get_default_kb
from app.services.knowledge_app import ingest_regulation_file

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class QuestionRequest(BaseModel):
    """问答请求"""
    question: str
    region: Optional[str] = None
    mode: Literal["vector", "keyword", "hybrid"] = "hybrid"


class QuestionResponse(BaseModel):
    """问答响应"""
    answer: str
    references: list
    raw_results: list


class IngestResponse(BaseModel):
    """文档导入响应"""
    document_id: int
    file_name: str
    file_type: str
    chunk_count: int
    success: int
    failed: int


class StatsResponse(BaseModel):
    """统计信息响应"""
    document_count: int
    knowledge_count: int
    milvus_vector_count: int
    category_distribution: dict
    regulation_distribution: dict
    region_distribution: dict


# =============================================================================
# 知识库管理 API
# =============================================================================

class KnowledgeItem(BaseModel):
    """知识点数据模型"""
    id: int
    document_id: int
    content: str
    category: Optional[str] = None
    region: Optional[str] = None
    regulation_type: Optional[str] = None
    article_number: Optional[str] = None
    section_number: Optional[str] = None
    milvus_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    document_name: Optional[str] = None


class KnowledgeListResponse(BaseModel):
    """知识点列表响应"""
    items: List[KnowledgeItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentItem(BaseModel):
    """文档数据模型"""
    id: int
    name: str
    source: Optional[str] = None
    file_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    knowledge_count: int = 0


class UpdateKnowledgeRequest(BaseModel):
    """更新知识点请求"""
    content: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    regulation_type: Optional[str] = None
    article_number: Optional[str] = None
    section_number: Optional[str] = None


class DistinctValuesResponse(BaseModel):
    """不重复值响应"""
    values: List[str]


@router.get("/list", response_model=KnowledgeListResponse)
async def api_list_knowledge(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="分类筛选"),
    region: Optional[str] = Query(None, description="地区筛选"),
    regulation_type: Optional[str] = Query(None, description="监管类型筛选"),
    search: Optional[str] = Query(None, description="关键词搜索"),
):
    """获取知识点列表（支持分页和筛选）"""
    try:
        kb = get_default_kb()
        skip = (page - 1) * page_size
        items, total = kb.get_all_knowledge(
            skip=skip,
            limit=page_size,
            category=category,
            region=region,
            regulation_type=regulation_type,
            search_keyword=search,
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return KnowledgeListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识点列表失败: {str(e)}")


@router.get("/detail/{knowledge_id}", response_model=KnowledgeItem)
async def api_get_knowledge(knowledge_id: int):
    """获取单个知识点详情"""
    try:
        kb = get_default_kb()
        item = kb.get_knowledge_by_id(knowledge_id)
        if not item:
            raise HTTPException(status_code=404, detail="知识点不存在")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识点失败: {str(e)}")


@router.put("/update/{knowledge_id}")
async def api_update_knowledge(knowledge_id: int, req: UpdateKnowledgeRequest):
    """更新知识点"""
    try:
        kb = get_default_kb()
        success = kb.update_knowledge(
            knowledge_id=knowledge_id,
            content=req.content,
            category=req.category,
            region=req.region,
            regulation_type=req.regulation_type,
            article_number=req.article_number,
            section_number=req.section_number,
        )
        if not success:
            raise HTTPException(status_code=404, detail="知识点不存在或没有更新")
        return {"message": "更新成功", "knowledge_id": knowledge_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新知识点失败: {str(e)}")


@router.delete("/delete/{knowledge_id}")
async def api_delete_knowledge(knowledge_id: int):
    """删除知识点"""
    try:
        kb = get_default_kb()
        success = kb.delete_knowledge(knowledge_id)
        if not success:
            raise HTTPException(status_code=404, detail="知识点不存在")
        return {"message": "删除成功", "knowledge_id": knowledge_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除知识点失败: {str(e)}")


@router.get("/documents", response_model=List[DocumentItem])
async def api_list_documents():
    """获取文档列表"""
    try:
        kb = get_default_kb()
        documents = kb.get_all_documents()
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.delete("/documents/{document_id}")
async def api_delete_document(document_id: int):
    """删除文档及其所有知识点"""
    try:
        kb = get_default_kb()
        success = kb.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="文档不存在")
        return {"message": "删除成功", "document_id": document_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.get("/filter-values", response_model=DistinctValuesResponse)
async def api_get_filter_values(field: str = Query(..., description="字段名: category, region, regulation_type")):
    """获取筛选字段的不重复值"""
    try:
        kb = get_default_kb()
        values = kb.get_distinct_values(field)
        return DistinctValuesResponse(values=values)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取筛选值失败: {str(e)}")


@router.post("/answer", response_model=QuestionResponse)
async def api_answer(req: QuestionRequest):
    """知识库问答接口"""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        from app.services.knowledge_app import answer_question
        return answer_question(req.question, region=req.region, mode=req.mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@router.post("/ingest", response_model=IngestResponse)
async def api_ingest(
    file: UploadFile = File(...),
    category: str = Form(...),
    regulation_type: str = Form(...),
    region: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    min_chunk_size: int = Form(1),
    keep_separator: bool = Form(True),
    batch_size: int = Form(100),
):
    """知识库文档导入接口"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件不能为空")

    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 {allowed_extensions}",
        )

    temp_path = None
    try:
        # 保存临时文件
        temp_path = f"/tmp/{file.filename}"
        os.makedirs("/tmp", exist_ok=True)
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return ingest_regulation_file(
            file_path=temp_path,
            category=category,
            regulation_type=regulation_type,
            region=region,
            source=source,
            min_chunk_size=min_chunk_size,
            keep_separator=keep_separator,
            batch_size=batch_size,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档导入失败: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/stats", response_model=StatsResponse)
async def api_stats():
    """获取知识库统计信息"""
    try:
        kb = get_default_kb()
        return kb.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
