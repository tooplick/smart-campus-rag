from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.models.blocks import RetrievalResult, Citation


async def build_citations(
    db: AsyncSession,
    results: list[RetrievalResult],
) -> list[Citation]:
    """Build citations from retrieval results, fetching document metadata from DB."""
    if not results:
        return []

    # Fetch all referenced documents
    doc_ids = list({r.document_id for r in results})
    stmt = select(Document).where(Document.id.in_(doc_ids))
    db_result = await db.execute(stmt)
    docs_by_id = {doc.id: doc for doc in db_result.scalars().all()}

    citations: list[Citation] = []
    for r in results:
        doc = docs_by_id.get(r.document_id)
        filename = doc.filename if doc else "unknown"
        citations.append(Citation(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            filename=filename,
            page_start=r.page_number,
            page_end=r.page_number,
            section_title=r.section_title,
            content=r.content[:200],
            score=r.score,
        ))

    return citations
