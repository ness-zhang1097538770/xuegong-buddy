"""Embedding 服务——调用通义千问 text-embedding-v3。"""

import dashscope
from dashscope import TextEmbedding
from app.core.config import settings


def get_embedding(text: str) -> list[float]:
    """单段文本向量化，返回向量列表。"""
    if not settings.dashscope_api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    resp = TextEmbedding.call(
        model="text-embedding-v3",
        input=text,
        api_key=settings.dashscope_api_key,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding 调用失败: {resp.code} - {resp.message}")

    return resp.output["embeddings"][0]["embedding"]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """批量文本向量化。"""
    if not settings.dashscope_api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    resp = TextEmbedding.call(
        model="text-embedding-v3",
        input=texts,
        api_key=settings.dashscope_api_key,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding 调用失败: {resp.code} - {resp.message}")

    return [emb["embedding"] for emb in resp.output["embeddings"]]