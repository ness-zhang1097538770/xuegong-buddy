"""文稿生成相关 schema。"""

from datetime import datetime
from pydantic import BaseModel, Field, field_serializer


class TemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    description: str = ""
    style: str = "formal"
    variables: str = "[]"  # JSON string
    is_builtin: bool = False
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()

    model_config = {"from_attributes": True}


class TemplateDetailResponse(TemplateResponse):
    system_prompt: str = ""
    user_prompt_template: str = ""


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    description: str = ""
    style: str = "formal"
    system_prompt: str = ""
    user_prompt_template: str = Field(min_length=1)
    variables: str = "[]"


class TemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    style: str | None = None
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    variables: str | None = None


class DocGenerateRequest(BaseModel):
    template_id: int
    variables: dict = {}
    style: str | None = None  # 覆盖模板默认文风
    reference_ids: list[str] = []  # 参考文件 ID 列表


class DocGenerateResponse(BaseModel):
    task_id: int
    template_name: str
    status: str
    content: str = ""


class DocTaskResponse(BaseModel):
    id: int
    template_name: str
    style: str
    status: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, v: datetime) -> str:
        return v.isoformat()

    model_config = {"from_attributes": True}


class RefUploadResponse(BaseModel):
    ref_ids: list[str]
    filenames: list[str]
    total_chars: int