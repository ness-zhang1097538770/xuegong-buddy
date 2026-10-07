"""专家智能体 RAG：按需检索 → 上下文构建 → 引用回传。

设计要点：
1. 按需检索（policy: always / auto / off），不是每个问题都检索；
2. 任何失败都静默降级为「不检索」，绝不中断专家对话；
3. cosine distance 越小越相似，max_distance 用于过滤无关片段。
"""

import logging
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.services import expert_service
from app.services.embedding_service import get_embedding
from app.services.kb_service import _get_or_create_collection, ensure_user_kb

logger = logging.getLogger(__name__)

DEFAULT_MAX_DISTANCE = 0.65
DEFAULT_TOP_K = 5


def get_rag_config(expert_id: str) -> dict:
    """读取专家的 RAG 配置；不存在则返回空 dict（等价于 off）。"""
    expert = expert_service.get_expert(expert_id)
    return (expert or {}).get("rag") or {}


def should_retrieve(rag_cfg: dict, question: str) -> bool:
    """判断本次提问是否需要检索。"""
    policy = rag_cfg.get("policy", "off")
    if policy == "always":
        return True
    if policy == "off":
        return False
    # auto：命中触发词才检索
    return any(w in question for w in rag_cfg.get("trigger_keywords", []))


def _shared_kb_ids(db: Session) -> list[int]:
    """公共政策库 id 列表（只读，不自动创建）。"""
    rows = db.query(KnowledgeBase).filter(KnowledgeBase.kb_type == "shared").all()
    return [kb.id for kb in rows]


def _build_query(expert: dict, question: str, last_answer: str = "") -> str:
    """构造检索 query：专家身份前缀增强 + 短问题兜底。"""
    if len(question) < 8 and last_answer:
        # 指代性短问题（"那家长那边呢"）补上上文
        return f"{last_answer[:100]} {question}"
    name = expert.get("name", "")
    desc = expert.get("desc", "")
    return f"{name}（{desc}）：{question}"


def retrieve(
    db: Session,
    user_id: int,
    expert_id: str,
    question: str,
    last_answer: str = "",
) -> tuple[list[dict], dict]:
    """检索与问题相关的知识库片段。

    返回 (chunks, meta)。任何异常都返回空列表，由调用方降级处理。
    chunks 元素：{"text", "doc_name", "kb_type", "distance"}
    """
    rag_cfg = get_rag_config(expert_id)
    if not should_retrieve(rag_cfg, question):
        return [], {"attempted": False, "reason": "policy_off"}

    expert = expert_service.get_expert(expert_id) or {}
    scopes = rag_cfg.get("scopes", ["personal"])
    top_k = int(rag_cfg.get("top_k", DEFAULT_TOP_K))
    max_distance = float(rag_cfg.get("max_distance", DEFAULT_MAX_DISTANCE))
    categories = rag_cfg.get("categories", ["综合"])
    where = {"category": {"$in": categories}} if categories else None

    # 1) 确定检索范围
    kb_ids: list[tuple[int, str]] = []
    if "shared" in scopes:
        kb_ids += [(i, "shared") for i in _shared_kb_ids(db)]
    if "personal" in scopes:
        try:
            kb_ids.append((ensure_user_kb(db, user_id).id, "personal"))
        except Exception as e:
            logger.warning("[expert_rag] 个人库获取失败: %s", e)

    if not kb_ids:
        return [], {"attempted": True, "reason": "no_kb", "hits": 0}

    # 2) 查询向量
    try:
        q_emb = get_embedding(_build_query(expert, question, last_answer))
    except Exception as e:
        logger.warning("[expert_rag] embedding 失败，降级为不检索: %s", e)
        return [], {"attempted": True, "reason": "embedding_failed", "hits": 0}

    # 3) 多库检索并合并
    candidates: list[dict] = []
    for kb_id, kb_type in kb_ids:
        try:
            coll = _get_or_create_collection(kb_id)
            res = coll.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
                where=where,
            )
        except Exception as e:
            logger.warning("[expert_rag] kb_%s 检索失败: %s", kb_id, e)
            continue

        docs = (res or {}).get("documents") or [[]]
        metas = (res or {}).get("metadatas") or [[]]
        dists = (res or {}).get("distances") or [[]]
        if not docs or not docs[0]:
            continue

        for i in range(len(docs[0])):
            candidates.append({
                "text": docs[0][i],
                "doc_name": (metas[0][i] or {}).get("doc_name", "未知文档"),
                "kb_type": kb_type,
                "distance": dists[0][i] if i < len(dists[0]) else None,
            })

    # 4) 过滤 + 重排 + 截断
    filtered = [c for c in candidates if c["distance"] is None or c["distance"] <= max_distance]
    filtered.sort(key=lambda x: x["distance"] if x["distance"] is not None else 9.0)
    chunks = filtered[:top_k]

    logger.info(
        "[expert_rag] expert=%s hits=%s/%s top1=%s",
        expert_id, len(chunks), len(candidates),
        round(chunks[0]["distance"], 3) if chunks else None,
    )
    return chunks, {"attempted": True, "reason": "ok", "hits": len(chunks),
                    "candidates": len(candidates)}


def build_context(chunks: list[dict]) -> str:
    """把检索结果拼成注入用户消息的材料块。"""
    parts = ["## 参考材料（来自你的知识库，方括号编号即引用号）\n"]
    for i, c in enumerate(chunks, 1):
        src = "公共政策库" if c["kb_type"] == "shared" else "我的知识库"
        parts.append(f"[{i}] 来源：{src} · 《{c['doc_name']}》\n{c['text']}\n")
    parts.append("（参考材料结束，以下为辅导员的提问）")
    return "\n".join(parts)


def to_citations(chunks: list[dict]) -> list[dict]:
    """转成前端可渲染的引用结构。"""
    return [
        {
            "index": i,
            "doc_name": c["doc_name"],
            "kb_type": c["kb_type"],
            "chunk_text": c["text"][:200],
            "distance": round(c["distance"], 3) if c["distance"] is not None else None,
        }
        for i, c in enumerate(chunks, 1)
    ]
