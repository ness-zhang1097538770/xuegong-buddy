"""知识库 API：上传文档、列表、删除、流式问答、对话历史。"""

import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.schemas.kb import (
    DocumentResponse, DocumentListResponse,
    ConversationResponse, MessageResponse,
)
from app.services.kb_service import upload_document, delete_document, get_user_documents, ensure_user_kb
from app.services.chat_service import stream_chat

router = APIRouter(prefix="/kb", tags=["知识库"])


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
async def upload(
    file: UploadFile = File(...),
    category: str = Form("综合"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 读取文件内容
    content = await file.read()
    try:
        doc = upload_document(db, user.id, content, file.filename or "untitled", category=category)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    docs = get_user_documents(db, user.id, status_filter)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.delete("/documents/{doc_id}")
def remove_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        delete_document(db, user.id, doc_id)
        return {"message": "已删除"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除")


@router.get("/chat")
async def chat(
    q: str = Query(..., description="提问内容"),
    conv_id: int | None = Query(None, description="对话 ID，不传则创建新对话"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """SSE 流式知识库问答。"""
    async def event_generator():
        async for event in stream_chat(db, user.id, q, conv_id):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kb = ensure_user_kb(db, user.id)
    convs = db.query(Conversation).filter(
        Conversation.user_id == user.id,
        Conversation.kb_id == kb.id,
    ).order_by(Conversation.created_at.desc()).all()
    return [ConversationResponse.model_validate(c) for c in convs]


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == user.id
    ).first()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    msgs = db.query(Message).filter(
        Message.conv_id == conv_id
    ).order_by(Message.created_at).all()
    return [MessageResponse.model_validate(m) for m in msgs]