"""知识库删除级联测试。

删除知识库(kb)的聚合契约:
- 其下全部文档连同 切片/来源引用/向量/物理文件 一并删除
- 会话(conversations.knowledge_base_id 外键)与知识库解绑但保留历史
依赖真实 PostgreSQL 外键约束(均无 ON DELETE CASCADE)。

测试通过 NoCommitSession 把路由内部的 commit 降级为 flush,全程可回滚,不污染开发库。

无需 pytest，可直接运行::

    uv run python tests/test_knowledge_delete.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete as sql_delete, func, select

from app.core.database import async_session, engine, get_db
from app.api.deps import get_current_admin
from app.models.conversation import Conversation
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


class NoCommitSession:
    """委托真实会话,但把 commit 降级为 flush,让带 commit 的路由也能整体回滚。"""

    def __init__(self, session) -> None:
        self._s = session

    def __getattr__(self, name):
        return getattr(self._s, name)

    async def commit(self) -> None:
        await self._s.flush()


async def _seed(db) -> tuple[int, int, int]:
    """插入 kb → 文档 → 切片 → 问答记录/来源 → 绑定该 kb 的会话,返回 (kb_id, doc_id, chunk_id)。"""
    kb = KnowledgeBase(name="delete-kb-test")
    db.add(kb)
    await db.flush()

    doc = Document(
        knowledge_base_id=kb.id,
        filename="delete-kb-test.txt",
        storage_path=str(Path(tempfile.gettempdir()) / "delete-kb-test-not-exist.txt"),
        file_type="txt",
        mime_type="text/plain",
        file_size=3,
        file_hash="0" * 64,
    )
    db.add(doc)
    await db.flush()

    chunk = DocumentChunk(document_id=doc.id, chunk_index=0, content="知识库删除测试切片")
    db.add(chunk)
    await db.flush()

    rec = QaRecord(
        conversation_id="11111111-1111-1111-1111-111111111111",
        turn_index=1,
        knowledge_base_id=kb.id,
        question="kb-del-test-q",
        answer="答",
        model_name="test-model",
    )
    db.add(rec)
    await db.flush()

    db.add(QaSource(qa_record_id=rec.id, chunk_id=chunk.id, similarity_score=0.9, source_order=1))
    db.add(Conversation(id="22222222-2222-2222-2222-222222222222", client_id="test-client",
                        knowledge_base_id=kb.id, title="kb-del-test-conv"))
    await db.flush()
    return kb.id, doc.id, chunk.id


async def _cleanup(db) -> None:
    """按标记清理种子数据(问答记录/会话不随聚合删除,单独处理)并提交。"""
    await db.execute(sql_delete(QaRecord).where(QaRecord.question == "kb-del-test-q"))
    await db.execute(sql_delete(Conversation).where(Conversation.title == "kb-del-test-conv"))
    await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "delete-kb-test"))
    await db.commit()


async def _call_delete_endpoint(db, kb_id: int, fake: FakeRetriever):
    from httpx import ASGITransport, AsyncClient

    from fastapi import FastAPI
    from app.api.routes import knowledge as knowledge_route

    async def _shared_db():
        yield NoCommitSession(db)

    app = FastAPI()
    app.include_router(knowledge_route.router)
    app.state.retriever = fake
    app.dependency_overrides[get_db] = _shared_db
    app.dependency_overrides[get_current_admin] = lambda: object()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.delete(f"/api/knowledge-bases/{kb_id}")


def test_delete_kb_cascades_documents_and_unbinds_conversations():
    """删除知识库时:其下文档/切片/来源引用级联删除,会话解绑(kb 置空)但保留。"""

    async def scenario():
        async with async_session() as db:
            try:
                kb_id, doc_id, chunk_id = await _seed(db)
                resp = await _call_delete_endpoint(db, kb_id, FakeRetriever())
                assert resp.status_code == 200, f"删除知识库应成功,实际 {resp.status_code} {resp.text}"
                assert resp.json()["success"] is True

                assert await db.get(KnowledgeBase, kb_id) is None, "知识库行应被删除"
                assert await db.get(Document, doc_id) is None, "其下文档应被级联删除"
                remain_chunks = (
                    await db.execute(
                        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_id)
                    )
                ).scalar()
                assert remain_chunks == 0, "文档切片应被级联删除"
                # 只看被删切片的引用行(全局可能有真实问答产生的来源)
                remain_sources = (
                    await db.execute(select(func.count(QaSource.id)).where(QaSource.chunk_id == chunk_id))
                ).scalar()
                assert remain_sources == 0, "被删切片的来源引用应被级联删除"

                conv = await db.get(Conversation, "22222222-2222-2222-2222-222222222222")
                assert conv is not None, "会话历史应保留"
                assert conv.knowledge_base_id is None, "会话应与知识库解绑"
            finally:
                await db.rollback()
                await _cleanup(db)
                await engine.dispose()

    asyncio.run(scenario())


def test_delete_kb_cleans_document_vectors():
    """删除知识库时,其下文档的 Qdrant 向量按 chunk ID 一并清理。"""

    async def scenario():
        async with async_session() as db:
            try:
                kb_id, doc_id, chunk_id = await _seed(db)
                fake = FakeRetriever()
                resp = await _call_delete_endpoint(db, kb_id, fake)
                assert resp.status_code == 200, f"删除知识库应成功,实际 {resp.status_code} {resp.text}"
                assert fake.deleted == [[chunk_id]], f"应按 chunk ID 清理向量,实际 {fake.deleted}"
            finally:
                await db.rollback()
                await _cleanup(db)
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
