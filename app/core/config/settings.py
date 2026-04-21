"""
Application settings.
"""

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "FinRegQA - 金融制度知识问答系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list = ["*"]

    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "finregqa")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.qq.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = True

    EMAIL_FROM: str = os.getenv("EMAIL_FROM", SMTP_USER)
    EMAIL_FROM_NAME: str = "FinRegQA系统"

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_SECRET_KEY: str = os.getenv(
        "PASSWORD_RESET_SECRET_KEY",
        "password-reset-secret-key",
    )

    MAX_SESSIONS_PER_USER: int = 3

    FINREGQA_DB_HOST: str = os.getenv("FINREGQA_DB_HOST", MYSQL_HOST)
    FINREGQA_DB_PORT: int = int(os.getenv("FINREGQA_DB_PORT", str(MYSQL_PORT)))
    FINREGQA_DB_NAME: str = os.getenv("FINREGQA_DB_NAME", MYSQL_DATABASE)
    FINREGQA_DB_USER: str = os.getenv("FINREGQA_DB_USER", MYSQL_USER)
    FINREGQA_DB_PASSWORD: str = os.getenv("FINREGQA_DB_PASSWORD", MYSQL_PASSWORD)

    MILVUS_URI: str = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
    MILVUS_TOKEN: str = os.getenv("MILVUS_TOKEN", "")
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "financial_knowledge")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    EMBEDDING_DIM: int = 512

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        """Accept common boolean-like environment values."""
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        raise ValueError(f"Unsupported DEBUG value: {value}")


@lru_cache()
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()


settings = get_settings()
