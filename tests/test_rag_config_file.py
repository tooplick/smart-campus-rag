"""rag-config 文件化测试:GET 合并默认值、PUT 落盘并热更新运行中 RAGConfig。

无需 pytest,可直接运行::

    uv run python tests/test_rag_config_file.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.api.routes import admin
from app.core.app_config import AppConfigStore, get_app_config
from app.rag.config import RAGConfig


def _client(tmp: str) -> tuple[TestClient, RAGConfig]:
    store = AppConfigStore(Path(tmp) / "app-config.yaml")
    live = RAGConfig()
    app = FastAPI()
    app.include_router(admin.router)
    app.state.rag_config = live
    app.dependency_overrides[get_current_admin] = lambda: object()
    app.dependency_overrides[get_app_config] = lambda: store
    return TestClient(app), live


def test_get_defaults_put_persists_and_hot_updates():
    with tempfile.TemporaryDirectory() as tmp:
        c, live = _client(tmp)
        r = c.get("/api/admin/rag-config")
        assert r.json()["data"]["chunk_size"] == 600, r.text
        r = c.put("/api/admin/rag-config", json={"chunk_size": 800, "similarity_threshold": 0.75})
        assert r.json()["success"], r.text
        assert r.json()["data"]["chunk_size"] == 800
        assert live.chunk_size == 800 and live.similarity_threshold == 0.75  # 热更新
        # 重启语义:新读取也拿到文件值
        r = c.get("/api/admin/rag-config")
        assert r.json()["data"]["chunk_size"] == 800
        # 非法值 422 且不落盘
        r = c.put("/api/admin/rag-config", json={"chunk_size": -1})
        assert r.status_code == 422 and r.json()["success"] is False
        assert c.get("/api/admin/rag-config").json()["data"]["chunk_size"] == 800


def test_null_and_empty_body_are_noops():
    """显式 null 不得绕过校验污染运行中配置;空 body 成功且幂等。"""
    with tempfile.TemporaryDirectory() as tmp:
        c, live = _client(tmp)
        c.put("/api/admin/rag-config", json={"chunk_size": 800})
        assert live.chunk_size == 800
        # 显式 null:既不报错也不把运行中配置改成 None,更不覆盖已有值
        r = c.put("/api/admin/rag-config", json={"chunk_size": None})
        assert r.json()["success"], r.text
        assert r.json()["data"]["chunk_size"] == 800
        assert live.chunk_size == 800
        # 空 body:成功且幂等,值不变
        r = c.put("/api/admin/rag-config", json={})
        assert r.json()["success"], r.text
        assert r.json()["data"]["chunk_size"] == 800
        assert live.chunk_size == 800


def test_runtime_params_persist_and_sync_instances():
    """运行参数:合法值落盘+热更 RAGConfig+同步 Provider 实例属性;越界 422。"""
    with tempfile.TemporaryDirectory() as tmp:
        c, live = _client(tmp)
        # 挂上模拟的运行中 Provider(构造时快照的实例属性)
        embedding = SimpleNamespace(batch_size=32, max_retries=3, timeout=120.0)
        llm = SimpleNamespace(max_retries=3, timeout=120.0)
        c.app.state.rag_pipeline = SimpleNamespace(embedding=embedding, llm=llm)

        r = c.put("/api/admin/rag-config", json={
            "embedding_batch_size": 64, "embedding_max_retries": 5,
            "llm_max_retries": 2, "request_timeout": 300,
        })
        assert r.json()["success"], r.text
        # 落盘 + RAGConfig 热更
        assert live.embedding_batch_size == 64 and live.request_timeout == 300
        assert c.get("/api/admin/rag-config").json()["data"]["embedding_batch_size"] == 64
        # 实例属性同步(否则改了不生效)
        assert embedding.batch_size == 64 and embedding.max_retries == 5 and embedding.timeout == 300
        assert llm.max_retries == 2 and llm.timeout == 300
        # embedding 参数不得误写到 llm 实例
        assert not hasattr(llm, "batch_size")

        # 越界一律 422 且不落盘
        for bad in ({"embedding_batch_size": 0}, {"llm_max_retries": 11},
                    {"request_timeout": 601}, {"embedding_max_retries": -1}):
            r = c.put("/api/admin/rag-config", json=bad)
            assert r.status_code == 422, (bad, r.text)
        assert c.get("/api/admin/rag-config").json()["data"]["embedding_batch_size"] == 64


def main() -> int:
    tests = [
        test_get_defaults_put_persists_and_hot_updates,
        test_null_and_empty_body_are_noops,
        test_runtime_params_persist_and_sync_instances,
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
