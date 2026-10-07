"""测试 fixtures：内存数据库 + 测试客户端。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.core.deps import get_db
# 导入所有模型确保表注册到 Base.metadata
import app.models.user  # noqa
import app.models.invite_code  # noqa
import app.models.knowledge_base  # noqa
import app.models.document  # noqa
import app.models.conversation  # noqa
import app.models.operation_log  # noqa
import app.models.template  # noqa
import app.models.doc_task  # noqa
import app.models.student  # noqa
import app.models.dorm  # noqa
import app.models.todo  # noqa
import app.models.approval  # noqa
import app.models.expert  # noqa
import app.models.notice_task  # noqa
from app.models.user import User
from app.models.invite_code import InviteCode

# 测试引擎（模块级单例，确保同一内存库）
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


def _build_test_app():
    """构建测试用 FastAPI app，跳过真实 init_db。"""
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.responses import JSONResponse
    from app.api.v1 import auth, kb, admin, doc, excel, home, students, dorm, experts, notice
    from app.api.v1.approvals import talks_router

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        yield

    app = FastAPI(
        title="学工Buddy-Test",
        lifespan=test_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_disclaimer_header(request, call_next):
        response = await call_next(request)
        response.headers["X-Disclaimer"] = "AI output is draft only."
        return response

    class AppError(Exception):
        def __init__(self, code, message, status_code=400):
            self.code = code
            self.message = message
            self.status_code = status_code

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def global_error_handler(request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"}},
        )

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(kb.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(doc.router, prefix="/api/v1")
    app.include_router(excel.router, prefix="/api/v1")
    app.include_router(home.router, prefix="/api/v1")
    app.include_router(students.router, prefix="/api/v1")
    app.include_router(talks_router, prefix="/api/v1")
    app.include_router(dorm.router, prefix="/api/v1")
    app.include_router(experts.router, prefix="/api/v1")
    app.include_router(notice.router, prefix="/api/v1")
    return app


@pytest.fixture
def db_session():
    """内存 SQLite 数据库会话——每个测试独立。"""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()
    # 清理所有表
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def client(db_session):
    """FastAPI 测试客户端。"""
    app = _build_test_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client, db_session):
    """创建管理员并返回 token。"""
    code = InviteCode(code="ADMIN01", is_used=False)
    db_session.add(code)
    db_session.commit()

    resp = client.post("/api/v1/auth/register", json={
        "email": "admin@school.edu.cn",
        "password": "admin123",
        "invite_code": "ADMIN01",
    })
    assert resp.status_code == 201, f"Admin register failed: {resp.json()}"
    user = db_session.query(User).filter(User.email == "admin@school.edu.cn").first()
    user.role = "admin"
    db_session.commit()

    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@school.edu.cn",
        "password": "admin123",
    })
    return resp.json()["access_token"]


@pytest.fixture
def user_token(client, db_session):
    """创建普通用户并返回 token。"""
    code = InviteCode(code="USER01", is_used=False)
    db_session.add(code)
    db_session.commit()

    resp = client.post("/api/v1/auth/register", json={
        "email": "counselor@school.edu.cn",
        "password": "user1234",
        "invite_code": "USER01",
    })
    assert resp.status_code == 201, f"User register failed: {resp.json()}"
    resp = client.post("/api/v1/auth/login", json={
        "email": "counselor@school.edu.cn",
        "password": "user1234",
    })
    return resp.json()["access_token"]