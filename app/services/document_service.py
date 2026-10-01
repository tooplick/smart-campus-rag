from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.qa_source import QaSource
from app.rag.retriever.qdrant import QdrantRetriever
from app.models.knowledge_base import KnowledgeBase
from app.utils.file import (
    validate_file_extension,
    get_file_extension,
    generate_storage_path,
    compute_file_hash,
    get_mime_type,
    MAX_FILE_SIZE,
)


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_knowledge_base(self, kb_id: int | None = None) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc())
        if kb_id is not None:
            stmt = stmt.where(Document.knowledge_base_id == kb_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, doc_id: int) -> Document | None:
        return await self.db.get(Document, doc_id)

    async def upload(self, file, knowledge_base_id: int) -> Document:
        # Validate knowledge base exists
        kb = await self.db.get(KnowledgeBase, knowledge_base_id)
        if not kb:
            raise ValueError("Knowledge base not found")

        # Validate file
        if not validate_file_extension(file.filename):
            raise ValueError("不支持的文件类型,允许: PDF/DOCX/TXT/MD/CSV/XLSX/PPTX/HTML/图片")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB")

        # Save file
        storage_path = generate_storage_path(file.filename)
        with open(storage_path, "wb") as f:
            f.write(content)

        # Create document record
        doc = Document(
            knowledge_base_id=knowledge_base_id,
            filename=file.filename,
            storage_path=storage_path,
            file_type=get_file_extension(file.filename),
            mime_type=get_mime_type(file.filename),
            file_size=len(content),
            file_hash=compute_file_hash(storage_path),
            status="pending",
            progress=0,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_chunk_ids(self, doc_id: int) -> list[int]:
        """收集文档当前一代切片的 ID(chunk ID 即 Qdrant 点 ID)。"""
        result = await self.db.execute(
            select(DocumentChunk.id).where(DocumentChunk.document_id == doc_id)
        )
        return list(result.scalars().all())

    async def delete_chunks_by_ids(
        self, chunk_ids: list[int], retriever: QdrantRetriever | None = None
    ) -> None:
        """按 ID 删除一代切片/来源引用/向量(删除文档与重建换代共用)。

        向量先行删除:失败则整体中止且库内数据未动,可原样重试。
        行删除只 flush 不提交——换代场景与新切片的插入同事务原子落库。
        qa_sources.chunk_id 与 document_chunks.document_id 均无 ON DELETE CASCADE,
        必须按外键依赖顺序删除(qa_sources → document_chunks)。
        """
        if not chunk_ids:
            return
        if retriever is not None:
            await retriever.delete_points(chunk_ids)
        await self.db.execute(delete(QaSource).where(QaSource.chunk_id.in_(chunk_ids)))
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids)))

    async def clear_document_chunks(self, doc_id: int, retriever: QdrantRetriever | None = None) -> None:
        """清空文档的全部切片/来源引用/向量(删除文档用)。"""
        chunk_ids = await self.get_chunk_ids(doc_id)
        await self.delete_chunks_by_ids(chunk_ids, retriever=retriever)

    async def delete(self, doc_id: int, retriever: QdrantRetriever | None = None) -> bool:
        doc = await self.db.get(Document, doc_id)
        if not doc:
            return False
        storage_path = doc.storage_path

        # 切片/来源引用/向量由统一入口清理
        await self.clear_document_chunks(doc_id, retriever=retriever)
        await self.db.delete(doc)

        # 物理文件最后清理:缺失或被占用都不应阻塞记录删除
        if storage_path:
            try:
                Path(storage_path).unlink(missing_ok=True)
            except OSError:
                pass

        await self.db.flush()
        return True

    async def update_status(self, doc_id: int, status: str, progress: int = 0, error_message: str | None = None):
        doc = await self.db.get(Document, doc_id)
        if not doc:
            return
        doc.status = status
        doc.progress = progress
        # 错误信息跟随状态更新:成功时必须清除旧错误,避免「已完成 + 陈旧红字」
        doc.error_message = error_message
        if status == "completed":
            doc.processed_at = datetime.now(timezone.utc)
        # 阶段进度即刻提交:轮询端要能看到 10/30/40/60/80 的中间态,
        # 否则整段处理在一个事务里,前端只见到 0 直接跳 100
        await self.db.commit()
