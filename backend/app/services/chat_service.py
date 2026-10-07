"""知识库问答服务：检索 → 拼接 Prompt → 流式生成。"""

import json
from collections.abc import AsyncGenerator

from dashscope import Generation
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import KnowledgeBase
from app.models.operation_log import OperationLog
from app.services.embedding_service import get_embedding
from app.services.kb_service import _get_or_create_collection, ensure_user_kb
from app.services.prompts.rag_qa import RAG_QA_SYSTEM, RAG_QA_USER_TEMPLATE


def _search_chunks(kb_id: int, query: str, top_k: int = 5) -> list[dict]:
    """向量检索相关文档片段。"""
    collection = _get_or_create_collection(kb_id)
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    if not results or not results["documents"] or not results["documents"][0]:
        return []

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "doc_name": results["metadatas"][0][i].get("doc_name", "未知文档"),
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })
    return chunks


def _build_documents_str(chunks: list[dict]) -> str:
    """构建 Prompt 中的参考文档部分。"""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] 来源: {chunk['doc_name']}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def get_or_create_conversation(db: Session, user_id: int, kb_id: int,
                               title: str = "新对话") -> Conversation:
    conv = db.query(Conversation).filter(
        Conversation.id == kb_id,  # placeholder
    ).first()
    # 简单逻辑：查已有，没有则创建
    # 实际由外部传入 conv_id
    conv = Conversation(user_id=user_id, kb_id=kb_id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


async def stream_chat(
    db: Session,
    user_id: int,
    question: str,
    conv_id: int | None = None,
) -> AsyncGenerator[dict, None]:
    """流式 RAG 问答。返回 dict 事件：{\"event\": \"chunk\"/\"done\"/\"error\", \"data\": ...}"""
    try:
        # 确保知识库存在
        kb = ensure_user_kb(db, user_id)

        # 检查知识库是否有向量化完成的文档
        from app.models.document import Document
        doc_count = db.query(Document).filter(
            Document.kb_id == kb.id,
            Document.status == "done",
        ).count()
        if doc_count == 0:
            yield {"event": "error", "data": {"error": {"code": "KB_EMPTY", "message": "知识库为空，请先上传文档"}}}
            return

        # 检索
        chunks = _search_chunks(kb.id, question, top_k=settings.rag_top_k)
        if not chunks:
            yield {"event": "error", "data": {"error": {"code": "NO_MATCH", "message": "未找到相关文档内容"}}}
            return

        # 构建 Prompt
        documents_str = _build_documents_str(chunks)
        user_prompt = RAG_QA_USER_TEMPLATE.format(documents=documents_str, question=question)

        # 构建 citation 数据
        citations = [
            {"doc_name": c["doc_name"], "chunk_text": c["text"][:300]}
            for c in chunks
        ]

        # 创建/获取对话
        if conv_id:
            conv = db.query(Conversation).filter(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
            ).first()
            if conv is None:
                yield {"event": "error", "data": {"error": {"code": "CONV_NOT_FOUND", "message": "对话不存在"}}}
                return
        else:
            title = question[:30] + "..." if len(question) > 30 else question
            conv = Conversation(user_id=user_id, kb_id=kb.id, title=title)
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # 保存用户问题
        user_msg = Message(conv_id=conv.id, role="user", content=question)
        db.add(user_msg)
        db.commit()

        # 调试信息直接输出到终端，不通过 yield
        print(f"\n[RAG DEBUG] 检索到 {len(chunks)} 个片段")
        for i, c in enumerate(chunks):
            print(f"  [{i+1}] {c['doc_name']} (distance={c.get('distance', 'N/A')})")

        # 调用模型流式生成
        if not settings.dashscope_api_key:
            yield {"event": "error", "data": {"error": {"code": "NO_API_KEY", "message": "API Key 未配置"}}}
            return

        full_content = ""
        try:
            responses = Generation.call(
                model="qwen-plus",
                api_key=settings.dashscope_api_key,
                messages=[
                    {"role": "system", "content": RAG_QA_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                result_format="message",
                stream=True,
                incremental_output=True,
            )

            for resp in responses:
                if resp.status_code != 200:
                    yield {"event": "error", "data": {"error": {"code": "MODEL_ERROR", "message": f"模型调用失败: {resp.code} - {resp.message}"}}}
                    return

                chunk_text = resp.output.choices[0].message.content
                full_content += chunk_text
                yield {"event": "chunk", "data": {"content": chunk_text}}

        except Exception as e:
            yield {"event": "error", "data": {"error": {"code": "MODEL_ERROR", "message": str(e)[:200]}}}
            return

        # 保存助手回复
        assistant_msg = Message(
            conv_id=conv.id,
            role="assistant",
            content=full_content,
            citations=json.dumps(citations, ensure_ascii=False),
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # 操作日志
        log = OperationLog(
            user_id=user_id,
            action="ask_question",
            detail=f"提问: {question[:50]}",
        )
        db.add(log)
        db.commit()

        # 返回完成事件
        yield {
            "event": "done",
            "data": {
                "conv_id": conv.id,
                "message_id": assistant_msg.id,
                "content": full_content,
                "citations": citations,
            },
        }

    except Exception as e:
        yield {"event": "error", "data": {"error": {"code": "INTERNAL_ERROR", "message": str(e)[:200]}}}