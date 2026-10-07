"""语音识别（ASR）服务——导入录音转文字，通义千问 Paraformer 实时版。"""

import os

from app.core.config import settings


class _NoopCallback:
    """同步识别模式下的空回调，结果从 call() 返回值读取。"""

    def on_open(self) -> None: ...
    def on_complete(self) -> None: ...
    def on_error(self, result) -> None: ...
    def on_close(self) -> None: ...
    def on_event(self, result) -> None: ...


_FORMAT_MAP = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".m4a": "aac",
    ".aac": "aac",
    ".ogg": "ogg",
    ".flac": "flac",
    ".webm": "webm",
    ".amr": "amr",
    ".pcm": "pcm",
}

ALLOWED_AUDIO_EXTS = set(_FORMAT_MAP.keys())


def transcribe_audio(file_path: str) -> str:
    """导入本地音频文件，返回识别出的文字。失败抛 ValueError/RuntimeError。"""
    if not settings.dashscope_api_key:
        raise RuntimeError("语音识别 Key 未配置，请在 .env 中设置 DASHSCOPE_API_KEY")

    ext = os.path.splitext(file_path)[1].lower()
    fmt = _FORMAT_MAP.get(ext)
    if not fmt:
        raise ValueError(f"不支持的音频格式：{ext or '未知'}")

    import dashscope
    from dashscope.audio.asr import Recognition

    # Recognition API 不接收 api_key 参数，走全局默认 key
    dashscope.api_key = settings.dashscope_api_key

    recognition = Recognition(
        model="paraformer-realtime-v2",
        callback=_NoopCallback(),
        format=fmt,
        sample_rate=16000,
    )
    result = recognition.call(file=file_path)

    status = getattr(result, "status_code", None)
    if status != 200:
        code = getattr(result, "code", "UNKNOWN")
        message = getattr(result, "message", "未知错误")
        raise RuntimeError(f"语音识别失败 [{code}]：{message}")

    output = getattr(result, "output", None) or {}
    sentences = output.get("sentence", [])
    if isinstance(sentences, dict):
        sentences = [sentences]
    text = "".join(s.get("text", "") for s in sentences if isinstance(s, dict))
    return text.strip()
