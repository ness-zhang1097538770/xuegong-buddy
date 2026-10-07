"""工作台首页 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.student import Student
from app.models.todo import TodoItem
from app.models.approval import Approval

router = APIRouter(prefix="/home", tags=["工作台"])


@router.get("/summary")
def get_home_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回副驾首页 Hero 区 4 个数字 + 待办清单。"""
    # 4 个 KPI 数字：待我审批、待跟进谈话、今日异常宿舍、学业预警人数
    pending_approvals = db.query(Approval).filter(
        Approval.handler_id == user.id,
        Approval.status == "pending",
    ).count()

    pending_talks = db.query(TodoItem).filter(
        TodoItem.handler_id == user.id,
        TodoItem.source_type == "talk",
        TodoItem.status == "pending",
    ).count()

    abnormal_dorms = db.query(TodoItem).filter(
        TodoItem.handler_id == user.id,
        TodoItem.source_type == "dorm",
        TodoItem.status == "pending",
    ).count()

    # 学业预警 = GPA 低于 2.0（且已录入）或风险分 > 0
    from sqlalchemy import or_
    risk_students = db.query(Student).filter(
        Student.owner_id == user.id,
        or_(
            Student.risk_score > 0,
            (Student.gpa > 0) & (Student.gpa < 2.0),
        ),
    ).count()

    # 待办清单
    todos = (
        db.query(TodoItem)
        .filter(TodoItem.handler_id == user.id, TodoItem.status == "pending")
        .order_by(TodoItem.priority.desc(), TodoItem.due_date.asc())
        .limit(50)
        .all()
    )

    return {
        "stats": {
            "pending_approvals": pending_approvals,
            "pending_talks": pending_talks,
            "abnormal_dorms": abnormal_dorms,
            "risk_students": risk_students,
        },
        "todos": [
            {
                "id": t.id,
                "source_type": t.source_type,
                "title": t.title,
                "target_name": t.target_name,
                "due_date": t.due_date,
                "priority": t.priority,
                "status": t.status,
            }
            for t in todos
        ],
        "user_info": {
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/todos/{todo_id}/resolve")
def resolve_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记待办为已完成。"""
    todo = (
        db.query(TodoItem)
        .filter(TodoItem.id == todo_id, TodoItem.handler_id == user.id)
        .first()
    )
    if not todo:
        return {"error": {"code": "NOT_FOUND", "message": "待办不存在"}}

    from datetime import datetime, timezone

    todo.status = "done"
    todo.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "已处理", "todo_id": todo_id}


@router.post("/todos")
def create_todo(
    title: str = Query(..., min_length=1, max_length=200),
    due_date: str = Query(""),
    note: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新增一条手动提醒（提醒录）。"""
    t = TodoItem(
        source_type="reminder",
        source_id=0,
        title=title.strip(),
        target_name=note.strip(),
        due_date=due_date.strip(),
        priority=50,
        status="pending",
        handler_id=user.id,
    )
    db.add(t)
    db.commit()
    return {"message": "已新增", "id": t.id}