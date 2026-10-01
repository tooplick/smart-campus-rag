from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.rag.models.blocks import RetrievalResult


async def expand_neighbors(
    db: AsyncSession,
    results: list[RetrievalResult],
    *,
    radius: int = 1,
) -> list[RetrievalResult]:
    """邻块扩展:为每个命中切片补齐同文档内前后各 radius 个切片。

    解决 chunk 边界截断答案的问题——命中切片的续文常常在相邻切片里。
    扩展块继承命中的相似度(被多个命中拉入时取最高),不重复计入已命中块,
    最终按 (document_id, chunk_index) 排序返回,保证上下文阅读顺序连贯。
    """
    if not results or radius <= 0:
        return results

    hit_keys = {(r.document_id, r.chunk_index): r for r in results}
    kb_by_doc = {r.document_id: r.knowledge_base_id for r in results}

    # 文档 → {缺口切片序号: 锚点分值}
    wanted: dict[int, dict[int, float]] = {}
    for r in results:
        gaps = wanted.setdefault(r.document_id, {})
        for i in range(r.chunk_index - radius, r.chunk_index + radius + 1):
            if i < 0 or (r.document_id, i) in hit_keys:
                continue
            gaps[i] = max(gaps.get(i, 0.0), r.score)

    if not wanted:
        return list(results)

    stmt = select(DocumentChunk).where(DocumentChunk.document_id.in_(wanted.keys()))
    rows = (await db.execute(stmt)).scalars().all()

    merged = list(results)
    for row in rows:
        score = wanted.get(row.document_id, {}).get(row.chunk_index)
        if score is None:
            continue
        merged.append(RetrievalResult(
            chunk_id=row.id,
            document_id=row.document_id,
            knowledge_base_id=kb_by_doc[row.document_id],
            score=score,
            content=row.content,
            content_type=row.content_type,
            page_number=row.page_number,
            section_title=row.section_title,
            chunk_index=row.chunk_index,
        ))

    merged.sort(key=lambda r: (r.document_id, r.chunk_index))
    return merged
