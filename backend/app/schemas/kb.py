"""知识库相关 schema。"""

from datetime import datetime
from pydantic import BaseModel, field_serializer


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    category: str = "综合"
    status: str
    chunk_count: int
    size_bytes: int
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return v.isoformat()

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class ConversationResponse(BaseModel):
    id: int
    kb_id: int
    title: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return v.isoformat()

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    citations: str | None = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return v.isoformat()

    model_config = {"from_attributes": True}


class ChatCitation(BaseModel):
    doc_name: str
    chunk_text: str


class ChatDoneData(BaseModel):
    conv_id: int
    message_id: int
    content: str
    citations: list[ChatCitation]