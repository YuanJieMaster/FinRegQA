"""
FinRegQA 知识库API路由
Knowledge base API endpoints
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.knowledge_app import answer_question, ingest_regulation_file, get_default_kb

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class QuestionRequest(BaseModel):
    """问答请求"""
    question: str
    region: Optional[str] = None


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
    faiss_index_size: int
    category_distribution: dict
    regulation_distribution: dict
    region_distribution: dict


@router.post("/answer", response_model=QuestionResponse)
async def api_answer(req: QuestionRequest):
    """知识库问答接口"""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        return answer_question(req.question, region=req.region)
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
