"""DocumentWorker 处理文档时的切片重建测试。

「重新处理」语义:处理文档 = 重建内容 —— 写入新切片前,
旧切片/来源引用/向量必须先被清理,不得累积两代切片。
Embedding 与 Qdrant 写入用替身,解析/切块/入库走真实实现。

需要真实 PostgreSQL;测试自带提交数据的清理逻辑。

无需 pytest，可直接运行::

    uv run python tests/test_worker_reprocess.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete as sql_delete, select

from app.core.database import async_session, engine
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.qa_record import QaRecord
from app.models.qa_source import QaSource
from app.rag.config import RAGConfig
from app.services.document_service import DocumentService
from app.services.worker_service import DocumentWorker


class FakeEmbedding:
    """返回固定维度向量的 Embedding 替身。"""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class FakeUpsertClient:
    def __init__(self) -> None:
        self.upserts: list[list[int]] = []

    async def upsert(self, *, collection_name: str, points) -> None:
        self.upserts.append([p.id for p in points])


class FakeRetriever:
    """记录向量写入与删除的检索器替身(兼容 worker 的 .client/.collection 直访问)。"""

    def __init__(self) -> None:
        self.client = FakeUpsertClient()
        self.collection = "test_col"
        self.deleted: list[list[int]] = []

    async def delete_points(self, point_ids: list[int]) -> None:
        self.deleted.append(list(point_ids))


async def _seed(tmp_dir: str):
    """插入 kb → 文档(指向真实临时 txt)→ 旧切片/来源,提交(供 worker 独立会话可见)。"""
    txt = Path(tmp_dir) / "worker-reprocess-test.txt"
    # 正文需超过切块器的 min_size(50 token,约 100 个汉字)才会产出切片
    long_text = "智能校园知识库面向全校师生提供智能问答服务。" * 6
    txt.write_text(long_text, encoding="utf-8")

    async with async_session() as db:
        kb = KnowledgeBase(name="worker-reprocess-test")
        db.add(kb)
        await db.flush()

        doc = Document(
            knowledge_base_id=kb.id,
            filename="worker-reprocess-test.txt",
            storage_path=str(txt),
            file_type="txt",
            mime_type="text/plain",
            file_size=txt.stat().st_size,
            file_hash="0" * 64,
            status="pending",
            progress=0,
        )
        db.add(doc)
        await db.flush()

        old_chunk = DocumentChunk(document_id=doc.id, chunk_index=0, content="旧切片内容")
        db.add(old_chunk)
        await db.flush()

        rec = QaRecord(
            conversation_id="33333333-3333-3333-3333-333333333333",
            turn_index=1,
            knowledge_base_id=kb.id,
            question="worker-reprocess-test-q",
            answer="答",
            model_name="test-model",
        )
        db.add(rec)
        await db.flush()
        db.add(QaSource(qa_record_id=rec.id, chunk_id=old_chunk.id, similarity_score=0.9, source_order=1))
        await db.commit()
        return kb.id, doc.id, old_chunk.id


async def _cleanup(doc_id: int) -> None:
    """清理测试数据(含 worker 提交的新切片)并提交。"""
    async with async_session() as db:
        await DocumentService(db).delete(doc_id, retriever=None)
        await db.execute(sql_delete(QaRecord).where(QaRecord.question == "worker-reprocess-test-q"))
        await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "worker-reprocess-test"))
        await db.commit()


def test_process_document_replaces_old_chunks():
    """处理文档前先清掉旧切片/来源/向量,新切片只保留一代。"""

    async def scenario():
        with tempfile.TemporaryDirectory() as tmp:
            kb_id, doc_id, old_chunk_id = await _seed(tmp)
            fake = FakeRetriever()
            try:
                worker = DocumentWorker(FakeEmbedding(), fake, RAGConfig())
                await worker._process_document(doc_id)

                async with async_session() as db:
                    assert await db.get(DocumentChunk, old_chunk_id) is None, "旧切片应被清理"
                    remain_sources = (
                        await db.execute(select(QaSource.id).where(QaSource.chunk_id == old_chunk_id))
                    ).scalars().all()
                    assert len(remain_sources) == 0, "旧来源引用应被清理"
                    assert fake.deleted == [[old_chunk_id]], f"旧向量应按 chunk ID 清理,实际 {fake.deleted}"

                    doc = await db.get(Document, doc_id)
                    assert doc is not None and doc.status == "completed", "文档应处理完成"
                    new_ids = (
                        await db.execute(
                            select(DocumentChunk.id).where(DocumentChunk.document_id == doc_id)
                        )
                    ).scalars().all()
                    assert len(new_ids) == doc.chunk_count > 0, "应只剩新一代切片"
                    for cid in new_ids:
                        assert cid != old_chunk_id
            finally:
                await _cleanup(doc_id)
                await engine.dispose()

    asyncio.run(scenario())


async def _seed_template(tmp_dir: str, template: str, text: str):
    """插入指定切块模板的 kb + 待处理文档,返回 (doc_id)。"""
    txt = Path(tmp_dir) / "template-test.txt"
    txt.write_text(text, encoding="utf-8")
    async with async_session() as db:
        kb = KnowledgeBase(name="worker-template-test", chunk_template=template)
        db.add(kb)
        await db.flush()
        doc = Document(
            knowledge_base_id=kb.id, filename="template-test.txt", storage_path=str(txt),
            file_type="txt", mime_type="text/plain", file_size=txt.stat().st_size,
            file_hash="0" * 64, status="pending", progress=0,
        )
        db.add(doc)
        await db.flush()
        await db.commit()
        return doc.id


def test_worker_respects_kb_chunk_template():
    """worker 按知识库的 chunk_template 分派切块(qa 模板产出问答对切片)。"""

    async def scenario():
        with tempfile.TemporaryDirectory() as tmp:
            text = "Q: 猫是什么?\nA: 猫是动物。\nQ: 狗是什么?\nA: 狗是动物。"
            doc_id = await _seed_template(tmp, "qa", text)
            try:
                worker = DocumentWorker(FakeEmbedding(), FakeRetriever(), RAGConfig())
                await worker._process_document(doc_id)
                async with async_session() as db:
                    rows = (await db.execute(
                        select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
                    )).scalars().all()
                    assert len(rows) == 2, f"qa 模板应产出问答对切片,实际 {len(rows)}"
                    assert "猫是什么" in rows[0].content and "狗是什么" in rows[1].content
            finally:
                async with async_session() as db:
                    await DocumentService(db).delete(doc_id, retriever=None)
                    await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "worker-template-test"))
                    await db.commit()
                    await engine.dispose()

    asyncio.run(scenario())


def test_update_status_clears_stale_error():
    """处理成功后旧错误信息必须清除,界面不得出现「已完成 + 陈旧红字」。"""

    async def scenario():
        from app.services.document_service import DocumentService

        async with async_session() as db:
            try:
                kb = KnowledgeBase(name="stale-err-test")
                db.add(kb)
                await db.flush()
                doc = Document(
                    knowledge_base_id=kb.id, filename="x.txt", storage_path="not-exist.txt",
                    file_type="txt", mime_type="text/plain", file_size=1, file_hash="0" * 64,
                    status="failed", error_message="旧错误",
                )
                db.add(doc)
                await db.flush()
                service = DocumentService(db)
                await service.update_status(doc.id, "completed", progress=100)
                await db.refresh(doc)
                assert doc.status == "completed"
                assert doc.error_message is None, f"成功后应清除错误信息,实际 {doc.error_message!r}"
            finally:
                await db.execute(sql_delete(Document).where(Document.filename == "x.txt"))
                await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "stale-err-test"))
                await db.commit()
                await engine.dispose()

    asyncio.run(scenario())


def test_update_status_commits_stage_progress():
    """阶段进度必须即刻提交:另一会话要能看到中间值(否则前端只见到 0 和 100)。"""

    async def scenario():
        from app.services.document_service import DocumentService

        async with async_session() as db:
            kb = KnowledgeBase(name="progress-test")
            db.add(kb)
            await db.flush()
            doc = Document(
                knowledge_base_id=kb.id, filename="progress-test.txt", storage_path="not-exist.txt",
                file_type="txt", mime_type="text/plain", file_size=1, file_hash="0" * 64,
                status="pending", progress=0,
            )
            db.add(doc)
            await db.flush()
            doc_id = doc.id
            await db.commit()

        try:
            async with async_session() as db:
                await DocumentService(db).update_status(doc_id, "processing", 40)
            # 独立会话模拟前端轮询:必须读到 40,而非提交前的 0
            async with async_session() as db:
                seen = await db.get(Document, doc_id)
                assert seen.progress == 40, f"阶段进度应即刻可见,实际 {seen.progress}"
                assert seen.status == "processing"
        finally:
            async with async_session() as db:
                await db.execute(sql_delete(Document).where(Document.filename == "progress-test.txt"))
                await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "progress-test"))
                await db.commit()
                await engine.dispose()

    asyncio.run(scenario())


def test_worker_stage_update_visible_to_pollers():
    """worker 自身的阶段进度写入(真实管线路径)必须即刻提交可轮询。"""

    async def scenario():
        async with async_session() as db:
            kb = KnowledgeBase(name="worker-progress-test")
            db.add(kb)
            await db.flush()
            doc = Document(
                knowledge_base_id=kb.id, filename="worker-progress-test.txt", storage_path="not-exist.txt",
                file_type="txt", mime_type="text/plain", file_size=1, file_hash="0" * 64,
                status="pending", progress=0,
            )
            db.add(doc)
            await db.flush()
            doc_id = doc.id
            await db.commit()

        try:
            worker = DocumentWorker(FakeEmbedding(), FakeRetriever(), RAGConfig())
            async with async_session() as db:
                doc = await db.get(Document, doc_id)
                await worker._update_status(db, doc, "processing", 40)
            async with async_session() as db:
                seen = await db.get(Document, doc_id)
                assert seen.progress == 40, f"worker 阶段进度应即刻可见,实际 {seen.progress}"
        finally:
            async with async_session() as db:
                await db.execute(sql_delete(Document).where(Document.filename == "worker-progress-test.txt"))
                await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "worker-progress-test"))
                await db.commit()
                await engine.dispose()

    asyncio.run(scenario())


def test_failed_rebuild_keeps_old_content_searchable():
    """重建失败/进行中不得丢失旧内容的可检索性:旧向量只在换代时刻删除。"""

    class FailingEmbedding:
        async def embed(self, texts):
            raise RuntimeError("嵌入服务不可用")

    async def scenario():
        with tempfile.TemporaryDirectory() as tmp:
            txt = Path(tmp) / "gap-test.txt"
            txt.write_text("智能校园知识库提供问答服务。" * 6, encoding="utf-8")
            async with async_session() as db:
                kb = KnowledgeBase(name="gap-test")
                db.add(kb)
                await db.flush()
                doc = Document(
                    knowledge_base_id=kb.id, filename="gap-test.txt", storage_path=str(txt),
                    file_type="txt", mime_type="text/plain", file_size=txt.stat().st_size,
                    file_hash="0" * 64, status="pending", progress=0,
                )
                db.add(doc)
                await db.flush()
                old_chunk = DocumentChunk(document_id=doc.id, chunk_index=0, content="旧切片内容")
                db.add(old_chunk)
                await db.flush()
                doc_id, old_id = doc.id, old_chunk.id
                await db.commit()

            fake = FakeRetriever()
            worker = DocumentWorker(FailingEmbedding(), fake, RAGConfig())
            try:
                await worker._process_document(doc_id)  # 嵌入失败 → 整段失败
                raise AssertionError("应失败")
            except Exception:
                pass
            try:
                assert fake.deleted == [], f"失败的重建不得删除旧向量,实际 {fake.deleted}"
                async with async_session() as db:
                    still = await db.get(DocumentChunk, old_id)
                    assert still is not None, "旧切片行应保留(回滚),文档保持可检索"
            finally:
                async with async_session() as db:
                    await DocumentService(db).delete(doc_id, retriever=None)
                    await db.execute(sql_delete(KnowledgeBase).where(KnowledgeBase.name == "gap-test"))
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
