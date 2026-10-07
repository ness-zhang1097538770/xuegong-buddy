"""文档模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf / docx / txt
    category = Column(String(30), default="综合", nullable=False)  # 类目：资助/学风/心理/处分/综合
    status = Column(String(30), default="uploaded", nullable=False)  # uploaded/chunking/vectorizing/done/failed
    chunk_count = Column(Integer, default=0)
    size_bytes = Column(Integer, default=0)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))