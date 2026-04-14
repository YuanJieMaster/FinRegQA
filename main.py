"""
FinRegQA FastAPI 应用入口
Main application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import auth, users, knowledge
from app.services.knowledge_app import close_default_kb


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    FinRegQA - 金融制度知识问答系统后端API
    
    ## 功能模块
    
    * **用户认证** - 用户注册、登录、登出、会话管理
    * **用户管理** - 个人信息查看与修改
    * **JWT认证** - 安全令牌认证
    * **邮箱验证** - QQ邮箱发送验证邮件
    
    ## 认证方式
    
    本API使用OAuth2密码模式认证。
    
    1. 注册用户: POST /api/v1/auth/register
    2. 登录获取令牌: POST /api/v1/auth/login
    3. 使用access_token访问受保护的接口
    
    在请求头中添加: `Authorization: Bearer <access_token>`
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "error_code": "INTERNAL_ERROR"}
    )


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()
    print(f"✅ {settings.APP_NAME} 已启动")
    print(f"📚 API文档: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行清理"""
    print(f"🔴 {settings.APP_NAME} 已关闭")
    close_default_kb()


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.APP_VERSION}


# 注册API路由
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge.router, prefix="/api")


@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
