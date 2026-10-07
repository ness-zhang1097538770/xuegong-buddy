"""专家智能体 RAG 单元测试（纯 mock，不调真实模型/embedding）。"""

import pytest
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from app.services import expert_rag
from app.services import expert_service

FAKE_EXPERT = {"id": "funding-award", "name": "资助与评奖专员", "desc": "资助政策解读"}


def _collection(docs, metas, dists):
    """构造一个 fake Chroma collection。"""
    coll = MagicMock()
    coll.query.return_value = {
        "documents": [docs],
        "metadatas": [metas],
        "distances": [dists],
    }
    return coll


# === should_retrieve：触发策略 ===

def test_should_retrieve_off():
    assert expert_rag.should_retrieve({"policy": "off"}, "任何问题") is False


def test_should_retrieve_always():
    assert expert_rag.should_retrieve({"policy": "always"}, "任何问题") is True


def test_should_retrieve_auto_no_trigger():
    cfg = {"policy": "auto", "trigger_keywords": ["助学金", "评定"]}
    assert expert_rag.should_retrieve(cfg, "学生沉默我该怎么接？") is False


def test_should_retrieve_auto_hit():
    cfg = {"policy": "auto", "trigger_keywords": ["助学金", "评定"]}
    assert expert_rag.should_retrieve(cfg, "助学金评定流程是什么？") is True


# === retrieve：降级不抛异常 ===

def test_retrieve_policy_off_skips_embedding(db_session):
    expert = dict(FAKE_EXPERT, rag={"policy": "off"})
    with patch.object(expert_service, "get_expert", return_value=expert), \
         patch.object(expert_rag, "get_embedding") as mock_emb:
        chunks, meta = expert_rag.retrieve(db_session, 1, "funding-award", "随便聊聊")
    assert chunks == []
    assert meta["attempted"] is False
    mock_emb.assert_not_called()


def test_retrieve_empty_kb_no_exception(db_session):
    expert = dict(FAKE_EXPERT, rag={"policy": "always", "scopes": ["personal"], "top_k": 5, "max_distance": 0.7})
    empty_coll = MagicMock()
    empty_coll.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    with patch.object(expert_service, "get_expert", return_value=expert), \
         patch.object(expert_rag, "ensure_user_kb", return_value=MagicMock(id=1)), \
         patch.object(expert_rag, "get_embedding", return_value=[0.0, 0.0]), \
         patch.object(expert_rag, "_get_or_create_collection", return_value=empty_coll):
        chunks, meta = expert_rag.retrieve(db_session, 1, "funding-award", "助学金评定流程")
    assert chunks == []
    assert meta["attempted"] is True
    assert meta["hits"] == 0


def test_retrieve_embedding_failure_degrades(db_session):
    expert = dict(FAKE_EXPERT, rag={"policy": "always", "scopes": ["personal"], "top_k": 5, "max_distance": 0.7})
    with patch.object(expert_service, "get_expert", return_value=expert), \
         patch.object(expert_rag, "ensure_user_kb", return_value=MagicMock(id=1)), \
         patch.object(expert_rag, "get_embedding", side_effect=RuntimeError("embedding down")):
        chunks, meta = expert_rag.retrieve(db_session, 1, "funding-award", "助学金评定流程")
    assert chunks == []
    assert meta["attempted"] is True
    assert meta["reason"] == "embedding_failed"


def test_retrieve_merges_and_sorts_by_distance(db_session):
    expert = dict(FAKE_EXPERT, rag={
        "policy": "always", "scopes": ["shared", "personal"], "top_k": 5, "max_distance": 0.9,
    })
    colls = {
        1: _collection(["片段A"], [{"doc_name": "A"}], [0.5]),
        2: _collection(["片段B"], [{"doc_name": "B"}], [0.2]),
        3: _collection(["片段C"], [{"doc_name": "C"}], [0.8]),
    }
    with patch.object(expert_service, "get_expert", return_value=expert), \
         patch.object(expert_rag, "_shared_kb_ids", return_value=[1, 2]), \
         patch.object(expert_rag, "ensure_user_kb", return_value=MagicMock(id=3)), \
         patch.object(expert_rag, "get_embedding", return_value=[0.0, 0.0]), \
         patch.object(expert_rag, "_get_or_create_collection", side_effect=lambda kb_id: colls[kb_id]):
        chunks, meta = expert_rag.retrieve(db_session, 1, "funding-award", "助学金评定流程")
    assert meta["hits"] == 3
    assert [c["doc_name"] for c in chunks] == ["B", "A", "C"]  # 按 distance 升序


def test_retrieve_filters_by_max_distance(db_session):
    expert = dict(FAKE_EXPERT, rag={
        "policy": "always", "scopes": ["personal"], "top_k": 5, "max_distance": 0.7,
    })
    coll = _collection(
        ["近", "中", "远"],
        [{"doc_name": "近"}, {"doc_name": "中"}, {"doc_name": "远"}],
        [0.1, 0.5, 0.9],
    )
    with patch.object(expert_service, "get_expert", return_value=expert), \
         patch.object(expert_rag, "ensure_user_kb", return_value=MagicMock(id=1)), \
         patch.object(expert_rag, "get_embedding", return_value=[0.0]), \
         patch.object(expert_rag, "_get_or_create_collection", return_value=coll):
        chunks, meta = expert_rag.retrieve(db_session, 1, "funding-award", "助学金评定流程")
    assert [c["doc_name"] for c in chunks] == ["近", "中"]  # 0.9 被阈值过滤


def test_retrieve_passes_category_filter(db_session):
    """P1：按专家类目硬过滤（where $in）。"""
    expert = dict(FAKE_EXPERT, rag={
        "policy": "always", "scopes": ["personal"], "top_k": 5, "max_distance": 0.7,
        "categories": ["资助", "综合"],
    })
    coll = _collection(["片段"], [{"doc_name": "A"}], [0.3])
    with patch.object(expert_service, "get_expert", return_value=expert), \
         patch.object(expert_rag, "ensure_user_kb", return_value=MagicMock(id=1)), \
         patch.object(expert_rag, "get_embedding", return_value=[0.0]), \
         patch.object(expert_rag, "_get_or_create_collection", return_value=coll):
        expert_rag.retrieve(db_session, 1, "funding-award", "助学金评定流程")

    coll.query.assert_called_once()
    assert coll.query.call_args.kwargs.get("where") == {"category": {"$in": ["资助", "综合"]}}


# === build_messages：提示词注入 ===

def test_build_messages_with_rag_block():
    msgs, _config = expert_service.build_messages(
        "funding-award", [], "助学金评定流程",
        rag_block="[1] 来源：我的知识库 · 《测试》\n内容",
    )
    assert "参考材料使用规则" in msgs[0]["content"]
    assert "[1] 来源" in msgs[-1]["content"]


def test_build_messages_no_hit_notice():
    msgs, _config = expert_service.build_messages(
        "funding-award", [], "助学金评定流程", rag_no_hit=True,
    )
    assert "未检索到校本依据" in msgs[0]["content"]


# === chat_stream：temperature 透传 ===

@pytest.mark.asyncio
async def test_chat_stream_passes_temperature():
    from app.core.config import settings

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeOutput:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    class FakeResp:
        def __init__(self, content):
            self.status_code = HTTPStatus.OK
            self.output = FakeOutput(content)
            self.code = ""
            self.message = ""

    with patch.object(settings, "dashscope_api_key", "fake-key"), \
         patch("dashscope.Generation.call", return_value=[FakeResp("你好")]) as mock_call:
        chunks = []
        async for c in expert_service.chat_stream(
            "funding-award", [{"role": "user", "content": "hi"}], temperature=0.3,
        ):
            chunks.append(c)

    kwargs = mock_call.call_args.kwargs
    assert kwargs.get("temperature") == 0.3
    assert kwargs.get("model") == "qwen-plus"
    assert any("token" in c for c in chunks)
    assert any("event: done" in c for c in chunks)
