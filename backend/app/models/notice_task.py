"""通知变材料任务模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.models.base import Base


class NoticeTask(Base):
    __tablename__ = "notice_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    theme = Column(String(200), nullable=False)  # 班会/通知主题
    event_time = Column(String(100), default="")  # 时间
    place = Column(String(100), default="")  # 地点
    audience = Column(String(100), default="")  # 对象
    status = Column(String(20), default="generating")  # generating / done / failed
    result_json = Column(Text, default="{}")  # 六件套结果 JSON
    error_msg = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
