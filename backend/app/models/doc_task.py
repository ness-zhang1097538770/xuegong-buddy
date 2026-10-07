"""文稿生成任务模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.models.base import Base


class DocTask(Base):
    __tablename__ = "doc_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    template_name = Column(String(100), nullable=False)
    style = Column(String(30), default="formal")
    variables_json = Column(Text, default="{}")  # 填写的变量值
    content = Column(Text, default="")  # 生成的文稿内容
    status = Column(String(20), default="pending")  # pending/generating/done/failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))