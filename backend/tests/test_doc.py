"""文稿模块测试（mock 模型调用）。"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.models.template import Template
from app.models.doc_task import DocTask


class TestTemplates:
    def test_list_templates_empty(self, client, user_token):
        resp = client.get("/api/v1/doc/templates", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_create_template(self, client, user_token):
        resp = client.post(
            "/api/v1/doc/templates",
            json={
                "name": "测试模板",
                "category": "测试",
                "style": "formal",
                "user_prompt_template": "测试内容 {var1}",
                "variables": '["var1"]',
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "测试模板"
        assert data["is_builtin"] is False

    def test_create_and_list(self, client, user_token):
        client.post("/api/v1/doc/templates", json={
            "name": "我的模板", "category": "自定义", "user_prompt_template": "内容", "variables": "[]"
        }, headers={"Authorization": f"Bearer {user_token}"})

        resp = client.get("/api/v1/doc/templates", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_delete_own_template(self, client, user_token):
        resp = client.post("/api/v1/doc/templates", json={
            "name": "待删除", "category": "测试", "user_prompt_template": "内容", "variables": "[]"
        }, headers={"Authorization": f"Bearer {user_token}"})
        tmpl_id = resp.json()["id"]

        resp = client.delete(f"/api/v1/doc/templates/{tmpl_id}", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200

    def test_cannot_delete_builtin(self, client, user_token, db_session):
        # 手动添加内置模板
        tmpl = Template(name="内置", category="内置", user_prompt_template="内容",
                        variables="[]", is_builtin=True)
        db_session.add(tmpl)
        db_session.commit()

        resp = client.delete(f"/api/v1/doc/templates/{tmpl.id}", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 400
        assert "内置" in resp.json()["detail"]

    def test_cannot_modify_others(self, client, user_token, admin_token):
        # admin 创建模板
        resp = client.post("/api/v1/doc/templates", json={
            "name": "admin模板", "category": "管理员", "user_prompt_template": "内容", "variables": "[]"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        tmpl_id = resp.json()["id"]

        # user 尝试修改
        resp = client.put(f"/api/v1/doc/templates/{tmpl_id}", json={
            "name": "被改了"
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403


class TestDocGenerate:
    def test_generate_no_template(self, client, user_token):
        resp = client.post("/api/v1/doc/generate", json={
            "template_id": 999, "variables": {}
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 400

    @patch("app.services.doc_service.Generation.call")
    def test_generate_success(self, mock_gen, client, user_token, db_session):
        # 创建模板
        tmpl = Template(name="测试生成", category="测试", user_prompt_template="姓名: {name}",
                        variables='["name"]', style="formal")
        db_session.add(tmpl)
        db_session.commit()

        # mock 模型返回
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message.content = "生成内容：张三"
        mock_gen.return_value = mock_response

        resp = client.post("/api/v1/doc/generate", json={
            "template_id": tmpl.id, "variables": {"name": "张三"}
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "done"
        assert "张三" in data["content"]

    def test_download_not_found(self, client, user_token):
        resp = client.get("/api/v1/doc/download/999", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 404

    def test_docx_export_format(self):
        """测试 docx 导出格式（纯函数）。"""
        from app.services.doc_service import export_docx

        content = "## 测试标题\n这是一段内容。\n**加粗文本**"
        docx_bytes = export_docx(content, "测试模板")
        assert len(docx_bytes) > 0
        # .docx 文件以 PK 开头（ZIP 格式）
        assert docx_bytes[:2] == b"PK"

    def test_variable_placeholders(self):
        """测试模板变量占位符替换。"""
        result = "姓名: {name}".format(name="张三")
        assert result == "姓名: 张三"

        result = "姓名: {name}".format(**{"name": "张三"})
        assert result == "姓名: 张三"


class TestDocTasks:
    def test_list_tasks_empty(self, client, user_token):
        resp = client.get("/api/v1/doc/tasks", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @patch("app.services.doc_service.Generation.call")
    def test_task_history(self, mock_gen, client, user_token, db_session):
        tmpl = Template(name="任务历史", category="测试", user_prompt_template="内容",
                        variables="[]")
        db_session.add(tmpl)
        db_session.commit()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message.content = "生成结果"
        mock_gen.return_value = mock_response

        client.post("/api/v1/doc/generate", json={
            "template_id": tmpl.id, "variables": {}
        }, headers={"Authorization": f"Bearer {user_token}"})

        resp = client.get("/api/v1/doc/tasks", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1