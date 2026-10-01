"""邻块扩展测试。

final top-k 命中后补齐同文档内前后相邻切片,让上下文跨越 chunk 边界连续;
扩展块继承命中的相似度,重叠命中去重,按 (document_id, chunk_index) 排序。
只读操作,全程事务回滚,不污染开发库。

无需 pytest，可直接运行::

    uv run python tests/test_neighbor_expansion.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Windows 控制台默认 GBK,统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import async_session, engine
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.rag.models.blocks import RetrievalResult


def _mk_result(chunk: DocumentChunk, kb_id: int, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        knowledge_base_id=kb_id,
        score=score,
        content=chunk.content,
        content_type="text",
        page_number=chunk.page_number,
        section_title=chunk.section_title,
        chunk_index=chunk.chunk_index,
    )


async def _seed(db) -> tuple[int, list[DocumentChunk]]:
    """插入 kb + 3 个连续切片的文档,返回 (kb_id, chunks)。"""
    kb = KnowledgeBase(name="expand-test")
    db.add(kb)
    await db.flush()

    doc = Document(
        knowledge_base_id=kb.id,
        filename="expand-test.txt",
        storage_path="not-exist.txt",
        file_type="txt",
        mime_type="text/plain",
        file_size=3,
        file_hash="0" * 64,
    )
    db.add(doc)
    await db.flush()

    chunks = []
    for i in range(3):
        c = DocumentChunk(document_id=doc.id, chunk_index=i, content=f"第 {i} 段内容")
        db.add(c)
        chunks.append(c)
    await db.flush()
    return kb.id, chunks


def test_expand_adds_neighbor_chunks():
    """单命中(chunk_index=0)扩出前后邻块,排序正确,扩展块继承锚点分值。"""

    async def scenario():
        from app.rag.retriever.expand import expand_neighbors

        async with async_session() as db:
            try:
                kb_id, chunks = await _seed(db)
                # 命中中间块,向前向后各扩 1 个
                hit = _mk_result(chunks[1], kb_id, score=0.9)
                expanded = await expand_neighbors(db, [hit], radius=1)

                assert len(expanded) == 3, f"应扩出 3 个切片,实际 {len(expanded)}"
                assert [r.chunk_index for r in expanded] == [0, 1, 2], "应按切片序排序"
                assert expanded[0].score == 0.9 and expanded[2].score == 0.9, "扩展块应继承命中分值"
                assert expanded[0].chunk_id == chunks[0].id and expanded[2].chunk_id == chunks[2].id
            finally:
                await db.rollback()
                await engine.dispose()

    asyncio.run(scenario())


def test_expand_dedupes_overlapping_hits():
    """相邻两个命中重叠扩展时,同一邻块只出现一次。"""

    async def scenario():
        from app.rag.retriever.expand import expand_neighbors

        async with async_session() as db:
            try:
                kb_id, chunks = await _seed(db)
                hits = [
                    _mk_result(chunks[0], kb_id, score=0.9),
                    _mk_result(chunks[1], kb_id, score=0.8),
                ]
                expanded = await expand_neighbors(db, hits, radius=1)

                ids = [r.chunk_id for r in expanded]
                assert len(ids) == len(set(ids)), f"结果应去重,实际 {ids}"
                assert sorted(r.chunk_index for r in expanded) == [0, 1, 2]
            finally:
                await db.rollback()
                await engine.dispose()

    asyncio.run(scenario())


def test_pipeline_includes_neighbors_in_retrievals():
    """管线装配验证:检索只命中 chunk 0,但邻块进入 retrievals/引用来源。"""

    async def scenario():
        from app.rag.config import RAGConfig
        from app.rag.pipeline import RAGPipeline

        class FakeEmbedding:
            async def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

        class FakeLLM:
            model = "test-model"

            async def chat(self, messages, *, stream: bool = False, temperature=0.2, max_tokens=512):
                return {"choices": [{"message": {"content": "回答"}}], "usage": {}}

        class FakeRetriever:
            def __init__(self, hit: RetrievalResult) -> None:
                self._hit = hit

            async def search(self, query_vector, *, knowledge_base_id=None, limit=8, score_threshold=None):
                return [self._hit]

        async with async_session() as db:
            try:
                kb_id, chunks = await _seed(db)
                pipeline = RAGPipeline(FakeEmbedding(), FakeLLM(), FakeRetriever(
                    _mk_result(chunks[0], kb_id, score=0.9)
                ), RAGConfig())
                answer = await pipeline.answer("第 0 段", kb_id, db)

                # 镜像真实案例:命中 chunk 0,续文在 chunk 1,radius=1 应把它带回来
                got = sorted(r.chunk_index for r in answer.retrievals)
                assert got == [0, 1], f"邻块应进入 retrievals,实际 {got}"
                assert len(answer.citations) == 2, f"邻块应成为引用来源,实际 {len(answer.citations)}"
            finally:
                await db.rollback()
                await engine.dispose()

    asyncio.run(scenario())


def main() -> int:
    tests = [
        obj
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            failed += 1
            print(f"FAIL {test.__name__}: {type(e).__name__}: {e}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
