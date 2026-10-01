"""DocumentService.delete 级联删除测试。

覆盖「删除文档」聚合契约:按外键依赖顺序删除
qa_sources → document_chunks → documents 行,并按 chunk ID 清理 Qdrant 向量
(chunk ID 即 Qdrant 点 ID)。依赖真实 PostgreSQL 外键约束
(document_chunks.document_id 与 qa_sources.chunk_id 均无 ON DELETE CASCADE)。

测试全程使用事务并回滚,不污染开发库。

无需 pytest，可直接运行::

    uv run python tests/test_document_delete.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.core.database import async_session, engine, get_db
from app.api.deps import get_current_admin
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.qa_record import QaRecord
from app.models.qa_source import QaSource
from app.services.document_service import DocumentService


class FakeRetriever:
    """记录 delete_points 调用的向量库替身(仅实现被测契约)。"""

    def __init__(self) -> None:
        self.deleted: list[list[int]] = []

    async def delete_points(self, point_ids: list[int]) -> None:
        self.deleted.append(list(point_ids))


class FakeAsyncClient:
    """记录 delete 调用的 Qdrant 客户端替身。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[int]]] = []

    async def delete(self, *, collection_name: str, points_selector: list[int]) -> None:
        self.calls.append((collection_name, points_selector))


async def _seed(db) -> tuple[int, int, int]:
    """插入 KB → 文档 → 切片 → 问答记录 → 来源引用,返回 (doc_id, chunk_id, qa_source_id)。

    storage_path 指向不存在的文件,顺带验证「文件缺失不阻塞删除」。
    """
    kb = KnowledgeBase(name="delete-test-kb")
    db.add(kb)
    await db.flush()

    doc = Document(
        knowledge_base_id=kb.id,
        filename="delete-test.txt",
        storage_path=str(Path(tempfile.gettempdir()) / "delete-test-not-exist.txt"),
        file_type="txt",
        mime_type="text/plain",
        file_size=3,
        file_hash="0" * 64,
    )
    db.add(doc)
    await db.flush()

    chunk = DocumentChunk(document_id=doc.id, chunk_index=0, content="测试切片")
    db.add(chunk)
    await db.flush()

    rec = QaRecord(
        conversation_id="00000000-0000-0000-0000-000000000000",
        turn_index=1,
        knowledge_base_id=kb.id,
        question="问",
        answer="答",
        model_name="test-model",
    )
    db.add(rec)
    await db.flush()

    src = QaSource(qa_record_id=rec.id, chunk_id=chunk.id, similarity_score=0.9, source_order=1)
    db.add(src)
    await db.flush()
    return doc.id, chunk.id, src.id


def test_delete_cascades_chunks_and_sources():
    """有切片与来源引用的文档可删除,依赖行(切片/来源)随文档一并消失。"""

    async def scenario():
        async with async_session() as db:
            try:
                doc_id, chunk_id, src_id = await _seed(db)
                service = DocumentService(db)
                ok = await service.delete(doc_id)
                assert ok is True

                assert await db.get(Document, doc_id) is None, "文档行应被删除"
                remain_chunks = (
                    await db.execute(
                        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_id)
                    )
                ).scalar()
                assert remain_chunks == 0, "文档切片应被级联删除"
                remain_sources = (
                    await db.execute(select(func.count(QaSource.id)).where(QaSource.id == src_id))
                ).scalar()
                assert remain_sources == 0, "引用被删切片的 qa_sources 行应被删除"
                # 问答记录本身保留(历史),只去掉悬空引用
                rec_id = (
                    await db.execute(select(func.count(QaRecord.id)).where(QaRecord.question == "问"))
                ).scalar()
                assert rec_id == 1, "问答记录应保留"
            finally:
                await db.rollback()
                await engine.dispose()  # 断开连接池,避免共享连接跨 asyncio.run 事件循环复用

    asyncio.run(scenario())


def test_delete_removes_qdrant_points():
    """删除文档时按 chunk ID 清理 Qdrant 向量点。"""

    async def scenario():
        async with async_session() as db:
            try:
                doc_id, chunk_id, _ = await _seed(db)
                fake = FakeRetriever()
                service = DocumentService(db)
                ok = await service.delete(doc_id, retriever=fake)
                assert ok is True
                assert fake.deleted == [[chunk_id]], f"应按 chunk ID 删向量,实际 {fake.deleted}"
            finally:
                await db.rollback()
                await engine.dispose()  # 断开连接池,避免共享连接跨 asyncio.run 事件循环复用

    asyncio.run(scenario())


def test_delete_endpoint_cleans_vectors():
    """删除端点(DELETE /api/documents/{id})接入向量清理并成功返回业务包装。"""

    async def scenario():
        from httpx import ASGITransport, AsyncClient

        from fastapi import FastAPI
        from app.api.routes import documents as documents_route

        async with async_session() as db:
            try:
                doc_id, chunk_id, _ = await _seed(db)
                fake = FakeRetriever()

                async def _shared_db():
                    yield db

                app = FastAPI()
                app.include_router(documents_route.router)
                app.state.retriever = fake
                app.dependency_overrides[get_db] = _shared_db
                app.dependency_overrides[get_current_admin] = lambda: object()

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.delete(f"/api/documents/{doc_id}")

                assert resp.status_code == 200, f"删除应成功,实际 {resp.status_code} {resp.text}"
                body = resp.json()
                assert body["success"] is True, f"应返回业务成功包装,实际 {body}"
                assert fake.deleted == [[chunk_id]], f"端点应传递向量清理,实际 {fake.deleted}"
                assert await db.get(Document, doc_id) is None, "文档行应被删除"
            finally:
                await db.rollback()
                await engine.dispose()  # 断开连接池,避免共享连接跨 asyncio.run 事件循环复用

    asyncio.run(scenario())


def test_delete_points_delegates_and_skips_empty():
    """QdrantRetriever.delete_points:空列表不触达客户端,非空按点 ID 转发删除。"""

    async def scenario():
        from app.rag.retriever.qdrant import QdrantRetriever

        fake_client = FakeAsyncClient()
        retriever = QdrantRetriever(fake_client, "col")
        await retriever.delete_points([])
        assert fake_client.calls == [], "空列表不应触达客户端"
        await retriever.delete_points([7, 8])
        assert fake_client.calls == [("col", [7, 8])], f"应按点 ID 转发,实际 {fake_client.calls}"

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
