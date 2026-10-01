"""文档内联预览端点测试:GET /api/files/{id}/view(公开,聊天端来源弹层直接展示原文件)。

与下载端点同一文件,但 Content-Disposition 为 inline,浏览器可直接渲染(PDF/图片/文本)。

无需 pytest，可直接运行::

    uv run python tests/test_file_view.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Windows 控制台默认 GBK,统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import files
from app.core.database import get_db
from app.models.document import Document


class FakeSession:
    def __init__(self, doc: Document | None) -> None:
        self._doc = doc

    async def get(self, model, pk):
        return self._doc


def _make_client(doc: Document | None) -> TestClient:
    app = FastAPI()
    app.include_router(files.router)
    app.dependency_overrides[get_db] = lambda: FakeSession(doc)
    return TestClient(app)


def _make_doc(storage_path: str) -> Document:
    return Document(
        id=1, knowledge_base_id=1, filename="校园手册.txt", storage_path=storage_path,
        file_type="txt", mime_type="text/plain", file_size=2, file_hash="deadbeef",
    )


def test_file_view_inline():
    """原文以 inline 方式返回(浏览器可直接渲染),内容为文件本体。"""

    def scenario() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "a.txt"
            f.write_text("原始全文", encoding="utf-8")
            client = _make_client(_make_doc(str(f)))
            resp = client.get("/api/files/1/view")
            assert resp.status_code == 200
            assert "inline" in resp.headers.get("content-disposition", "")
            assert resp.text == "原始全文", "必须是文件本体,而非拼接内容"

    scenario()


def test_file_view_not_found():
    """文档或文件缺失返回 404。"""

    def scenario() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gone = Path(tmp) / "gone.txt"
            client = _make_client(_make_doc(str(gone)))
            resp = client.get("/api/files/1/view")
            assert resp.status_code == 404
            assert resp.json()["error"]["code"] == "FILE_NOT_FOUND"

    scenario()


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
