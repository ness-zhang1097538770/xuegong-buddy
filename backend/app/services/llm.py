"""大模型调用公共封装：SDK 初始化兜底、失败有限重试。"""

from app.core.config import settings


def call_qwen(
    messages: list[dict],
    model: str = "qwen-plus",
    temperature: float | None = None,
    max_retries: int = 2,
) -> str:
    """调用通义千问，返回模型文本。任何阶段失败统一抛 RuntimeError。

    重试策略：最多 max_retries 次（不含首次），全部失败抛出最后一次错误。
    后续切换 DeepSeek 只需改本函数。
    """
    if not settings.dashscope_api_key:
        raise RuntimeError("API Key 未配置")

    from dashscope import Generation

    kwargs = dict(
        model=model,
        api_key=settings.dashscope_api_key,
        messages=messages,
        result_format="message",
    )
    if temperature is not None:
        kwargs["temperature"] = temperature

    last_err: Exception | None = None
    for _ in range(max_retries + 1):
        try:
            resp = Generation.call(**kwargs)
            if resp.status_code == 200:
                content = resp.output.choices[0].message.content
                if content is None:
                    raise RuntimeError("模型返回空内容")
                return content
            last_err = RuntimeError(f"模型调用失败: {resp.code} - {resp.message}")
        except RuntimeError:
            raise
        except Exception as e:  # 含 SDK 初始化失败、网络超时等
            last_err = e

    raise RuntimeError(f"模型调用失败（已重试 {max_retries} 次）: {last_err}")
