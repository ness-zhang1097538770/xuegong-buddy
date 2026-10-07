"""学生模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.models.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(30), nullable=False, index=True)  # 学号
    name = Column(String(50), nullable=False)
    class_name = Column(String(100), nullable=False, default="")  # 班级
    grade = Column(String(20), default="")  # 年级，如 2023 级
    gender = Column(String(10), default="")
    phone = Column(String(20), default="")
    dorm_building = Column(String(50), default="")  # 楼栋
    dorm_room = Column(String(20), default="")  # 房号
    gpa = Column(Float, default=0.0)  # GPA，满量程 4.0
    attendance = Column(Float, default=100.0)  # 出勤率，满量程 100%
    tags = Column(String, default="[]")  # JSON 数组标签
    risk_score = Column(Integer, default=0)  # 风险分，越高越危险
    status = Column(String(20), default="active")  # active / graduated / transferred
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 所属辅导员
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))