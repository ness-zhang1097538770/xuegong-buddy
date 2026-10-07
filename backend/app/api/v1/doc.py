"""文稿生成 API：模板管理、文稿生成、Word 导出、参考文件上传。"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.doc import (
    TemplateResponse, TemplateDetailResponse, TemplateCreate, TemplateUpdate,
    DocGenerateRequest, DocGenerateResponse, DocTaskResponse, RefUploadResponse,
)
from app.services.template_service import (
    get_templates, get_template, create_template, update_template, delete_template,
)
from app.services.doc_service import generate_doc, export_docx, get_user_tasks, store_ref_files

router = APIRouter(prefix="/doc", tags=["文稿"])


# === 模板管理 ===

@router.get("/templates", response_model=dict)
def list_templates(
    category: str | None = Query(None),
    style: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tmpls = get_templates(db, category, style)
    return {
        "templates": [TemplateResponse.model_validate(t) for t in tmpls],
        "total": len(tmpls),
    }


@router.get("/templates/{tmpl_id}", response_model=TemplateDetailResponse)
def get_template_detail(
    tmpl_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tmpl = get_template(db, tmpl_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return TemplateDetailResponse.model_validate(tmpl)


@router.post("/templates", status_code=201, response_model=TemplateDetailResponse)
def create_new_template(
    req: TemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tmpl = create_template(db, user.id, req.model_dump())
    return TemplateDetailResponse.model_validate(tmpl)


@router.put("/templates/{tmpl_id}", response_model=TemplateDetailResponse)
def update_existing_template(
    tmpl_id: int,
    req: TemplateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        tmpl = update_template(db, user.id, tmpl_id, req.model_dump(exclude_none=True))
        return TemplateDetailResponse.model_validate(tmpl)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/templates/{tmpl_id}")
def delete_existing_template(
    tmpl_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        delete_template(db, user.id, tmpl_id)
        return {"message": "已删除"}
    except ValueError as e:
        msg = str(e)
        if "不存在" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# === 文稿生成 ===

# === 参考文件上传 ===

@router.post("/upload-reference", response_model=RefUploadResponse)
async def upload_reference_files(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
):
    """上传参考文件（最多 5 个，PDF/Word/TXT），返回 ref_id 列表。"""
    file_data = []
    for f in files:
        content = await f.read()
        file_data.append((f.filename or "unknown", content))

    try:
        results = store_ref_files(user.id, file_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RefUploadResponse(
        ref_ids=[r["ref_id"] for r in results],
        filenames=[r["filename"] for r in results],
        total_chars=sum(r["chars"] for r in results),
    )


# === 文稿生成 ===

@router.post("/generate", status_code=201, response_model=DocGenerateResponse)
def generate_document(
    req: DocGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        task = generate_doc(
            db, user.id, req.template_id, req.variables, req.style,
            reference_ids=req.reference_ids if req.reference_ids else None,
        )
        return DocGenerateResponse(
            task_id=task.id,
            template_name=task.template_name,
            status=task.status,
            content=task.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{task_id}")
def download_docx(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.doc_task import DocTask
    task = db.query(DocTask).filter(DocTask.id == task_id, DocTask.user_id == user.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "done":
        raise HTTPException(status_code=400, detail="文稿尚未生成完成")

    docx_bytes = export_docx(task.content, task.template_name)
    # 文件名用英文+数字，避免中文 header 编码问题
    safe_name = f"doc_{task_id}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"},
    )


@router.get("/tasks", response_model=list[DocTaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tasks = get_user_tasks(db, user.id)
    return [DocTaskResponse.model_validate(t) for t in tasks]