"""公开文件下载端点测试。

无需 pytest，可直接运行::

    uv run python tests/test_files_api.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import files
from app.core.database import get_db
from app.models.document import Document


class FakeSession:
    """只实现 db.get 的最小异步会话替身。"""

    def __init__(self, doc: Document | None) -> None:
        self._doc = doc

    async def get(self, model, pk):
        assert model is Document, f"期望查询 Document，实际查询 {model}"
        return self._doc


def _make_client(doc: Document | None) -> TestClient:
    """把 files 路由挂到独立 FastAPI 实例（无 lifespan，不连库），覆盖 get_db。"""
    app = FastAPI()
    app.include_router(files.router)
    app.dependency_overrides[get_db] = lambda: FakeSession(doc)
    return TestClient(app)


def _make_doc(storage_path: str) -> Document:
    return Document(
        id=1,
        knowledge_base_id=1,
        filename="校园手册.txt",
        storage_path=storage_path,
        file_type="txt",
        mime_type="text/plain",
        file_size=2,
        file_hash="deadbeef",
    )


def test_download_success():
    """文档与文件都存在时返回 attachment 下载响应。"""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a.txt"
        f.write_text("你好", encoding="utf-8")
        client = _make_client(_make_doc(str(f)))
        resp = client.get("/api/files/1")
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert resp.headers.get("content-type", "").startswith("text/plain")
        assert resp.content == "你好".encode("utf-8")


def test_download_doc_not_found():
    """文档记录不存在返回 404 业务错误。"""
    client = _make_client(None)
    resp = client.get("/api/files/404")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FILE_NOT_FOUND"


def test_download_file_missing_on_disk():
    """文档记录在但文件已落盘丢失返回 404。"""
    with tempfile.TemporaryDirectory() as tmp:
        gone = Path(tmp) / "gone.txt"
        client = _make_client(_make_doc(str(gone)))
        resp = client.get("/api/files/1")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "FILE_NOT_FOUND"


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
