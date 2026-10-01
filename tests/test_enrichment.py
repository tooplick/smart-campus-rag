"""入库增强测试:auto-keywords / auto-questions。

切块入库时 LLM 生成关键词与候选问题,拼入嵌入文本(原文入库保持纯净,
增强内容记入 metadata_json);LLM 失败降级为纯正文嵌入,不阻塞入库。

无需 pytest，可直接运行::

    uv run python tests/test_enrichment.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# Windows 控制台默认 GBK,统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete as sql_delete, select

from app.core.database import async_session, engine
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.rag.config import RAGConfig


class FakeLLM:
    """返回固定 JSON 增强结果的 LLM 替身。"""

    model = "test-model"

    async def chat(self, messages, *, stream: bool = False, temperature=0.2, max_tokens=256):
        return {"choices": [{"message": {"content":
            '{"keywords": ["向量检索", "FastAPI"], "questions": ["什么是向量检索?"]}'
        }}], "usage": {}}


class FailingLLM:
    model = "test-model"

    async def chat(self, messages, *, stream: bool = False, temperature=0.2, max_tokens=256):
        raise RuntimeError("LLM 不可用")


class FakeEmbedding:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.texts.extend(texts)
        return [[0.1, 0.2] for _ in texts]


class FakeUpsertClient:
    async def upsert(self, *, collection_name: str, points) -> None:
        pass


class FakeRetriever:
    def __init__(self) -> None:
        self.client = FakeUpsertClient()
        self.collection = "test_col"
        self.deleted: list[list[int]] = []

    async def delete_points(self, point_ids: list[int]) -> None:
        self.deleted.append(list(point_ids))


def test_embed_text_for_includes_enrichment():
    """嵌入文本 = 正文 + 关键词 + 相关问题;缺失项不占位。"""

    def scenario() -> None:
        from app.rag.enrichment import embed_text_for

        full = embed_text_for("正文内容", ["向量检索", "FastAPI"], ["什么是向量检索?"])
        assert "正文内容" in full and "向量检索" in full and "什么是向量检索?" in full
        plain = embed_text_for("正文内容", [], [])
        assert plain.strip() == "正文内容", f"无增强应为纯正文,实际 {plain!r}"

    scenario()


def test_enrich_chunk_parses_json():
    """LLM JSON 输出解析为关键词/问题列表。"""

    async def scenario():
        from app.rag.enrichment import enrich_chunk

        meta = await enrich_chunk(FakeLLM(), "讲向量检索的切片", keywords=2, questions=1)
        assert meta["keywords"] == ["向量检索", "FastAPI"], f"实际 {meta}"
        assert meta["questions"] == ["什么是向量检索?"], f"实际 {meta}"

    asyncio.run(scenario())


def test_enrich_chunk_degrades_on_failure():
    """LLM 失败返回空元数据(降级),不抛异常。"""

    async def scenario():
        from app.rag.enrichment import enrich_chunk

        meta = await enrich_chunk(FailingLLM(), "任意切片", keywords=2, questions=1)
        assert meta == {}, f"失败应降级为空,实际 {meta}"

    asyncio.run(scenario())


def test_worker_embeds_enriched_text():
    """worker 入库:嵌入文本携带关键词/问题,切片 metadata 记录增强内容。"""

    async def scenario():
        from app.services.worker_service import DocumentWorker

        with tempfile.TemporaryDirectory() as tmp:
            txt = Path(tmp) / "enrich-test.txt"
            txt.write_text("智能校园知识库提供向量检索问答服务。" * 6, encoding="utf-8")

            async with async_session() as db:
                kb = KnowledgeBase(name="enrich-test")
                db.add(kb)
                await db.flush()
                doc = Document(
                    knowledge_base_id=kb.id, filename="enrich-test.txt", storage_path=str(txt),
                    file_type="txt", mime_type="text/plain", file_size=txt.stat().st_size,
                    file_hash="0" * 64, status="pending", progress=0,
                )
                db.add(doc)
                await db.flush()
                doc_id = doc.id
                await db.commit()

            emb = FakeEmbedding()
            try:
                worker = DocumentWorker(emb, FakeRetriever(), RAGConfig(), llm=FakeLLM())
                await worker._process_document(doc_id)
                assert any("向量检索" in t and "什么是向量检索?" in t for t in emb.texts), \
                    f"嵌入文本应携带增强内容,实际 {emb.texts}"
                async with async_session() as db:
                    rows = (await db.execute(
                        select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
                    )).scalars().all()
                    assert rows and rows[0].metadata_json.get("keywords") == ["向量检索", "FastAPI"], \
                        f"metadata 应记录增强内容,实际 {rows[0].metadata_json if rows else None}"
            finally:
                async with async_session() as db:
                    from app.services.document_service import DocumentService
                    await DocumentService(db).delete(doc_id, retriever=None)
                    # 防御:清掉历史泄漏(同名 KB 下的孤儿文档)后再删 KB
                    orphan_docs = (await db.execute(
                        select(Document.id).join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
                        .where(KnowledgeBase.name == "enrich-test")
                    )).scalars().all()
                    for oid in orphan_docs:
                        await DocumentService(db).delete(oid, retriever=None)
                    await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "enrich-test"))
                    await db.commit()
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
