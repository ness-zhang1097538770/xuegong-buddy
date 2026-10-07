"""文稿模板模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from app.models.base import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, default="")
    style = Column(String(30), default="formal")  # formal/soft/brief
    system_prompt = Column(Text, default="")
    user_prompt_template = Column(Text, nullable=False)
    variables = Column(Text, default="[]")  # JSON array
    is_builtin = Column(Boolean, default=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))