"""重排模型测试:RerankProvider 响应解析 + 管线两级排序。

重排输入 = 融合候选池,输出按相关度重排后截断 final_top_k;
未配置重排时管线保持融合排序;重排失败时回退融合排序。

无需 pytest，可直接运行::

    uv run python tests/test_rerank.py
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

import httpx

from app.core.database import async_session, engine
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.rag.models.blocks import RetrievalResult


class FakeEmbedding:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class FakeLLM:
    model = "test-model"

    async def chat(self, messages, *, stream: bool = False, temperature=0.2, max_tokens=512):
        return {"choices": [{"message": {"content": "回答"}}], "usage": {}}


class FakeRetriever:
    def __init__(self, hits: list[RetrievalResult]) -> None:
        self._hits = hits

    async def search(self, query_vector, *, knowledge_base_id=None, limit=8, score_threshold=None):
        return list(self._hits)


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


async def _seed(db) -> tuple[int, list[DocumentChunk]]:
    kb = KnowledgeBase(name="rerank-test")
    db.add(kb)
    await db.flush()
    doc = Document(
        knowledge_base_id=kb.id, filename="rerank-test.txt", storage_path="not-exist.txt",
        file_type="txt", mime_type="text/plain", file_size=3, file_hash="0" * 64,
    )
    db.add(doc)
    await db.flush()
    chunks = []
    for i in range(3):
        c = DocumentChunk(document_id=doc.id, chunk_index=i, content=f"切片 {i} 内容")
        db.add(c)
        chunks.append(c)
    await db.flush()
    return kb.id, chunks


def test_rerank_provider_parses_response():
    """OpenAI 兼容 /rerank 响应解析:按相关度降序返回 (index, score)。"""

    async def scenario():
        from app.rag.rerank.openai_compatible import OpenAICompatibleRerank

        payload = {"results": [
            {"index": 2, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.7},
        ]}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = OpenAICompatibleRerank(
            "https://api.example.com/v1", "key", "bge-reranker-v2-m3", client=client,
        )
        out = await provider.rerank("问题", ["a", "b", "c"], top_n=2)
        assert out == [(2, 0.9), (0, 0.7)], f"应按相关度降序,实际 {out}"
        await client.aclose()

    asyncio.run(scenario())


def test_pipeline_rerank_reorders_and_cuts():
    """管线两级排序:融合分误导排序时,重排纠正顺序并截断 final_top_k。"""

    async def scenario():
        from app.rag.config import RAGConfig
        from app.rag.pipeline import RAGPipeline

        class FakeRerank:
            async def rerank(self, query, documents, *, top_n):
                # 与向量分相反的真实相关度:切片 2 最相关
                scores = [0.1, 0.5, 0.9]
                return sorted(enumerate(scores), key=lambda x: -x[1])

        async with async_session() as db:
            try:
                kb_id, chunks = await _seed(db)
                hits = [
                    _mk_result(chunks[0], kb_id, score=0.9),  # 向量分最高但语义最不相关
                    _mk_result(chunks[1], kb_id, score=0.5),
                    _mk_result(chunks[2], kb_id, score=0.1),
                ]
                pipeline = RAGPipeline(
                    FakeEmbedding(), FakeLLM(), FakeRetriever(hits),
                    # final_top_k=1:未重排会选中向量分最高的切片 0;重排应选中切片 2
                    RAGConfig(similarity_threshold=0.01, final_top_k=1),
                    rerank=FakeRerank(),
                )
                answer = await pipeline.answer("问题", kb_id, db)
                got = {r.chunk_id for r in answer.retrievals}
                assert chunks[2].id in got, f"重排第一名应入选,实际 {got}"
                # 命中切片 2 后邻块扩展带回切片 1;落选且非邻块的切片 0 不应在内
                assert got == {chunks[1].id, chunks[2].id}, f"截断与扩展不符,实际 {got}"
            finally:
                await db.rollback()
                await engine.dispose()

    asyncio.run(scenario())


def test_pipeline_without_rerank_keeps_fused_order():
    """未配置重排时保持融合排序(既有行为不回归)。"""

    async def scenario():
        from app.rag.config import RAGConfig
        from app.rag.pipeline import RAGPipeline

        async with async_session() as db:
            try:
                kb_id, chunks = await _seed(db)
                hits = [
                    _mk_result(chunks[0], kb_id, score=0.9),
                    _mk_result(chunks[1], kb_id, score=0.5),
                ]
                pipeline = RAGPipeline(
                    FakeEmbedding(), FakeLLM(), FakeRetriever(hits),
                    RAGConfig(similarity_threshold=0.01),
                )
                answer = await pipeline.answer("问题", kb_id, db)
                got = [r.chunk_id for r in answer.retrievals]
                assert got[0] == chunks[0].id, f"无重排应保持融合序,实际 {got}"
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
