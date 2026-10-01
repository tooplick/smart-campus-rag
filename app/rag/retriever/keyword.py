from __future__ import annotations

import re

import jieba
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.models.blocks import RetrievalResult

# 中文连续串:补 bigram 兜底,防 jieba 误切专名
_CJK_RUN = re.compile(r"[一-鿿]{2,}")
_VALID = re.compile(r"[A-Za-z0-9一-鿿]")


def segment_query(query: str) -> list[str]:
    """切查询词:保留 ≥2 字的词/ASCII 词,附中文 bigram,去重;词即精确匹配单元。"""
    q = query.strip()
    if not q:
        return []
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        t = term.strip()
        if len(t) >= 2 and t not in seen and _VALID.search(t):
            seen.add(t)
            terms.append(t)

    for t in jieba.cut_for_search(q):
        add(t)
    for run in _CJK_RUN.findall(q):
        for i in range(len(run) - 1):
            add(run[i:i + 2])
    add(q)
    return terms


def _like_pattern(term: str) -> str:
    """ILIKE 模式,转义 % _ \ 通配符。"""
    escaped = term.replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")
    return f"%{escaped}%"


async def keyword_search(
    db: AsyncSession,
    query: str,
    knowledge_base_id: int | None = None,
    *,
    limit: int = 8,
) -> list[tuple[RetrievalResult, float]]:
    """关键词路检索:命中词按词长加权,整句完全包含给满分。

    专有名词/术语/编号等精确词的召回由本路负责;错别字的语义兜底交给向量路。
    """
    q = query.strip()
    terms = segment_query(q)
    if not terms:
        return []

    stmt = select(DocumentChunk, Document).join(
        Document, Document.id == DocumentChunk.document_id
    )
    if knowledge_base_id is not None:
        stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)
    patterns = [_like_pattern(t) for t in terms]
    if q:
        patterns.append(_like_pattern(q))
    stmt = stmt.where(or_(*[DocumentChunk.content.ilike(p, escape="\\") for p in patterns]))

    rows = (await db.execute(stmt)).all()
    total_w = sum(len(t) for t in terms) or 1

    scored: list[tuple[DocumentChunk, Document, float]] = []
    for chunk, doc in rows:
        content = (chunk.content or "").lower()
        if q and q.lower() in content:
            score = 1.0  # 整句完全包含:关键词路满分
        else:
            matched = sum(len(t) for t in terms if t.lower() in content)
            score = matched / total_w
        if score > 0:
            scored.append((chunk, doc, score))

    scored.sort(key=lambda x: -x[2])
    results: list[tuple[RetrievalResult, float]] = []
    for chunk, doc, score in scored[:limit]:
        results.append((RetrievalResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            knowledge_base_id=doc.knowledge_base_id,
            score=score,
            content=chunk.content,
            content_type=chunk.content_type,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            chunk_index=chunk.chunk_index,
        ), score))
    return results


def fuse_scores(vec: float | None, kw: float | None, *, vector_weight: float) -> float:
    """按存在的路归一化加权平均:纯路保持原分,双路为加权平均。

    纯向量命中的融合分等于原余弦分——相似度阈值的语义与旧配置保持兼容。
    """
    w = min(max(vector_weight, 0.0), 1.0)
    num = 0.0
    den = 0.0
    if vec is not None:
        num += w * vec
        den += w
    if kw is not None:
        num += (1.0 - w) * kw
        den += 1.0 - w
    return num / den if den > 0 else 0.0


def fuse_results(
    dense: list[RetrievalResult],
    keyword: list[tuple[RetrievalResult, float]],
    *,
    vector_weight: float,
) -> list[RetrievalResult]:
    """合并两路结果:同切片取融合分,按分数降序;融合分写入 score 字段。"""
    vec_by_id = {r.chunk_id: r for r in dense}
    kw_by_id = {r.chunk_id: (r, s) for r, s in keyword}

    out: list[RetrievalResult] = []
    for cid in set(vec_by_id) | set(kw_by_id):
        result = vec_by_id.get(cid) or kw_by_id[cid][0]
        vec = vec_by_id[cid].score if cid in vec_by_id else None
        kw = kw_by_id[cid][1] if cid in kw_by_id else None
        result.score = fuse_scores(vec, kw, vector_weight=vector_weight)
        out.append(result)
    out.sort(key=lambda r: -r.score)
    return out
