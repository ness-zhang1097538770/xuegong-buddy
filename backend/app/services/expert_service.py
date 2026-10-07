"""专家智能体服务——加载提示词、调用大模型。"""

import json
import os
import re
import yaml
from pathlib import Path
from typing import AsyncGenerator

from app.core.config import settings


# 专家配置目录（相对于 backend/ 即 app/../experts/）
_EXPERTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "experts")


def _load_index() -> dict:
    """读取专家注册表。"""
    path = os.path.join(_EXPERTS_DIR, "index.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_expert_prompt(expert_id: str) -> tuple[dict, str]:
    """读取专家的 YAML 头部配置 + Markdown 正文（即 System Prompt）。

    返回 (config_dict, system_prompt_str)。
    """
    index = _load_index()
    expert = next((e for e in index["experts"] if e["id"] == expert_id), None)
    if not expert:
        raise ValueError(f"专家 '{expert_id}' 不存在")

    prompt_file = expert.get("prompt_file", f"{expert_id}.md")
    path = os.path.join(_EXPERTS_DIR, prompt_file)
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # 解析 YAML front matter
    config = {}
    body = raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if m:
        try:
            config = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            pass
        body = raw[m.end():]

    return config, body.strip()


def list_experts() -> list[dict]:
    """返回专家列表，供前端「专家广场」使用。"""
    index = _load_index()
    return index.get("experts", [])


def get_categories() -> list[dict]:
    """返回分类列表。"""
    index = _load_index()
    return index.get("categories", [])


def get_expert(expert_id: str) -> dict | None:
    """按 id 返回专家配置（来自 index.json）。"""
    index = _load_index()
    return next((e for e in index.get("experts", []) if e.get("id") == expert_id), None)


def get_temperature(expert_id: str) -> float | None:
    """读取专家温度配置。"""
    expert = get_expert(expert_id)
    return expert.get("temperature") if expert else None


def build_messages(
    expert_id: str,
    history: list[dict],
    user_message: str,
    rag_block: str | None = None,
    rag_no_hit: bool = False,
) -> tuple[list[dict], dict]:
    """构建发给大模型的完整消息列表。

    rag_block：检索到的参考材料块；有值时在 system 追加使用规则、在用户消息前置材料。
    rag_no_hit：检索过但无命中；在 system 追加「未检索到」提示。
    """
    from app.services.prompts.expert_rag import (
        EXPERT_RAG_RULES,
        EXPERT_RAG_NO_HIT_NOTICE,
    )

    config, system_prompt = _load_expert_prompt(expert_id)

    system = system_prompt
    if rag_block:
        system = system + "\n\n" + EXPERT_RAG_RULES
    elif rag_no_hit:
        system = system + "\n\n" + EXPERT_RAG_NO_HIT_NOTICE

    msgs = [{"role": "system", "content": system}]

    for h in history:
        role = h.get("role", "user")
        content = h.get("content", "")
        msgs.append({"role": "assistant" if role == "assistant" else "user", "content": content})

    final_user = f"{rag_block}\n\n---\n\n{user_message}" if rag_block else user_message
    msgs.append({"role": "user", "content": final_user})
    return msgs, config


async def chat_stream(
    expert_id: str,
    messages: list[dict],
    temperature: float | None = None,
) -> AsyncGenerator[str, None]:
    """流式调用大模型，逐个 yield token 供 SSE 输出。

    当前使用通义千问 DashScope，后续切换 DeepSeek 只需改此函数。
    """
    from dashscope import Generation
    from dashscope.api_entities.dashscope_response import GenerationResponse
    from http import HTTPStatus

    if not settings.dashscope_api_key:
        yield "data: [ERROR] 模型 API Key 未配置，请在 .env 中设置 DASHSCOPE_API_KEY\n\n"
        yield "event: error\ndata: {\"error\": {\"code\": \"NO_API_KEY\", \"message\": \"模型 API Key 未配置\"}}\n\n"
        return

    try:
        kwargs = dict(
            model="qwen-plus",
            api_key=settings.dashscope_api_key,
            messages=messages,
            result_format="message",
            stream=True,
            incremental_output=True,
        )
        if temperature is not None:
            kwargs["temperature"] = temperature

        gen = Generation.call(**kwargs)

        full_text = ""
        for resp in gen:
            if resp.status_code == HTTPStatus.OK:
                chunk = resp.output.choices[0].message.content
                full_text += chunk
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            else:
                yield f"event: error\ndata: {json.dumps({'error': {'code': resp.code, 'message': resp.message}})}\n\n"
                return

        yield "event: done\ndata: {\"content\": " + json.dumps(full_text) + "}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': {'code': 'LLM_ERROR', 'message': str(e)}})}\n\n"