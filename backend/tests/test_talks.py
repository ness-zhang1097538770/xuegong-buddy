"""谈心谈话测试：录入即归档、自动跟进待办、AI 初稿（mock）。"""

from app.models.user import User
from app.models.approval import TalkRecord
from app.models.todo import TodoItem


def test_create_talk_archives_and_creates_todo(client, user_token, db_session):
    headers = {"Authorization": f"Bearer {user_token}"}
    resp = client.post(
        "/api/v1/talks",
        params={
            "student_name": "张三",
            "student_id_ref": "2023001",
            "method": "面谈",
            "topic": "学业压力",
            "content": "近期成绩下滑",
            "conclusion": "需要持续关注",
            "need_follow": 1,
            "follow_date": "2026-10-01",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    talk_id = resp.json()["id"]

    # 已归档
    talk = db_session.query(TalkRecord).filter(TalkRecord.id == talk_id).first()
    assert talk is not None
    assert talk.student_id_ref == "2023001"

    # 自动生成跟进待办
    todo = (
        db_session.query(TodoItem)
        .filter(TodoItem.source_type == "talk", TodoItem.source_id == talk_id)
        .first()
    )
    assert todo is not None
    assert todo.status == "pending"
    assert todo.due_date == "2026-10-01"


def test_close_follow(client, user_token, db_session):
    headers = {"Authorization": f"Bearer {user_token}"}
    talk_id = client.post(
        "/api/v1/talks",
        params={
            "student_name": "张三",
            "student_id_ref": "2023001",
            "need_follow": 1,
            "follow_date": "2026-10-01",
            "content": "谈话",
            "conclusion": "跟进",
        },
        headers=headers,
    ).json()["id"]

    resp = client.post(
        f"/api/v1/talks/{talk_id}/close-follow",
        params={"conclusion": "已再次面谈，情绪稳定"},
        headers=headers,
    )
    assert resp.status_code == 200

    talk = db_session.query(TalkRecord).filter(TalkRecord.id == talk_id).first()
    assert talk.follow_closed == 1
    todo = (
        db_session.query(TodoItem)
        .filter(TodoItem.source_type == "talk", TodoItem.source_id == talk_id)
        .first()
    )
    assert todo.status == "done"


def test_talk_draft(monkeypatch, client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    def fake_draft(student_name, method, topic, key_points, history=""):
        return f"【对象】{student_name}\n【类型】{topic}\n【处置建议】多关注"

    monkeypatch.setattr("app.services.talk_service.generate_talk_draft", fake_draft)
    resp = client.post(
        "/api/v1/talks/draft",
        json={"student_name": "张三", "topic": "学业压力", "key_points": "近期成绩下滑"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert "张三" in resp.json()["draft"]
    assert resp.json()["is_draft"] is True
