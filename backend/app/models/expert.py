"""专家会话与智能体模型。"""

import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class ExpertSession(Base):
    """专家会话——记录用户与某个专家的对话历史。"""

    __tablename__ = "expert_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expert_id = Column(String(64), nullable=False, index=True)
    title = Column(String(128), nullable=False, default="新会话")
    messages = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", backref="expert_sessions")