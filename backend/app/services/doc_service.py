"""文稿生成服务：调用模型 + 导出 Word + 参考文件解析。"""

import json, os, io, uuid
from sqlalchemy.orm import Session
from dashscope import Generation
from docx import Document
from pypdf import PdfReader
from app.core.config import settings
from app.models.doc_task import DocTask
from app.models.operation_log import OperationLog
from app.services.template_service import get_template

# 参考文件内存缓存（一次性使用）
_ref_cache: dict = {}  # ref_id -> {"filename": str, "text": str, "user_id": int}

STYLE_DESC = {
    "formal": "正式公文风格——措辞规范、格式完整、适合上报和存档",
    "soft": "谈心柔和风格——语气温和、体现关心、适合与学生直接交流的记录",
    "brief": "简洁简报风格——条理清晰、重点突出、适合内部汇报和快速阅读",
}


MAX_REF_FILES = 5
MAX_REF_SIZE_MB = 5


def parse_ref_file(filename: str, content: bytes) -> str:
    """解析参考文件内容为纯文本。"""
    name_lower = filename.lower()
    if name_lower.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    elif name_lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        texts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
        return "\n".join(texts)
    elif name_lower.endswith(".docx"):
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise ValueError(f"不支持的文件格式: {filename}")


def store_ref_files(user_id: int, files: list[tuple[str, bytes]]) -> list[dict]:
    """存储参考文件到内存缓存，返回 ref_id 列表。"""
    if len(files) > MAX_REF_FILES:
        raise ValueError(f"最多上传 {MAX_REF_FILES} 个参考文件")

    results = []
    for filename, content in files:
        if len(content) > MAX_REF_SIZE_MB * 1024 * 1024:
            raise ValueError(f"{filename} 超过 {MAX_REF_SIZE_MB}MB 限制")
        if not filename.lower().endswith((".pdf", ".txt", ".docx")):
            raise ValueError(f"{filename} 格式不支持，仅支持 PDF/Word/TXT")

        text = parse_ref_file(filename, content)
        ref_id = uuid.uuid4().hex[:12]
        _ref_cache[ref_id] = {"filename": filename, "text": text, "user_id": user_id}
        results.append({"ref_id": ref_id, "filename": filename, "chars": len(text)})

    return results


def get_ref_texts(user_id: int, ref_ids: list[str]) -> str:
    """获取参考文件文本拼接。"""
    texts = []
    for rid in ref_ids:
        cached = _ref_cache.get(rid)
        if cached and cached["user_id"] == user_id:
            texts.append(f"### 参考文件: {cached['filename']}\n{cached['text']}")
        else:
            texts.append(f"### 参考文件: (已过期)\n[文件内容不可用]")
    return "\n\n---\n\n".join(texts)


def generate_doc(
    db: Session,
    user_id: int,
    template_id: int,
    variables: dict,
    style: str | None = None,
    reference_ids: list[str] | None = None,
) -> DocTask:
    """生成文稿并保存任务记录。同步执行（MVP 阶段）。"""
    # 获取模板
    tmpl = get_template(db, template_id)
    if tmpl is None:
        raise ValueError("模板不存在")

    use_style = style or tmpl.style or "formal"
    var_names = json.loads(tmpl.variables) if tmpl.variables else []

    # 创建任务记录
    task = DocTask(
        user_id=user_id,
        template_id=template_id,
        template_name=tmpl.name,
        style=use_style,
        variables_json=json.dumps(variables, ensure_ascii=False),
        status="generating",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        # 构建 prompt
        fill_lines = []
        for v in var_names:
            val = variables.get(v, f"【{v}】")
            fill_lines.append(f"- {v}: {val}")
        fill_info = "\n".join(fill_lines) if fill_lines else "无特定填写信息"

        user_prompt = tmpl.user_prompt_template.format(**{v: variables.get(v, f"【{v}】") for v in var_names})

        system_prompt = tmpl.system_prompt or (
            f"你是一位高校学工领域的专业文书撰写助手。请根据用户要求和模板格式生成规范文书。"
            f"文风要求：{STYLE_DESC.get(use_style, '正式风格')}"
        )

        # 如果有参考文件，拼入 prompt
        if reference_ids:
            ref_text = get_ref_texts(user_id, reference_ids)
            if ref_text:
                user_prompt = (
                    f"以下为参考文件内容，请借鉴其风格、用词、结构和要点来撰写文稿：\n\n"
                    f"{ref_text}\n\n"
                    f"---\n\n"
                    f"以下是正式任务：\n{user_prompt}"
                )

        # 调用模型
        if not settings.dashscope_api_key:
            raise RuntimeError("API Key 未配置")

        resp = Generation.call(
            model="qwen-plus",
            api_key=settings.dashscope_api_key,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            result_format="message",
        )

        if resp.status_code != 200:
            task.status = "failed"
            task.content = f"模型调用失败: {resp.code} - {resp.message}"
            db.commit()
            raise RuntimeError(task.content)

        content = resp.output.choices[0].message.content

        # 更新任务
        task.status = "done"
        task.content = content
        db.commit()
        db.refresh(task)

        # 操作日志
        log = OperationLog(
            user_id=user_id,
            action="generate_doc",
            detail=f"生成文稿: {tmpl.name}",
        )
        db.add(log)
        db.commit()

        return task

    except Exception as e:
        if task.status != "failed":
            task.status = "failed"
            task.content = str(e)[:500]
            db.commit()
        raise


def export_docx(content: str, template_name: str) -> bytes:
    """将文稿内容导出为 .docx 文件。"""
    doc = Document()
    doc.styles["Normal"].font.name = "SimSun"
    doc.styles["Normal"].font.size = 150000  # 15pt in EMU

    title = doc.add_heading(template_name, level=0)
    title.alignment = 1  # 居中

    # 按段落分割
    paragraphs = content.split("\n")
    for para_text in paragraphs:
        para_text = para_text.strip()
        if not para_text:
            continue
        # 检测标题
        if para_text.startswith("## "):
            doc.add_heading(para_text[3:], level=2)
        elif para_text.startswith("# "):
            doc.add_heading(para_text[2:], level=1)
        elif para_text.startswith("**") and para_text.endswith("**"):
            p = doc.add_paragraph()
            run = p.add_run(para_text.strip("*"))
            run.bold = True
        else:
            doc.add_paragraph(para_text)

    # 底部免责
    doc.add_paragraph("")
    disclaimer = doc.add_paragraph()
    disclaimer_run = disclaimer.add_run("⚠️ 本文件由 AI 生成，仅为草稿，涉及学生/思政/危机材料必须人工复核。")
    disclaimer_run.font.size = 120000
    disclaimer_run.italic = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def get_user_tasks(db: Session, user_id: int, limit: int = 20) -> list[DocTask]:
    return (
        db.query(DocTask)
        .filter(DocTask.user_id == user_id)
        .order_by(DocTask.created_at.desc())
        .limit(limit)
        .all()
    )