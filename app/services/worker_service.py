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
from app.rag.parser.dispatch import get_parser
from app.rag.chunker.text_chunker import chunk_blocks
from app.rag.embedding.openai_compatible import OpenAICompatibleEmbedding
from app.rag.enrichment import embed_text_for, enrich_chunk
from app.rag.llm.openai_compatible import OpenAICompatibleLLM
from app.rag.retriever.qdrant import QdrantRetriever
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

WORKER_ID = uuid.uuid4().hex[:8]
MAX_ATTEMPTS = 3


class DocumentWorker:
    def __init__(
        self,
        embedding: OpenAICompatibleEmbedding,
        retriever: QdrantRetriever,
        config: RAGConfig | None = None,
        llm: OpenAICompatibleLLM | None = None,
        vision_config: dict | None = None,
    ):
        self.embedding = embedding
        self.retriever = retriever
        self.config = config or RAGConfig()
        self.llm = llm
        self.vision_config = vision_config
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

                # Parse:按文件类型分派解析器(图片走 Vision OCR,需已配置 Vision 模型)
                file_path = Path(doc.storage_path)
                parser = get_parser(doc.file_type, vision_config=self.vision_config)
                blocks = await parser.parse(file_path)
                await self._update_status(db, doc, "processing", 30)

                # Chunk
                # 按知识库配置的切块模板分派(对齐 RAGFlow 模板化切块)
                kb = await db.get(KnowledgeBase, doc.knowledge_base_id)
                template = (kb.chunk_template if kb else None) or "general"
                chunk_data_list = chunk_blocks(
                    blocks,
                    document_id=doc.id,
                    knowledge_base_id=doc.knowledge_base_id,
                    target_size=self.config.chunk_size,
                    overlap=self.config.chunk_overlap,
                    template=template,
                )
                await self._update_status(db, doc, "processing", 40)

                # 记录上一代切片 ID:旧内容保持可检索,待新内容就绪后在换代点原子替换
                service = DocumentService(db)
                old_chunk_ids = await service.get_chunk_ids(doc.id)

                # 入库增强(对齐 RAGFlow auto-keywords/auto-questions):失败降级纯正文
                if self.llm is not None and (self.config.auto_keywords > 0 or self.config.auto_questions > 0):
                    for cd in chunk_data_list:
                        meta = await enrich_chunk(
                            self.llm, cd.content,
                            keywords=self.config.auto_keywords,
                            questions=self.config.auto_questions,
                        )
                        if meta:
                            cd.metadata = {**(cd.metadata or {}), **meta}

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
                # 切片数随 60% 阶段一起可见,前端进度/计数同步更新
                doc.chunk_count = len(chunk_models)
                await self._update_status(db, doc, "processing", 60)

                # Embedding:正文 + 增强元数据拼入嵌入文本
                texts = [
                    embed_text_for(
                        c.content,
                        (c.metadata_json or {}).get("keywords", []),
                        (c.metadata_json or {}).get("questions", []),
                    )
                    for c in chunk_models
                ]
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

                # 换代点:新向量已就绪,删除上一代向量与行(行删除与新切片同事务原子提交,
                # 重建全程旧内容可检索,消除「重新处理期间知识库空窗」)
                await service.delete_chunks_by_ids(old_chunk_ids, retriever=self.retriever)

                # Update document(chunk_count 已在 60% 阶段记录)
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
        # 委托 DocumentService(即刻提交):阶段进度 10/30/40/60/80 对轮询端实时可见,
        # 否则整段处理在一个事务里,前端只见到 0 直接跳 100
        await DocumentService(db).update_status(doc.id, status, progress)
