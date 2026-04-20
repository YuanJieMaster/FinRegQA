"""
FinRegQA 知识库模型
Knowledge base models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Document(Base):
    """文档表"""
    __tablename__ = "document"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    source = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    knowledge_items = relationship("Knowledge", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_document_name", "name"),
    )


class Knowledge(Base):
    """知识条目表"""
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("document.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    regulation_type = Column(String(100), nullable=True)
    article_number = Column(String(50), nullable=True)
    section_number = Column(String(50), nullable=True)
    milvus_id = Column(BigInteger, nullable=True)  # Milvus 主键ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    document = relationship("Document", back_populates="knowledge_items")
    logs = relationship("Log", back_populates="knowledge")

    __table_args__ = (
        Index("idx_knowledge_document_id", "document_id"),
        Index("idx_knowledge_category", "category"),
        Index("idx_knowledge_region", "region"),
        Index("idx_knowledge_article", "article_number"),
    )


class Log(Base):
    """操作日志表"""
    __tablename__ = "log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    operation = Column(String(50), nullable=False)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=True)
    message = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    knowledge = relationship("Knowledge", back_populates="logs")

    __table_args__ = (
        Index("idx_log_operation", "operation"),
        Index("idx_log_status", "status"),
        Index("idx_log_created", "created_at"),
    )
