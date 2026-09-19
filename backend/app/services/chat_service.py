from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.qa_record import QaRecord
from app.models.qa_source import QaSource
from app.rag.models.blocks import RagAnswer

logger = logging.getLogger(__name__)


class ChatService:
    async def validate_knowledge_base(self, db: AsyncSession, kb_id: int | None) -> tuple[bool, str]:
        """Validate knowledge base exists and has completed documents."""
        if kb_id is None:
            return True, ""

        kb = await db.get(KnowledgeBase, kb_id)
        if not kb:
            return False, "知识库不存在"
        if not kb.is_enabled:
            return False, "知识库已禁用"

        # Check for completed documents
        stmt = select(func.count(Document.id)).where(
            Document.knowledge_base_id == kb_id,
            Document.status == "completed",
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        if count == 0:
            # Check if any are processing
            stmt2 = select(func.count(Document.id)).where(
                Document.knowledge_base_id == kb_id,
                Document.status.in_(["pending", "processing"]),
            )
            result2 = await db.execute(stmt2)
            processing = result2.scalar() or 0
            if processing > 0:
                return False, "当前知识库正在建立索引，请稍后再试。"
            return False, "当前知识库暂无可用资料。"

        return True, ""

    async def save_qa_record(
        self,
        db: AsyncSession,
        conversation_id: str,
        turn_index: int,
        knowledge_base_id: int,
        question: str,
        rag_answer: RagAnswer,
    ) -> QaRecord:
        """Save QA record and sources to database."""
        record = QaRecord(
            conversation_id=conversation_id,
            turn_index=turn_index,
            knowledge_base_id=knowledge_base_id,
            question=question,
            answer=rag_answer.answer,
            model_name=rag_answer.model_name,
            retrieval_count=len(rag_answer.retrievals),
            latency_ms=rag_answer.latency_ms,
            prompt_tokens=rag_answer.usage.prompt_tokens if rag_answer.usage else 0,
            completion_tokens=rag_answer.usage.completion_tokens if rag_answer.usage else 0,
            total_tokens=rag_answer.usage.total_tokens if rag_answer.usage else 0,
            status="success",
            metadata_json=rag_answer.citations[0].__dict__ if rag_answer.citations else None,
        )
        db.add(record)
        await db.flush()

        # Save sources
        for i, citation in enumerate(rag_answer.citations):
            source = QaSource(
                qa_record_id=record.id,
                chunk_id=citation.chunk_id,
                similarity_score=citation.score,
                source_order=i + 1,
            )
            db.add(source)

        await db.flush()
        return record

    async def get_conversation_turn_index(self, db: AsyncSession, conversation_id: str) -> int:
        """Get the next turn index for a conversation."""
        stmt = select(func.max(QaRecord.turn_index)).where(
            QaRecord.conversation_id == conversation_id
        )
        result = await db.execute(stmt)
        max_idx = result.scalar()
        return (max_idx or 0) + 1

    async def get_conversation_history(
        self, db: AsyncSession, conversation_id: str, max_turns: int = 5
    ) -> list[dict]:
        """Get recent conversation history for multi-turn context."""
        stmt = (
            select(QaRecord)
            .where(QaRecord.conversation_id == conversation_id)
            .order_by(QaRecord.turn_index.desc())
            .limit(max_turns)
        )
        result = await db.execute(stmt)
        records = list(result.scalars().all())
        records.reverse()

        messages: list[dict] = []
        for r in records:
            messages.append({"role": "user", "content": r.question})
            messages.append({"role": "assistant", "content": r.answer})
        return messages
