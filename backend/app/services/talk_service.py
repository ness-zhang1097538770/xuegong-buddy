"""谈话记录仪 AI 初稿服务。"""

from app.services.llm import call_qwen
from app.services.prompts.talk_draft import TALK_DRAFT_SYSTEM_PROMPT, TALK_DRAFT_USER_PROMPT


def generate_talk_draft(
    student_name: str,
    method: str,
    topic: str,
    key_points: str,
    history: str = "",
) -> str:
    """基于本次要点 + 历史生成谈心谈话记录草稿，返回结构化文本。"""
    user_prompt = TALK_DRAFT_USER_PROMPT.format(
        student_name=student_name,
        method=method,
        topic=topic or "日常关心",
        key_points=key_points,
        history=history or "（无历史记录）",
    )
    return call_qwen(
        [
            {"role": "system", "content": TALK_DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
