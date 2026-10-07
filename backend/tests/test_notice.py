"""通知变材料测试：解析器纯函数 + 生成（mock 模型）+ 下载。"""

from app.services.notice_service import parse_sections


def test_parse_sections_canonical():
    raw = (
        "【通知-正式版】\n正式通知内容\n"
        "【通知-群发版】\n群发文案内容\n"
        "【通知-家长版】\n家长通知内容\n"
        "【班会方案】\n班会方案内容\n"
    )
    r = parse_sections(raw)
    assert "正式通知内容" in r["notice_formal"]
    assert "群发文案内容" in r["notice_group"]
    assert "家长通知内容" in r["notice_parent"]
    assert "班会方案内容" in r["meeting_plan"]


def test_parse_sections_markdown_variant():
    raw = (
        "## 通知-正式版\nA\n"
        "# 通知-群发版\nB\n"
        "## 通知-家长版\nC\n"
        "## 班会方案\nD\n"
    )
    r = parse_sections(raw)
    assert "A" in r["notice_formal"]
    assert "B" in r["notice_group"]
    assert "C" in r["notice_parent"]
    assert "D" in r["meeting_plan"]


def test_parse_sections_fallback():
    r = parse_sections("没有任何标记的正文")
    assert r["notice_formal"] == "没有任何标记的正文"


def test_generate_notice(monkeypatch, client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    def fake_call(messages, temperature=None):
        return (
            "【通知-正式版】\n正式通知\n"
            "【通知-群发版】\n群发文案\n"
            "【通知-家长版】\n家长通知\n"
            "【班会方案】\n班会方案"
        )

    monkeypatch.setattr("app.services.notice_service.call_qwen", fake_call)
    resp = client.post(
        "/api/v1/notice/generate",
        json={"theme": "防电诈主题班会", "event_time": "周日晚7点", "place": "教三101"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "done"
    assert "正式通知" in data["result"]["notice_formal"]
    # 代码确定性两件套
    assert "签到表" in data["result"]["signin_sheet"]
    assert "班会纪要" in data["result"]["minutes_template"]


def test_generate_notice_model_fail(monkeypatch, client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    def fake_call(messages, temperature=None):
        raise RuntimeError("API Key 未配置")

    monkeypatch.setattr("app.services.notice_service.call_qwen", fake_call)
    resp = client.post(
        "/api/v1/notice/generate", json={"theme": "班会"}, headers=headers
    )
    assert resp.status_code == 500
    assert "error" in resp.json()


def test_download_notice(monkeypatch, client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    def fake_call(messages, temperature=None):
        return (
            "【通知-正式版】\n正式通知\n"
            "【通知-群发版】\n群发\n"
            "【通知-家长版】\n家长\n"
            "【班会方案】\n方案"
        )

    monkeypatch.setattr("app.services.notice_service.call_qwen", fake_call)
    gen = client.post(
        "/api/v1/notice/generate", json={"theme": "班会"}, headers=headers
    ).json()

    resp = client.get(f"/api/v1/notice/download/{gen['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )
