"""
FinRegQA 应用配置
Application Settings
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # 忽略额外字段
    )
    
    # 应用基础配置
    APP_NAME: str = "FinRegQA - 金融制度知识问答系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API前缀
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # MySQL数据库配置
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "finregqa")
    
    @property
    def DATABASE_URL(self) -> str:
        """获取数据库连接URL"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """获取异步数据库连接URL"""
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    # JWT配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7天
    
    # QQ邮箱SMTP配置
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.qq.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")  # 你的QQ邮箱
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # QQ邮箱授权码
    SMTP_USE_TLS: bool = True
    
    # 邮箱配置
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", SMTP_USER)
    EMAIL_FROM_NAME: str = "FinRegQA系统"
    
    # JWT重置密码配置
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_SECRET_KEY: str = os.getenv("PASSWORD_RESET_SECRET_KEY", "password-reset-secret-key")
    
    # 会话管理
    MAX_SESSIONS_PER_USER: int = 3
    
    # PostgreSQL配置（知识库）
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "financial_kb")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    # FAISS配置
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "./data/faiss_index")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    EMBEDDING_DIM: int = 512


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
