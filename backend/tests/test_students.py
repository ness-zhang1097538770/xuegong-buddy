"""学生档案（一人一页）测试：导入、列表、叙事时间轴、交接包。"""

import io
import openpyxl
from app.models.user import User
from app.models.student import Student


def _seed_student(db_session, user, student_id="2023001", name="张三"):
    s = Student(
        student_id=student_id,
        name=name,
        class_name="计算机2301",
        grade="2023级",
        gpa=3.2,
        attendance=95.0,
        owner_id=user.id,
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


def test_import_students(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["学号", "姓名", "班级", "年级", "GPA", "出勤率"])
    ws.append(["2023001", "张三", "计算机2301", "2023级", 3.2, 95])
    ws.append(["2023002", "李四", "计算机2301", "2023级", 2.8, 92])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = client.post(
        "/api/v1/students/import",
        files={
            "file": (
                "students.xlsx",
                buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported"] == 2


def test_list_students(client, user_token, db_session):
    user = db_session.query(User).filter(User.email == "counselor@school.edu.cn").first()
    _seed_student(db_session, user)
    headers = {"Authorization": f"Bearer {user_token}"}
    resp = client.get("/api/v1/students", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_student_detail_narrative(client, user_token, db_session):
    user = db_session.query(User).filter(User.email == "counselor@school.edu.cn").first()
    s = _seed_student(db_session, user)
    headers = {"Authorization": f"Bearer {user_token}"}

    # 建一条谈话记录
    client.post(
        "/api/v1/talks",
        params={
            "student_name": "张三",
            "student_id_ref": s.student_id,
            "topic": "学业压力",
            "content": "成绩下滑",
            "conclusion": "持续关注",
        },
        headers=headers,
    )

    resp = client.get(f"/api/v1/students/{s.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "张三"
    assert len(data["talk_records"]) == 1
    assert data["talk_records"][0]["topic"] == "学业压力"


def test_handover_download(client, user_token, db_session):
    user = db_session.query(User).filter(User.email == "counselor@school.edu.cn").first()
    s = _seed_student(db_session, user)
    headers = {"Authorization": f"Bearer {user_token}"}

    resp = client.get(f"/api/v1/students/{s.id}/handover", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )
