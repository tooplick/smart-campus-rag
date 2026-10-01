"""混合检索测试:关键词路打分 + 融合公式 + 管线融合装配。

关键词路负责精确词(人名/术语/编号),错别字语义由向量路兜;
融合按存在的路归一化加权平均,纯向量命中保持原余弦分(阈值语义兼容)。
只读操作,全程事务回滚。

无需 pytest，可直接运行::

    uv run python tests/test_hybrid_retrieval.py
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


async def _seed(db) -> tuple[int, list[DocumentChunk]]:
    """插入 kb + 3 个切片:0 含人名与术语,1 含术语,2 无关。"""
    kb = KnowledgeBase(name="hybrid-test")
    db.add(kb)
    await db.flush()

    doc = Document(
        knowledge_base_id=kb.id,
        filename="hybrid-test.txt",
        storage_path="not-exist.txt",
        file_type="txt",
        mime_type="text/plain",
        file_size=3,
        file_hash="0" * 64,
    )
    db.add(doc)
    await db.flush()

    contents = [
        "唐星星的个人简介,擅长 FastAPI 与 Qdrant 向量检索。",
        "另一段介绍 FastAPI 网关的工程实践内容。",
        "完全无关的校园风景描写,秋天的银杏大道非常美。",
    ]
    chunks = []
    for i, content in enumerate(contents):
        c = DocumentChunk(document_id=doc.id, chunk_index=i, content=content)
        db.add(c)
        chunks.append(c)
    await db.flush()
    return kb.id, chunks


def _mk_result(chunk: DocumentChunk, kb_id: int, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        knowledge_base_id=kb_id,
        score=score,
        content=chunk.content,
        content_type="text",
        chunk_index=chunk.chunk_index,
    )


def test_keyword_search_exact_terms():
    """关键词路:命中词按词长加权,无关切片不返回。"""

    async def scenario():
        from app.rag.retriever.keyword import keyword_search

        async with async_session() as db:
            try:
                kb_id, chunks = await _seed(db)
                hits = await keyword_search(db, "唐星星 FastAPI", kb_id, limit=10)
                by_chunk = {r.chunk_id: score for r, score in hits}

                assert chunks[0].id in by_chunk, "含两个词的切片应命中"
                assert chunks[1].id in by_chunk, "含一个词的切片应命中"
                assert chunks[2].id not in by_chunk, "无关切片不应返回"
                assert by_chunk[chunks[0].id] > by_chunk[chunks[1].id], "命中词多者分高"
            finally:
                await db.rollback()
                await engine.dispose()

    asyncio.run(scenario())


def test_keyword_search_full_query_boost():
    """整句完全包含查询时关键词分为满分。"""

    async def scenario():
        from app.rag.retriever.keyword import keyword_search

        async with async_session() as db:
            try:
                kb_id, chunks = await _seed(db)
                hits = await keyword_search(db, "唐星星", kb_id, limit=10)
                by_chunk = {r.chunk_id: score for r, score in hits}
                assert by_chunk.get(chunks[0].id) == 1.0, f"完全包含应满分,实际 {by_chunk}"
            finally:
                await db.rollback()
                await engine.dispose()

    asyncio.run(scenario())


def test_fusion_normalizes_present_branches():
    """融合按存在的路归一:纯向量保持原分,纯关键词保持原分,双路为加权平均。"""

    def scenario() -> None:
        from app.rag.retriever.keyword import fuse_scores

        assert abs(fuse_scores(0.8, None, vector_weight=0.7) - 0.8) < 1e-9, "纯向量命中应保持原余弦分"
        assert abs(fuse_scores(None, 1.0, vector_weight=0.7) - 1.0) < 1e-9, "纯关键词命中应保持关键词分"
        mixed = fuse_scores(0.6, 1.0, vector_weight=0.7)
        assert abs(mixed - 0.72) < 1e-9, f"双路应为加权平均,实际 {mixed}"

    scenario()


def test_pipeline_hybrid_includes_keyword_only_hit():
    """管线装配:向量只命中无关块,关键词独有命中(人名)也必须进结果。"""

    async def scenario():
        from app.rag.config import RAGConfig
        from app.rag.pipeline import RAGPipeline

        class FakeEmbedding:
            async def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.1, 0.2] for _ in texts]

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
                # 向量路只给出无关块(chunk 2);问题含人名,关键词路应捞回 chunk 0
                pipeline = RAGPipeline(
                    FakeEmbedding(), FakeLLM(),
                    FakeRetriever(_mk_result(chunks[2], kb_id, score=0.4)),
                    RAGConfig(similarity_threshold=0.05),
                )
                answer = await pipeline.answer("唐星星", kb_id, db)

                got = {r.chunk_id for r in answer.retrievals}
                assert chunks[0].id in got, f"关键词独有命中应进结果,实际 {got}"
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
