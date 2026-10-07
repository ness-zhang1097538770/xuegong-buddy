"""宿舍与查寝模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.base import Base


class Dorm(Base):
    __tablename__ = "dorms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building = Column(String(50), nullable=False, index=True)  # 楼栋名称原文
    floor = Column(String(20), default="")  # 楼层，如 1F / 2F
    room = Column(String(20), nullable=False)  # 房号原文
    members = Column(String, default="[]")  # JSON，成员学号列表
    status = Column(String(20), default="unchecked")  # unchecked / normal / abnormal
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DormCheck(Base):
    __tablename__ = "dorm_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dorm_id = Column(Integer, ForeignKey("dorms.id"), nullable=False)
    date = Column(String(20), nullable=False)  # 检查日期 YYYY-MM-DD
    status = Column(String(20), nullable=False)  # normal / abnormal
    abnormal_type = Column(String(50), default="")  # 异常类型：夜不归宿/违规电器/拒查/卫生
    note = Column(String, default="")
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))