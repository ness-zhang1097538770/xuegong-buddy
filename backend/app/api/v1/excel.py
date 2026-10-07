"""Excel 台账 API：上传、批量生成、回写下载、信息提取。"""

import io, json, uuid, os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.excel import BatchGenerateResponse, ExtractRequest
from app.services.excel_service import read_excel, batch_generate_reviews, write_excel, extract_to_ledger

router = APIRouter(prefix="/excel", tags=["Excel台账"])

# 持久化目录
_RESULT_DIR = Path("data/results")
_RESULT_DIR.mkdir(parents=True, exist_ok=True)

# 简易内存缓存（上传数据仍用内存，只有生成结果持久化）
_upload_cache = {}  # task_id -> {"rows": [...], "user_id": int}


@router.post("/upload/read")
async def upload_and_read(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """上传 Excel 并读取前 10 行预览。"""
    content = await file.read()
    max_mb = 10
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件超过 {max_mb}MB")

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 格式")

    try:
        rows = read_excel(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取失败: {e}")

    task_id = uuid.uuid4().hex[:12]
    _upload_cache[task_id] = {"rows": rows, "user_id": user.id}

    return {
        "task_id": task_id,
        "headers": list(rows[0].keys()) if rows else [],
        "preview": rows[:10],
        "total_rows": len(rows),
    }


@router.post("/batch-generate", response_model=BatchGenerateResponse)
def batch_generate(
    max_rows: int = Query(default=50, ge=1, le=200),
    template_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量生成评语。使用最近一次上传的 Excel 数据。"""
    # 获取当前用户最近的上传
    user_uploads = {k: v for k, v in _upload_cache.items() if v["user_id"] == user.id}
    if not user_uploads:
        raise HTTPException(status_code=400, detail="请先上传 Excel 文件")

    task_id, cached = list(user_uploads.items())[-1]
    rows = cached["rows"][:max_rows]

    try:
        results = batch_generate_reviews(db, user.id, rows, template_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    headers = list(rows[0].keys()) if rows else []
    excel_bytes = write_excel(results, headers)

    result_id = uuid.uuid4().hex[:12]
    # 持久化到磁盘，服务重启不丢失
    file_path = _RESULT_DIR / f"{result_id}.xlsx"
    file_path.write_bytes(excel_bytes)

    return BatchGenerateResponse(
        task_id=result_id,
        row_count=len(results),
        download_url=f"/api/v1/excel/download/{result_id}",
        headers=headers + ["AI评语"],
        preview=results,
    )


@router.get("/download/{result_id}")
def download_result(
    result_id: str,
    user: User = Depends(get_current_user),
):
    """下载批量生成的 Excel 结果。持久化到磁盘，服务重启不丢失。"""
    # 安全检查：防止路径穿越
    if ".." in result_id or "/" in result_id:
        raise HTTPException(status_code=400, detail="无效的 result_id")

    file_path = _RESULT_DIR / f"{result_id}.xlsx"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="结果已过期，请重新生成")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"reviews_{result_id}.xlsx",
    )


@router.post("/extract")
def extract_info(
    req: ExtractRequest,
    user: User = Depends(get_current_user),
):
    """从自由文本提取信息到台账字段。"""
    try:
        result = extract_to_ledger(req.text, req.fields)
        return {"result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))