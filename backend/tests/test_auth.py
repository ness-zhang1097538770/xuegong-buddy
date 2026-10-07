"""认证模块测试。"""

import pytest


class TestRegister:
    def test_register_success(self, client, db_session):
        from app.models.invite_code import InviteCode
        code = InviteCode(code="TEST01", is_used=False)
        db_session.add(code)
        db_session.commit()

        resp = client.post("/api/v1/auth/register", json={
            "email": "test@school.edu.cn",
            "password": "test1234",
            "invite_code": "TEST01",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "test@school.edu.cn"
        assert "user_id" in data

    def test_register_duplicate_email(self, client, db_session):
        from app.models.invite_code import InviteCode
        code1 = InviteCode(code="DUP01", is_used=False)
        code2 = InviteCode(code="DUP02", is_used=False)
        db_session.add_all([code1, code2])
        db_session.commit()

        client.post("/api/v1/auth/register", json={
            "email": "dup@school.edu.cn", "password": "test1234", "invite_code": "DUP01",
        })
        resp = client.post("/api/v1/auth/register", json={
            "email": "dup@school.edu.cn", "password": "test1234", "invite_code": "DUP02",
        })
        assert resp.status_code == 400
        assert "已注册" in resp.json()["detail"]

    def test_register_invalid_invite_code(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "test@school.edu.cn", "password": "test1234", "invite_code": "FAKE00",
        })
        assert resp.status_code == 400
        assert "邀请码" in resp.json()["detail"]

    def test_invite_code_cannot_reuse(self, client, db_session):
        from app.models.invite_code import InviteCode
        code = InviteCode(code="ONCE01", is_used=False)
        db_session.add(code)
        db_session.commit()

        # 第一次使用
        resp = client.post("/api/v1/auth/register", json={
            "email": "first@school.edu.cn", "password": "test1234", "invite_code": "ONCE01",
        })
        assert resp.status_code == 201

        # 第二次使用同一个码
        resp = client.post("/api/v1/auth/register", json={
            "email": "second@school.edu.cn", "password": "test1234", "invite_code": "ONCE01",
        })
        assert resp.status_code == 400

    def test_register_weak_password(self, client, db_session):
        from app.models.invite_code import InviteCode
        code = InviteCode(code="WEAK01", is_used=False)
        db_session.add(code)
        db_session.commit()

        resp = client.post("/api/v1/auth/register", json={
            "email": "weak@school.edu.cn", "password": "123", "invite_code": "WEAK01",
        })
        assert resp.status_code == 422  # Pydantic validation error


class TestLogin:
    def test_login_success(self, client, user_token):
        resp = client.post("/api/v1/auth/login", json={
            "email": "counselor@school.edu.cn", "password": "user1234",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "counselor@school.edu.cn"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "counselor@school.edu.cn", "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@school.edu.cn", "password": "test1234",
        })
        assert resp.status_code == 401

    def test_get_me_unauthorized(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_get_me_authorized(self, client, user_token):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "counselor@school.edu.cn"


class TestAdmin:
    def test_non_admin_cannot_create_codes(self, client, user_token):
        resp = client.post(
            "/api/v1/admin/invite-codes",
            json={"count": 5},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_create_codes(self, client, admin_token):
        resp = client.post(
            "/api/v1/admin/invite-codes",
            json={"count": 3},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert len(resp.json()["codes"]) == 3

    def test_admin_can_list_codes(self, client, admin_token):
        resp = client.get(
            "/api/v1/admin/invite-codes",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200