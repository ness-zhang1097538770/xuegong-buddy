"""学工Buddy 后端入口——FastAPI 应用。"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.models.base import init_db
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
from app.api.v1 import auth, kb, admin, doc, excel, home, students, dorm, experts, notice, approvals
from app.api.v1.approvals import talks_router
from app.services.template_service import seed_builtin_templates
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库和内置模板。"""
    init_db()
    # 种子内置模板
    from app.models.base import SessionLocal
    db = SessionLocal()
    try:
        seed_builtin_templates(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="学工Buddy",
    description="辅导员 / 高校行政 AI 助手 · 私有知识库 + 文稿生成 + 台账自动化",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS——开发阶段允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局免责声明中间件
@app.middleware("http")
async def add_disclaimer_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Disclaimer"] = (
        "AI output is draft only. Student/sensitive/crisis materials MUST be reviewed by human."
    )
    return response


# 全局异常处理——统一错误格式
@app.exception_handler(Exception)
async def global_error_handler(request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误，请联系管理员"}},
    )


# 注册 API 路由
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
app.include_router(approvals.router, prefix="/api/v1")

# 验收页面——直接路由返回 HTML
_static_dir = os.path.join(os.path.dirname(__file__), "static")


@app.get("/api/v1/websites")
async def get_websites():
    """返回常用网站导航数据。"""
    import json
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "websites.json")
    if not os.path.isfile(data_path):
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "网站数据未找到"}})
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/", response_class=HTMLResponse)
async def serve_chat_page():
    html_path = os.path.join(_static_dir, "chat.html")
    if os.path.isfile(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>验收页面未找到，请确认 chat.html 已放入 app/static/</h1>"

# 挂载静态文件——放在所有路由之后，FastAPI 会优先匹配路由再匹配挂载
app.mount("/", StaticFiles(directory=_static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.port, reload=True)