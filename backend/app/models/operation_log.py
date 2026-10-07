"""操作日志模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.models.base import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)  # upload_doc / ask_question / login / register
    detail = Column(Text, nullable=True)  # 操作摘要，不含敏感内容
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))