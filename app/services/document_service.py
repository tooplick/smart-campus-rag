from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
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
            raise ValueError(f"Unsupported file type. Allowed: PDF, DOCX, TXT")

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

    async def delete(self, doc_id: int) -> bool:
        doc = await self.db.get(Document, doc_id)
        if not doc:
            return False

        # Delete physical file
        if doc.storage_path and Path(doc.storage_path).exists():
            Path(doc.storage_path).unlink()

        await self.db.delete(doc)
        await self.db.flush()
        return True

    async def update_status(self, doc_id: int, status: str, progress: int = 0, error_message: str | None = None):
        doc = await self.db.get(Document, doc_id)
        if not doc:
            return
        doc.status = status
        doc.progress = progress
        if error_message:
            doc.error_message = error_message
        if status == "completed":
            doc.processed_at = datetime.now(timezone.utc)
        await self.db.flush()
