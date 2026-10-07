"""副驾首页测试：4 个数字统计。"""

from app.models.user import User
from app.models.approval import Approval
from app.models.todo import TodoItem
from app.models.student import Student


def test_home_summary_four_stats(client, user_token, db_session):
    user = db_session.query(User).filter(User.email == "counselor@school.edu.cn").first()

    # 1 条待审批（另一条已办结不计）
    db_session.add(Approval(type="leave", title="请假", applicant_name="张三", handler_id=user.id, status="pending"))
    db_session.add(Approval(type="aid", title="助学金", applicant_name="李四", handler_id=user.id, status="approved"))
    # 1 条待跟进谈话
    db_session.add(TodoItem(source_type="talk", title="跟进谈话", handler_id=user.id, status="pending"))
    # 1 条异常宿舍
    db_session.add(TodoItem(source_type="dorm", title="查寝异常", handler_id=user.id, status="pending"))
    # 1 名学业预警（GPA 低于 2.0）
    db_session.add(Student(student_id="001", name="王五", owner_id=user.id, risk_score=0, gpa=1.8))
    db_session.commit()

    headers = {"Authorization": f"Bearer {user_token}"}
    resp = client.get("/api/v1/home/summary", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["pending_approvals"] == 1
    assert stats["pending_talks"] == 1
    assert stats["abnormal_dorms"] == 1
    assert stats["risk_students"] == 1


def test_home_resolve_todo(client, user_token, db_session):
    from app.models.user import User
    user = db_session.query(User).filter(User.email == "counselor@school.edu.cn").first()
    todo = TodoItem(source_type="talk", title="跟进", handler_id=user.id, status="pending")
    db_session.add(todo)
    db_session.commit()

    headers = {"Authorization": f"Bearer {user_token}"}
    resp = client.post(f"/api/v1/home/todos/{todo.id}/resolve", headers=headers)
    assert resp.status_code == 200
    db_session.refresh(todo)
    assert todo.status == "done"
