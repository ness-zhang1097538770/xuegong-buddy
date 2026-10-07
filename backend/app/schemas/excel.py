"""Excel 台账相关 schema。"""

from pydantic import BaseModel, Field


class BatchGenerateRequest(BaseModel):
    template_id: int | None = None
    max_rows: int = Field(default=50, ge=1, le=200)


class BatchGenerateResponse(BaseModel):
    task_id: str
    row_count: int
    download_url: str
    headers: list[str]
    preview: list[dict]


class ExtractRequest(BaseModel):
    text: str
    fields: list[str] = Field(min_length=1)