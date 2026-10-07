"""知识库问答模块测试（mock 模型调用）。"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestChatErrors:
    def test_chat_unauthorized(self, client):
        resp = client.get("/api/v1/kb/chat?q=测试问题")
        assert resp.status_code == 401


class TestConversations:
    def test_list_conversations_empty(self, client, user_token):
        resp = client.get(
            "/api/v1/kb/conversations",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        # 新用户无对话
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 0

    def test_get_messages_conversation_not_found(self, client, user_token):
        resp = client.get(
            "/api/v1/kb/conversations/999/messages",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 404