"""专家智能体 API。"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.expert import ExpertSession
from app.services import expert_service
from app.services import expert_rag

router = APIRouter(prefix="/experts", tags=["专家智能体"])


class ChatRequest(BaseModel):
    expert_id: str
    session_id: int | None = None
    messages: list[dict] = []


# === 专家列表 ===

@router.get("")
def get_experts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """返回专家广场数据：分类 + 专家列表 + 用户最近会话。"""
    experts = expert_service.list_experts()
    categories = expert_service.get_categories()

    # 用户最近会话
    recent = (
        db.query(ExpertSession)
        .filter(ExpertSession.user_id == user.id)
        .order_by(ExpertSession.updated_at.desc())
        .limit(10)
        .all()
    )
    sessions = [
        {"id": s.id, "expert_id": s.expert_id, "title": s.title, "updated_at": str(s.updated_at)}
        for s in recent
    ]

    return {"categories": categories, "experts": experts, "sessions": sessions}


# === 会话管理 ===

@router.get("/sessions")
def get_sessions(
    expert_id: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户会话列表，可按专家筛选。"""
    q = db.query(ExpertSession).filter(ExpertSession.user_id == user.id)
    if expert_id:
        q = q.filter(ExpertSession.expert_id == expert_id)
    sessions = q.order_by(ExpertSession.updated_at.desc()).limit(50).all()
    return {
        "sessions": [
            {
                "id": s.id,
                "expert_id": s.expert_id,
                "title": s.title,
                "messages": s.messages,
                "created_at": str(s.created_at),
                "updated_at": str(s.updated_at),
            }
            for s in sessions
        ]
    }


@router.post("/sessions")
def create_session(
    expert_id: str = Query(...),
    title: str = Query("新会话"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新建专家会话。"""
    # 校验 expert 存在
    experts = expert_service.list_experts()
    if not any(e["id"] == expert_id for e in experts):
        raise HTTPException(status_code=404, detail=f"专家 '{expert_id}' 不存在")

    session = ExpertSession(
        user_id=user.id,
        expert_id=expert_id,
        title=title,
        messages=[],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "expert_id": session.expert_id, "title": session.title}


# === 对话（SSE 流式） ===

@router.post("/chat")
async def expert_chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """与指定专家对话，SSE 流式返回。"""
    # 校验专家存在
    experts = expert_service.list_experts()
    expert = next((e for e in experts if e["id"] == body.expert_id), None)
    if not expert:
        raise HTTPException(status_code=404, detail=f"专家 '{body.expert_id}' 不存在")

    # 处理或创建会话
    session_id = body.session_id
    if session_id:
        session = (
            db.query(ExpertSession)
            .filter(ExpertSession.id == session_id, ExpertSession.user_id == user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        session = ExpertSession(
            user_id=user.id,
            expert_id=body.expert_id,
            title="新会话",
            messages=[],
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    # 取最后一条用户消息
    user_msg = ""
    if body.messages:
        user_msg = body.messages[-1].get("content", "")
    if not user_msg:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # === RAG 检索（失败静默降级）===
    history = session.messages or []
    last_answer = ""
    if history:
        last_answer = history[-1].get("content", "") or ""

    chunks, rag_meta = expert_rag.retrieve(db, user.id, body.expert_id, user_msg, last_answer)
    rag_block = expert_rag.build_context(chunks) if chunks else None
    rag_no_hit = bool(rag_meta.get("attempted")) and not chunks

    # 构建完整消息列表
    llm_messages, config = expert_service.build_messages(
        body.expert_id, history, user_msg,
        rag_block=rag_block, rag_no_hit=rag_no_hit,
    )
    temperature = expert_service.get_temperature(body.expert_id)

    async def event_generator():
        full = ""
        async for chunk in expert_service.chat_stream(
            body.expert_id, llm_messages, temperature=temperature
        ):
            if chunk.startswith("data: "):
                try:
                    d = json.loads(chunk[6:])
                    if "token" in d:
                        full += d["token"]
                except json.JSONDecodeError:
                    pass
            yield chunk

        # 保存到会话
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": full})
        session.messages = history
        # 自动生成标题（用第一条用户消息前 30 字）
        if session.title == "新会话" and user_msg:
            session.title = user_msg[:30] + ("…" if len(user_msg) > 30 else "")
        db.commit()

        # done 事件带上引用（老前端不解析也不受影响）
        yield (
            "event: done\ndata: "
            + json.dumps({
                "content": full,
                "session_id": session_id,
                "citations": expert_rag.to_citations(chunks),
            }, ensure_ascii=False)
            + "\n\n"
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# === 删除会话 ===

@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = (
        db.query(ExpertSession)
        .filter(ExpertSession.id == session_id, ExpertSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(session)
    db.commit()
    return {"message": "已删除"}