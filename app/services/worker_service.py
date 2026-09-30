from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.rag.config import RAGConfig
from app.rag.models.blocks import DocumentChunkData
from app.rag.parser.txt import TxtParser
from app.rag.parser.pdf import PdfParser
from app.rag.chunker.text_chunker import chunk_blocks
from app.rag.embedding.openai_compatible import OpenAICompatibleEmbedding
from app.rag.retriever.qdrant import QdrantRetriever

logger = logging.getLogger(__name__)

WORKER_ID = uuid.uuid4().hex[:8]
MAX_ATTEMPTS = 3


class DocumentWorker:
    def __init__(
        self,
        embedding: OpenAICompatibleEmbedding,
        retriever: QdrantRetriever,
        config: RAGConfig | None = None,
    ):
        self.embedding = embedding
        self.retriever = retriever
        self.config = config or RAGConfig()
        self._running = False

    async def run(self, poll_interval: float = 5.0):
        """Main worker loop. Polls for pending documents."""
        self._running = True
        logger.info(f"DocumentWorker {WORKER_ID} started")
        while self._running:
            try:
                async with async_session() as db:
                    doc = await self._claim_document(db)
                    if doc:
                        await db.commit()
                        await self._process_document(doc.id)
                    else:
                        await asyncio.sleep(poll_interval)
            except Exception:
                logger.exception("Worker loop error")
                await asyncio.sleep(poll_interval)

    def stop(self):
        self._running = False

    async def _claim_document(self, db: AsyncSession) -> Document | None:
        """Claim a pending document using FOR UPDATE SKIP LOCKED."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Document)
            .where(Document.status == "pending")
            .order_by(Document.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = "processing"
            doc.locked_at = now
            doc.locked_by = WORKER_ID
            doc.attempt_count = (doc.attempt_count or 0) + 1
        return doc

    async def _process_document(self, doc_id: int):
        """Process a single document through the ingestion pipeline."""
        try:
            async with async_session() as db:
                doc = await db.get(Document, doc_id)
                if not doc:
                    return

                await self._update_status(db, doc, "processing", 10)

                # Parse
                file_path = Path(doc.storage_path)
                if doc.file_type == "txt":
                    parser = TxtParser()
                elif doc.file_type == "pdf":
                    parser = PdfParser()
                else:
                    raise ValueError(f"Unsupported file type: {doc.file_type}")

                blocks = await parser.parse(file_path)
                await self._update_status(db, doc, "processing", 30)

                # Chunk
                chunk_data_list = chunk_blocks(
                    blocks,
                    document_id=doc.id,
                    knowledge_base_id=doc.knowledge_base_id,
                    target_size=self.config.chunk_size,
                    overlap=self.config.chunk_overlap,
                )
                await self._update_status(db, doc, "processing", 40)

                # Save chunks to PostgreSQL
                chunk_models: list[DocumentChunk] = []
                for cd in chunk_data_list:
                    chunk = DocumentChunk(
                        document_id=cd.document_id,
                        chunk_index=cd.chunk_index,
                        content=cd.content,
                        content_type=cd.content_type,
                        page_number=cd.page_number,
                        section_title=cd.section_title,
                        start_char=cd.start_char,
                        end_char=cd.end_char,
                        token_count=cd.token_count,
                        metadata_json=cd.metadata,
                    )
                    db.add(chunk)
                    chunk_models.append(chunk)
                await db.flush()
                await self._update_status(db, doc, "processing", 60)

                # Embedding
                texts = [c.content for c in chunk_models]
                vectors = await self.embedding.embed(texts)
                await self._update_status(db, doc, "processing", 80)

                # Upsert to Qdrant
                from qdrant_client.models import PointStruct

                points = []
                for chunk, vector in zip(chunk_models, vectors):
                    points.append(
                        PointStruct(
                            id=chunk.id,
                            vector=vector,
                            payload={
                                "chunk_id": chunk.id,
                                "document_id": chunk.document_id,
                                "knowledge_base_id": doc.knowledge_base_id,
                                "content": chunk.content,
                                "chunk_index": chunk.chunk_index,
                                "content_type": chunk.content_type,
                                "page_number": chunk.page_number,
                                "section_title": chunk.section_title,
                            },
                        )
                    )
                await self.retriever.client.upsert(
                    collection_name=self.retriever.collection,
                    points=points,
                )

                # Update document
                doc.chunk_count = len(chunk_models)
                doc.status = "completed"
                doc.progress = 100
                doc.processed_at = datetime.now(timezone.utc)
                doc.locked_at = None
                doc.locked_by = None
                await db.commit()

                logger.info(f"Document {doc_id} processed: {len(chunk_models)} chunks")

        except Exception as e:
            logger.exception(f"Document {doc_id} processing failed")
            async with async_session() as db:
                doc = await db.get(Document, doc_id)
                if doc:
                    if doc.attempt_count >= MAX_ATTEMPTS:
                        doc.status = "failed"
                        doc.error_message = str(e)[:500]
                    else:
                        doc.status = "pending"
                    doc.locked_at = None
                    doc.locked_by = None
                    await db.commit()

    async def _update_status(
        self, db: AsyncSession, doc: Document, status: str, progress: int
    ):
        doc.status = status
        doc.progress = progress
        await db.flush()
