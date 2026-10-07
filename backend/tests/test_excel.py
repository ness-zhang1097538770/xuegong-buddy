"""Excel 台账模块测试。"""

import io
import pytest
from unittest.mock import patch, MagicMock
from openpyxl import Workbook


def _make_test_excel():
    """创建测试 Excel 文件。"""
    wb = Workbook()
    ws = wb.active
    ws.append(["姓名", "班级", "学业表现", "活动参与", "备注"])
    ws.append(["张三", "计算机2024", "优秀", "ACM社团", "编程能力强"])
    ws.append(["李四", "数学2024", "良好", "学生会", "沟通能力好"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


class TestExcelRead:
    def test_parse_excel(self):
        """测试 Excel 解析（纯函数）。"""
        from app.services.excel_service import read_excel

        data = _make_test_excel()
        rows = read_excel(data)
        assert len(rows) == 2
        assert rows[0]["姓名"] == "张三"
        assert rows[0]["班级"] == "计算机2024"

    def test_write_excel(self):
        """测试 Excel 写入（纯函数）。"""
        from app.services.excel_service import write_excel

        rows = [{"姓名": "张三", "班级": "计科", "AI评语": "表现优秀"}]
        data = write_excel(rows, ["姓名", "班级"])
        assert len(data) > 0
        assert data[:2] == b"PK"

    def test_upload_read(self, client, user_token):
        """测试上传并读取 Excel。"""
        data = _make_test_excel()
        resp = client.post(
            "/api/v1/excel/upload/read",
            files={"file": ("test.xlsx", data)},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["total_rows"] == 2
        assert len(result["preview"]) == 2
        assert "task_id" in result

    def test_upload_invalid_format(self, client, user_token):
        """测试上传非 Excel 格式。"""
        resp = client.post(
            "/api/v1/excel/upload/read",
            files={"file": ("test.txt", b"not excel")},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 400

    def test_upload_empty_excel(self, client, user_token):
        """测试上传空 Excel。"""
        wb = Workbook()
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = client.post(
            "/api/v1/excel/upload/read",
            files={"file": ("empty.xlsx", buf.getvalue())},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        # 空 Excel 应该报错
        assert resp.status_code == 400


class TestBatchGenerate:
    @patch("app.services.excel_service.Generation.call")
    def test_batch_generate(self, mock_gen, client, user_token):
        """测试批量生成评语。"""
        # 先上传
        data = _make_test_excel()
        resp = client.post(
            "/api/v1/excel/upload/read",
            files={"file": ("students.xlsx", data)},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200

        # Mock 模型
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message.content = "该生表现优秀，建议继续保持。"
        mock_gen.return_value = mock_response

        # 批量生成
        resp = client.post(
            "/api/v1/excel/batch-generate?max_rows=2",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["row_count"] == 2
        # 验证新增字段：headers 和 preview
        assert "AI评语" in result["headers"]
        assert len(result["preview"]) == 2
        assert result["preview"][0]["AI评语"] == "该生表现优秀，建议继续保持。"

        # 下载（磁盘持久化）
        result_id = result["task_id"]
        resp = client.get(
            f"/api/v1/excel/download/{result_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

    @patch("app.services.excel_service.Generation.call")
    def test_batch_generate_download_persisted(self, mock_gen, client, user_token):
        """测试结果持久化到磁盘，下载不依赖内存缓存。"""
        data = _make_test_excel()
        client.post(
            "/api/v1/excel/upload/read",
            files={"file": ("students.xlsx", data)},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message.content = "评语"
        mock_gen.return_value = mock_response

        resp = client.post(
            "/api/v1/excel/batch-generate?max_rows=1",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        result_id = resp.json()["task_id"]

        # 验证磁盘文件存在
        from pathlib import Path
        file_path = Path("data/results") / f"{result_id}.xlsx"
        assert file_path.is_file()

        # 下载
        resp = client.get(
            f"/api/v1/excel/download/{result_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"


class TestExtract:
    @patch("app.services.excel_service.Generation.call")
    def test_extract_info(self, mock_gen, client, user_token):
        """测试信息提取。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message.content = '{"姓名":"张三","班级":"计算机2024","特长":"【缺失】"}'
        mock_gen.return_value = mock_response

        resp = client.post(
            "/api/v1/excel/extract",
            json={
                "text": "张三同学是计算机2024级学生，成绩优异。",
                "fields": ["姓名", "班级", "特长"],
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["姓名"] == "张三"
        assert result["特长"] == "【缺失】"