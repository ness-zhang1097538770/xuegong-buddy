"""待办事项模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.base import Base


class TodoItem(Base):
    __tablename__ = "todo_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(30), nullable=False)  # approval / talk / dorm / material
    source_id = Column(Integer, default=0)  # 关联源记录 ID
    title = Column(String(200), nullable=False)
    target_name = Column(String(100), default="")  # 学生姓名或对象
    due_date = Column(String(30), default="")  # 到期日
    priority = Column(Integer, default=0)  # 优先级，逾期 > 今日 > 未来
    status = Column(String(20), default="pending")  # pending / done / cancelled
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))