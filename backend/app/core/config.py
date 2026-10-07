"""应用配置——从 .env 读取，所有敏感信息不入代码。"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 通义千问
    dashscope_api_key: str = ""

    # 数据库
    database_url: str = "sqlite:///./data/studybuddy.db"

    # Chroma 向量库
    chroma_path: str = "./data/chroma"

    # 文件上传
    upload_dir: str = "./data/uploads"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 天

    # 服务
    port: int = 8000

    # 文件限制
    max_upload_size_mb: int = 20
    allowed_upload_types: list[str] = ["pdf", "txt", "docx"]

    # 台账批量生成的并发数（串行时 50 行要等 50 次来回，并发后耗时按批次算）
    ledger_concurrency: int = 6

    # RAG 参数
    rag_top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

# 确保数据目录存在
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)