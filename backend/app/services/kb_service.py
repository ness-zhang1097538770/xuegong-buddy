"""知识库服务：文档上传、分段、向量化。"""

import json
import os
import re
import uuid
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.operation_log import OperationLog
from app.services.embedding_service import get_embeddings

import chromadb


def _get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.chroma_path)


def _get_or_create_collection(kb_id: int):
    client = _get_chroma_client()
    name = f"kb_{kb_id}"
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(name, metadata={"hnsw:space": "cosine"})


def _extract_text(file_path: str, file_type: str) -> str:
    """从文件提取文本内容。"""
    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif file_type == "pdf":
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n".join(text_parts)
    elif file_type == "docx":
        # python-docx 在此阶段暂不完全启用，返回空并标记
        raise NotImplementedError("docx 解析将在后续阶段支持")
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def _chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> list[str]:
    """简单固定长度分段。"""
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # 先按段落分割
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) < chunk_size:
            current += para + "\n"
        else:
            if current:
                chunks.append(current.strip())
            current = para + "\n"
    if current:
        chunks.append(current.strip())

    # 对于特别长的段落再按字符切
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            # 按 chunk_size 切，带重叠
            start = 0
            while start < len(chunk):
                end = min(start + chunk_size, len(chunk))
                final_chunks.append(chunk[start:end].strip())
                start += chunk_size - chunk_overlap

    return final_chunks


def _safe_filename(filename: str) -> str:
    """安全文件名，防止路径遍历。"""
    # 只保留文件名部分，去掉路径
    name = Path(filename).name
    # 只允许字母数字汉字和下划线点号横线
    name = re.sub(r"[^\w\u4e00-\u9fff.\-]", "_", name)
    if not name or name.startswith("."):
        name = f"file_{uuid.uuid4().hex[:8]}"
    return name


def ensure_user_kb(db: Session, user_id: int) -> KnowledgeBase:
    """确保用户有个人知识库，没有则创建。"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.owner_id == user_id,
        KnowledgeBase.kb_type == "personal",
    ).first()
    if kb is None:
        kb = KnowledgeBase(name="我的知识库", kb_type="personal", owner_id=user_id)
        db.add(kb)
        db.commit()
        db.refresh(kb)
    return kb


def upload_document(db: Session, user_id: int, file_content: bytes, filename: str) -> Document:
    """上传文档：保存文件、记录、异步向量化（同步实现）。"""
    # 校验文件大小
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_content) > max_bytes:
        raise ValueError(f"文件大小超过 {settings.max_upload_size_mb}MB 限制")

    # 安全文件名
    safe_name = _safe_filename(filename)
    file_type = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if file_type not in settings.allowed_upload_types:
        raise ValueError(f"不支持的文件格式: .{file_type}")

    # 确保知识库存在
    kb = ensure_user_kb(db, user_id)

    # 保存文件
    user_dir = Path(settings.upload_dir) / str(user_id) / str(uuid.uuid4().hex[:8])
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 创建文档记录
    doc = Document(
        kb_id=kb.id,
        filename=safe_name,
        file_path=str(file_path.absolute()),
        file_type=file_type,
        status="uploaded",
        size_bytes=len(file_content),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 操作日志
    log = OperationLog(
        user_id=user_id,
        action="upload_doc",
        detail=f"上传文档 {safe_name}",
    )
    db.add(log)
    db.commit()

    # 异步向量化（MVP 同步实现）
    _vectorize_document(db, doc)

    return doc


def _vectorize_document(db: Session, doc: Document):
    """将文档分段并向量化入库。"""
    try:
        # 更新状态
        doc.status = "chunking"
        db.commit()

        # 提取文本
        text = _extract_text(doc.file_path, doc.file_type)
        chunks = _chunk_text(text)

        if not chunks:
            doc.status = "failed"
            doc.error_message = "文档无可提取的文本内容"
            db.commit()
            return

        # 向量化
        doc.status = "vectorizing"
        db.commit()

        embeddings = get_embeddings(chunks)
        collection = _get_or_create_collection(doc.kb_id)

        # 存入 Chroma
        ids = [f"doc_{doc.id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": str(doc.id), "doc_name": doc.filename, "chunk_index": i}
            for i in range(len(chunks))
        ]
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        # 更新状态
        doc.status = "done"
        doc.chunk_count = len(chunks)
        db.commit()

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)[:500]
        db.commit()
        raise


def delete_document(db: Session, user_id: int, doc_id: int):
    """删除文档及关联向量。"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        raise ValueError("文档不存在")

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc.kb_id).first()
    if kb is None or kb.owner_id != user_id:
        raise PermissionError("无权删除此文档")

    # 删除磁盘文件
    try:
        os.remove(doc.file_path)
    except OSError:
        pass

    # 删除向量
    try:
        collection = _get_or_create_collection(doc.kb_id)
        ids_to_delete = [f"doc_{doc.id}_chunk_{i}" for i in range(doc.chunk_count)]
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
    except Exception:
        pass

    db.delete(doc)
    db.commit()


def get_user_documents(db: Session, user_id: int, status: str | None = None) -> list[Document]:
    """获取用户文档列表。"""
    kb = ensure_user_kb(db, user_id)
    query = db.query(Document).filter(Document.kb_id == kb.id)
    if status:
        query = query.filter(Document.status == status)
    return query.order_by(Document.created_at.desc()).all()