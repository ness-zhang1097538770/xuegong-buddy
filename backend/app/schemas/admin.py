"""管理相关 schema。"""

from datetime import datetime
from pydantic import BaseModel, Field, field_serializer


class InviteCodesCreate(BaseModel):
    count: int = Field(ge=1, le=50, default=5)


class InviteCodesResponse(BaseModel):
    codes: list[str]


class InviteCodeItem(BaseModel):
    id: int
    code: str
    is_used: bool
    used_by_email: str | None = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return v.isoformat()

    model_config = {"from_attributes": True}


class InviteCodeListResponse(BaseModel):
    codes: list[InviteCodeItem]


class OperationLogItem(BaseModel):
    id: int
    user_id: int
    action: str
    detail: str | None = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return v.isoformat()

    model_config = {"from_attributes": True}


class OperationLogListResponse(BaseModel):
    logs: list[OperationLogItem]
    total: int