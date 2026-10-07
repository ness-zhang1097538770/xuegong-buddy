"""审批模型。"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.models.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)  # leave / aid / discipline / other
    title = Column(String(200), nullable=False)
    applicant_name = Column(String(50), nullable=False)  # 申请人姓名
    applicant_student_id = Column(String(30), default="")  # 申请人学号
    content = Column(Text, default="")  # 申请内容
    attachments = Column(String, default="[]")  # JSON 附件列表
    status = Column(String(20), default="pending")  # pending / approved / rejected / returned
    opinion = Column(Text, default="")  # 审批意见
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    risk_flags = Column(String, default="[]")  # JSON 风险标记
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


class TalkRecord(Base):
    __tablename__ = "talk_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_name = Column(String(50), nullable=False)
    student_id_ref = Column(String(30), default="")  # 关联学生学号
    method = Column(String(20), default="面谈")  # 面谈 / 线上 / 电话 / 宿舍走访
    topic = Column(String(50), default="")  # 学业压力 / 心理疏导 / 生活困难 / 就业指导 / 日常关心
    content = Column(Text, default="")
    conclusion = Column(Text, default="")
    mood = Column(String(20), default="平稳")  # 低落 / 平稳 / 积极 / 激动
    need_follow = Column(Integer, default=0)  # 是否需要跟进 0/1
    follow_date = Column(String(20), default="")  # 下次跟进日期
    follow_closed = Column(Integer, default=0)  # 跟进是否已闭环
    is_sensitive = Column(Integer, default=0)  # 是否含心理/危机敏感内容
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))