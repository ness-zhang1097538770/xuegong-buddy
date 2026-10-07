"""管理 API：邀请码管理、操作日志查看。"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_admin_user
from app.models.user import User
from app.models.invite_code import InviteCode
from app.models.operation_log import OperationLog
from app.schemas.admin import (
    InviteCodesCreate, InviteCodesResponse,
    InviteCodeItem, InviteCodeListResponse,
    OperationLogItem, OperationLogListResponse,
)
from app.services.auth_service import generate_invite_codes

router = APIRouter(prefix="/admin", tags=["管理"])


@router.post("/invite-codes", status_code=status.HTTP_201_CREATED, response_model=InviteCodesResponse)
def create_invite_codes(
    req: InviteCodesCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    codes = generate_invite_codes(db, req.count)
    return InviteCodesResponse(codes=codes)


@router.get("/invite-codes", response_model=InviteCodeListResponse)
def list_invite_codes(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    codes = db.query(InviteCode).order_by(InviteCode.created_at.desc()).all()
    return InviteCodeListResponse(
        codes=[InviteCodeItem.model_validate(c) for c in codes]
    )


@router.get("/logs", response_model=OperationLogListResponse)
def list_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    total = db.query(OperationLog).count()
    logs = (
        db.query(OperationLog)
        .order_by(OperationLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return OperationLogListResponse(
        logs=[OperationLogItem.model_validate(l) for l in logs],
        total=total,
    )