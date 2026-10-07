"""通知变材料 API：一句话生成六件套材料。"""

import json
from datetime import datetime
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.notice_task import NoticeTask
from app.services import notice_service

router = APIRouter(prefix="/notice", tags=["通知变材料"])


def _err(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


class NoticeGenerateRequest(BaseModel):
    theme: str = Field(min_length=1, max_length=200)
    event_time: str = ""
    place: str = ""
    audience: str = ""


class NoticeTaskResponse(BaseModel):
    id: int
    theme: str
    event_time: str
    place: str
    audience: str
    status: str
    result: dict = {}
    created_at: str


def _to_response(task: NoticeTask, include_result: bool = True) -> NoticeTaskResponse:
    return NoticeTaskResponse(
        id=task.id,
        theme=task.theme,
        event_time=task.event_time,
        place=task.place,
        audience=task.audience,
        status=task.status,
        result=notice_service.get_task_result(task) if include_result else {},
        created_at=task.created_at.isoformat() if task.created_at else "",
    )


@router.post("/generate", status_code=201, response_model=NoticeTaskResponse)
def generate(
    req: NoticeGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """一句话 → 六件套材料（同步生成）。"""
    try:
        task = notice_service.generate_notice_package(
            db, user.id, req.theme, req.event_time, req.place, req.audience
        )
        return _to_response(task)
    except RuntimeError as e:
        return _err(500, "MODEL_ERROR", str(e))


@router.get("/tasks", response_model=list[NoticeTaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tasks = (
        db.query(NoticeTask)
        .filter(NoticeTask.user_id == user.id)
        .order_by(NoticeTask.created_at.desc())
        .limit(20)
        .all()
    )
    return [_to_response(t, include_result=False) for t in tasks]


@router.get("/{task_id}", response_model=NoticeTaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.query(NoticeTask).filter(
        NoticeTask.id == task_id, NoticeTask.user_id == user.id
    ).first()
    if not task:
        return _err(404, "NOT_FOUND", "任务不存在")
    return _to_response(task)


@router.get("/download/{task_id}")
def download_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.query(NoticeTask).filter(
        NoticeTask.id == task_id, NoticeTask.user_id == user.id
    ).first()
    if not task:
        return _err(404, "NOT_FOUND", "任务不存在")
    if task.status != "done":
        return _err(400, "NOT_READY", "材料尚未生成完成")

    docx_bytes = notice_service.export_notice_docx(task)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=notice_{task_id}.docx"},
    )


@router.post("/signin/import")
async def import_signin(
    file: UploadFile = File(...),
    theme: str = Query(""),
    event_time: str = Query(""),
    place: str = Query(""),
    user: User = Depends(get_current_user),
):
    """导入班级学生名单 Excel → 生成带真实姓名的签到表。"""
    if not file.filename or not (
        file.filename.endswith(".xlsx") or file.filename.endswith(".xls")
    ):
        return _err(400, "BAD_FORMAT", "仅支持 .xlsx / .xls 格式")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return _err(400, "TOO_LARGE", "文件不能超过 10MB")

    try:
        students = notice_service.parse_student_excel(content)
    except ValueError as e:
        return _err(400, "PARSE_ERROR", str(e))
    except Exception:
        return _err(400, "PARSE_ERROR", "Excel 解析失败，请检查文件格式")

    if not students:
        return _err(400, "EMPTY", "未识别到学生，请确认 Excel 含「姓名」列且有数据")

    sheet = notice_service.build_signin_sheet_with_students(
        students, theme, event_time, place
    )
    return {"signin_sheet": sheet, "students": students, "count": len(students)}


class SigninExportRequest(BaseModel):
    theme: str = ""
    event_time: str = ""
    place: str = ""
    students: list[dict] = []


@router.post("/signin/export")
def export_signin(
    req: SigninExportRequest,
    user: User = Depends(get_current_user),
):
    """导出带真实姓名的签到表 Word。"""
    if not req.students:
        return _err(400, "EMPTY", "学生名单为空")
    docx_bytes = notice_service.export_signin_docx(
        req.students, req.theme, req.event_time, req.place
    )
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=signin_sheet.docx"},
    )
