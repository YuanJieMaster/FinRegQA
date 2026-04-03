"""
金融知识库 FastAPI 服务
Financial Knowledge Base FastAPI Service

提供 RESTful API 接口：
- POST /api/answer：问答
- POST /api/ingest：导入文档
- GET /api/stats：统计信息
"""

import os
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from dotenv import load_dotenv
from example_usage import answer_question, ingest_regulation_file, get_default_kb, close_default_kb

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="金融监管知识库 API",
    description="基于 PostgreSQL + FAISS + LLM 的金融监管问答系统",
    version="1.0.0",
)

# 允许跨域请求（前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 数据模型
# ============================================================================


class QuestionRequest(BaseModel):
    """问答请求"""
    question: str


class QuestionResponse(BaseModel):
    """问答响应"""
    answer: str
    references: list
    raw_results: list


class IngestRequest(BaseModel):
    """文档导入请求"""
    category: str
    regulation_type: str
    source: Optional[str] = None
    min_chunk_size: int = 1
    keep_separator: bool = True
    batch_size: int = 100


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


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    message: str


# ============================================================================
# 健康检查
# ============================================================================


@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    健康检查端点
    """
    try:
        kb = get_default_kb()
        stats = kb.get_statistics()
        return {
            "status": "healthy",
            "message": f"知识库正常，包含 {stats['knowledge_count']} 个知识点",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"知识库连接失败: {str(e)}")


# ============================================================================
# 问答接口
# ============================================================================


@app.post("/api/answer", response_model=QuestionResponse)
def api_answer(req: QuestionRequest):
    """
    问答接口

    Args:
        req: 包含 question 字段的请求

    Returns:
        answer: 生成的答案
        references: 检索到的法规依据
        raw_results: 原始检索结果

    Example:
        POST /api/answer
        {
            "question": "商业银行资本充足率最低要求是什么？"
        }
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        result = answer_question(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


# ============================================================================
# 文档导入接口
# ============================================================================


@app.post("/api/ingest", response_model=IngestResponse)
async def api_ingest(
    file: UploadFile = File(...),
    category: str = Form(...),
    regulation_type: str = Form(...),
    source: Optional[str] = Form(None),
    min_chunk_size: int = Form(1),
    keep_separator: bool = Form(True),
    batch_size: int = Form(100),
):
    """
    文档导入接口（支持 PDF/DOCX/TXT）

    Args:
        file: 上传的文件
        category: 分类（如"风险管理"、"资本管理"）
        regulation_type: 监管类型（如"商业银行监管"）
        source: 文档来源（可选）
        min_chunk_size: 最小分块大小
        keep_separator: 是否保留分隔符
        batch_size: 批处理大小

    Returns:
        document_id: 文档 ID
        file_name: 文件名
        file_type: 文件类型
        chunk_count: 分块数量
        success: 成功导入数
        failed: 失败数

    Example:
        POST /api/ingest
        Content-Type: multipart/form-data

        file: <binary>
        category: 风险管理
        regulation_type: 商业银行监管
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件不能为空")

    # 检查文件类型
    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 {allowed_extensions}",
        )

    try:
        # 保存临时文件
        temp_path = f"/tmp/{file.filename}"
        os.makedirs("/tmp", exist_ok=True)
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 导入文档
        result = ingest_regulation_file(
            file_path=temp_path,
            category=category,
            regulation_type=regulation_type,
            source=source,
            min_chunk_size=min_chunk_size,
            keep_separator=keep_separator,
            batch_size=batch_size,
        )

        # 删除临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档导入失败: {str(e)}")


# ============================================================================
# 统计信息接口
# ============================================================================


@app.get("/api/stats", response_model=StatsResponse)
def api_stats():
    """
    获取知识库统计信息

    Returns:
        document_count: 文档数
        knowledge_count: 知识点数
        faiss_index_size: FAISS 索引大小
        category_distribution: 分类分布
        regulation_distribution: 监管类型分布

    Example:
        GET /api/stats
    """
    try:
        kb = get_default_kb()
        stats = kb.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


# ============================================================================
# 启动和关闭事件
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("=" * 80)
    print("金融知识库 FastAPI 服务启动")
    print("=" * 80)
    print(f"LLM 模型: {os.getenv('FINREGQA_LLM_MODEL', 'gpt-4o-mini')}")
    print(f"LLM Base URL: {os.getenv('FINREGQA_LLM_BASE_URL', '(默认 OpenAI)')}")
    print(f"数据库: {os.getenv('FINREGQA_DB_HOST', 'localhost')}:{os.getenv('FINREGQA_DB_PORT', '5432')}")
    print("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print("关闭知识库连接...")
    close_default_kb()


# ============================================================================
# 根路由
# ============================================================================


@app.get("/")
def root():
    """根路由，返回 API 文档链接"""
    return {
        "message": "金融监管知识库 API",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": {
            "health": "GET /health",
            "answer": "POST /api/answer",
            "ingest": "POST /api/ingest",
            "stats": "GET /api/stats",
        },
    }


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    host = os.getenv("FINREGQA_API_HOST", "0.0.0.0")
    port = int(os.getenv("FINREGQA_API_PORT", "8000"))
    reload = os.getenv("FINREGQA_API_RELOAD", "false").lower() == "true"

    print(f"启动服务: http://{host}:{port}")
    print(f"API 文档: http://{host}:{port}/docs")

    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
    )
