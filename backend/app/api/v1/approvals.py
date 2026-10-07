"""事务审批 API。"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.approval import Approval, TalkRecord
from app.models.todo import TodoItem
from app.models.operation_log import OperationLog

router = APIRouter(prefix="/approvals", tags=["事务审批"])

TYPE_LABELS = {"leave": "请假", "aid": "奖助贷", "discipline": "违纪", "other": "其他"}
TYPE_COLORS = {"leave": "blue", "aid": "green", "discipline": "red", "other": "gray"}


@router.get("")
def list_approvals(
    type: str | None = Query(None),
    status: str | None = Query("pending"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Approval).filter(Approval.handler_id == user.id)
    if type:
        query = query.filter(Approval.type == type)
    if status:
        query = query.filter(Approval.status == status)

    total = query.count()
    items = (
        query.order_by(Approval.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": a.id,
                "type": a.type,
                "type_label": TYPE_LABELS.get(a.type, a.type),
                "type_color": TYPE_COLORS.get(a.type, "gray"),
                "title": a.title,
                "applicant_name": a.applicant_name,
                "applicant_student_id": a.applicant_student_id,
                "content": a.content,
                "attachments": json.loads(a.attachments) if a.attachments else [],
                "status": a.status,
                "opinion": a.opinion,
                "risk_flags": json.loads(a.risk_flags) if a.risk_flags else [],
                "created_at": a.created_at.isoformat() if a.created_at else "",
            }
            for a in items
        ],
    }


@router.get("/{approval_id}")
def get_approval_detail(
    approval_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = db.query(Approval).filter(
        Approval.id == approval_id, Approval.handler_id == user.id
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="审批单不存在")

    # 查关联学生
    student_info = None
    if a.applicant_student_id:
        from app.models.student import Student
        s = db.query(Student).filter(
            Student.student_id == a.applicant_student_id,
            Student.owner_id == user.id,
        ).first()
        if s:
            student_info = {
                "name": s.name,
                "class_name": s.class_name,
                "gpa": s.gpa,
                "attendance": s.attendance,
                "tags": json.loads(s.tags) if s.tags else [],
                "risk_score": s.risk_score,
            }

    return {
        "id": a.id,
        "type": a.type,
        "type_label": TYPE_LABELS.get(a.type, a.type),
        "type_color": TYPE_COLORS.get(a.type, "gray"),
        "title": a.title,
        "applicant_name": a.applicant_name,
        "applicant_student_id": a.applicant_student_id,
        "content": a.content,
        "attachments": json.loads(a.attachments) if a.attachments else [],
        "status": a.status,
        "opinion": a.opinion,
        "risk_flags": json.loads(a.risk_flags) if a.risk_flags else [],
        "student": student_info,
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else "",
    }


@router.post("/{approval_id}/resolve")
def resolve_approval(
    approval_id: int,
    action: str = Query(..., regex="^(approve|reject|return)$"),
    opinion: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """处理审批：approve/reject/return。"""
    a = db.query(Approval).filter(
        Approval.id == approval_id, Approval.handler_id == user.id
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="审批单不存在")
    if a.status != "pending":
        raise HTTPException(status_code=400, detail="该审批已处理")

    if action == "reject" and not opinion:
        raise HTTPException(status_code=400, detail="驳回必须填写理由")

    a.status = {"approve": "approved", "reject": "rejected", "return": "returned"}[action]
    a.opinion = opinion
    a.resolved_at = datetime.now(timezone.utc)

    # 更新关联的待办
    todo = db.query(TodoItem).filter(
        TodoItem.source_type == "approval",
        TodoItem.source_id == approval_id,
        TodoItem.handler_id == user.id,
    ).first()
    if todo:
        todo.status = "done"
        todo.resolved_at = datetime.now(timezone.utc)

    # 操作日志
    log = OperationLog(
        user_id=user.id,
        action=f"approval_{action}",
        detail=f"{action} approval #{approval_id}: {a.title} | opinion: {opinion[:100]}",
    )
    db.add(log)
    db.commit()

    return {"message": "已处理", "status": a.status}


@router.post("/seed-demo")
def seed_demo_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """生成演示审批数据。"""
    demos = [
        {"type": "leave", "title": "李浩然 · 病假 3 天", "applicant_name": "李浩然",
         "applicant_student_id": "2023010108", "content": "感冒发烧，校医院建议居家休息三天，返校后补交病假条。家长已知情（父亲 139****0088）。",
         "risk_flags": json.dumps(["该生已有 3 门挂科预警", "近 30 天第 2 次请假"])},
        {"type": "aid", "title": "赵梦琪 · 国家助学金申请", "applicant_name": "赵梦琪",
         "applicant_student_id": "2023010122", "content": "家庭因父亲工伤丧失劳动力，母亲务农，两子女同时在读。村委与乡镇民政已出具证明。已认定特殊困难。",
         "risk_flags": json.dumps([])},
        {"type": "discipline", "title": "陈思远 · 夜不归宿", "applicant_name": "陈思远",
         "applicant_student_id": "2023010115", "content": "4月10日 23:40 查寝未归。称在校外兼职送外卖，未提供证明。当月第 2 次。",
         "risk_flags": json.dumps(["本月第 2 次违纪", "学生未提供有效证明"])},
        {"type": "leave", "title": "王雨桐 · 事假 1 天", "applicant_name": "王雨桐",
         "applicant_student_id": "2023010101", "content": "家中有事需回家一趟，已与家长确认。",
         "risk_flags": json.dumps(["该生心理测评高风险", "关注请假原因是否与情绪有关"])},
    ]
    for d in demos:
        a = Approval(**d, handler_id=user.id)
        db.add(a)
        db.flush()
        # 同步创建待办
        todo = TodoItem(
            source_type="approval", source_id=a.id, title=a.title,
            target_name=a.applicant_name, due_date="2026-09-21",
            priority=100 if a.type == "discipline" else 50, handler_id=user.id,
        )
        db.add(todo)
    db.commit()
    return {"message": f"已生成 {len(demos)} 条演示审批数据"}


# === 谈心谈话（注册为独立路由）===

talks_router = APIRouter(prefix="/talks", tags=["谈心谈话"])

@talks_router.get("")
def list_talks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    need_follow: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(TalkRecord).filter(TalkRecord.handler_id == user.id)
    if need_follow is not None:
        query = query.filter(TalkRecord.need_follow == need_follow, TalkRecord.follow_closed == 0)

    total = query.count()
    items = (
        query.order_by(TalkRecord.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": t.id,
                "student_name": t.student_name,
                "method": t.method,
                "topic": t.topic,
                "content": t.content[:200] if not user.role == "admin" or not t.is_sensitive else "[敏感内容已脱敏]",
                "conclusion": t.conclusion,
                "mood": t.mood,
                "need_follow": bool(t.need_follow),
                "follow_date": t.follow_date,
                "follow_closed": bool(t.follow_closed),
                "created_at": t.created_at.isoformat() if t.created_at else "",
            }
            for t in items
        ],
    }


@talks_router.post("")
def create_talk(
    student_name: str = Query(...),
    method: str = Query("面谈"),
    topic: str = Query(""),
    content: str = Query(""),
    conclusion: str = Query(""),
    mood: str = Query("平稳"),
    need_follow: int = Query(0),
    follow_date: str = Query(""),
    student_id_ref: str = Query(""),
    is_sensitive: int = Query(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建谈话记录——保存即归档。"""
    t = TalkRecord(
        student_name=student_name,
        student_id_ref=student_id_ref,
        method=method,
        topic=topic,
        content=content,
        conclusion=conclusion,
        mood=mood,
        need_follow=need_follow,
        follow_date=follow_date,
        is_sensitive=is_sensitive,
        handler_id=user.id,
    )
    db.add(t)
    db.flush()

    # 自动生成跟进待办
    if need_follow and follow_date:
        todo = TodoItem(
            source_type="talk",
            source_id=t.id,
            title=f"跟进谈话：{student_name}",
            target_name=student_name,
            due_date=follow_date,
            priority=80,
            handler_id=user.id,
        )
        db.add(todo)

    log = OperationLog(
        user_id=user.id,
        action="create_talk",
        detail=f"创建谈话记录: {student_name} | topic: {topic}",
    )
    db.add(log)
    db.commit()

    return {"message": "已保存并归档", "id": t.id}


class TalkDraftRequest(BaseModel):
    student_name: str = Field(min_length=1, max_length=50)
    method: str = "面谈"
    topic: str = ""
    key_points: str = Field(min_length=1)
    student_id_ref: str = ""


@talks_router.post("/draft")
def generate_talk_draft(
    req: TalkDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """基于本次要点 + 该生历史生成谈话记录草稿（AI 初稿，不自动保存）。"""
    from app.services.talk_service import generate_talk_draft as do_draft

    history = ""
    if req.student_id_ref:
        records = (
            db.query(TalkRecord)
            .filter(
                TalkRecord.handler_id == user.id,
                TalkRecord.student_id_ref == req.student_id_ref,
            )
            .order_by(TalkRecord.created_at.desc())
            .limit(5)
            .all()
        )
        if records:
            lines = []
            for r in records:
                lines.append(
                    f"- {r.created_at.strftime('%Y-%m-%d')} [{r.topic or '未归类'}] 结论：{r.conclusion or '无'}"
                )
            history = "\n".join(lines)

    try:
        draft = do_draft(
            student_name=req.student_name,
            method=req.method,
            topic=req.topic,
            key_points=req.key_points,
            history=history,
        )
    except RuntimeError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "MODEL_ERROR", "message": str(e)}},
        )

    return {"draft": draft, "is_draft": True}


@talks_router.post("/transcribe")
async def transcribe_talk_audio(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """导入录音文件 → 转文字（通义千问 Paraformer 实时版）。"""
    from fastapi.responses import JSONResponse
    import os
    import tempfile

    from app.services.asr_service import ALLOWED_AUDIO_EXTS, transcribe_audio as do_asr

    filename = file.filename or "audio"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "BAD_FORMAT", "message": "仅支持 wav/mp3/m4a/aac/ogg/flac/webm/amr 音频格式"}},
        )

    content = await file.read()
    if not content:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "EMPTY_FILE", "message": "音频文件为空"}},
        )
    if len(content) > 50 * 1024 * 1024:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "TOO_LARGE", "message": "音频文件不能超过 50MB"}},
        )

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.write(content)
    tmp.close()
    try:
        text = do_asr(tmp.name)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": {"code": "BAD_FORMAT", "message": str(e)}})
    except RuntimeError as e:
        return JSONResponse(status_code=502, content={"error": {"code": "ASR_ERROR", "message": str(e)}})
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    if not text:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "NO_SPEECH", "message": "未识别到语音内容，请换一段更清晰的录音"}},
        )

    return {"transcript": text}


@talks_router.post("/{talk_id}/close-follow")
def close_talk_follow(
    talk_id: int,
    conclusion: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """关闭跟进。"""
    t = db.query(TalkRecord).filter(
        TalkRecord.id == talk_id, TalkRecord.handler_id == user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="记录不存在")
    t.follow_closed = 1
    if conclusion:
        t.conclusion = t.conclusion + "\n\n[跟进闭环] " + conclusion

    # 关闭关联待办
    todo = db.query(TodoItem).filter(
        TodoItem.source_type == "talk",
        TodoItem.source_id == talk_id,
    ).first()
    if todo:
        todo.status = "done"
        todo.resolved_at = datetime.now(timezone.utc)

    db.commit()
    return {"message": "跟进已闭环"}