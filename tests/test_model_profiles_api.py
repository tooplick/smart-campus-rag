"""模型配置 API 测试:CRUD / 切换启用 / 旧端点文件适配。

无需 pytest,可直接运行::

    uv run python tests/test_model_profiles_api.py
"""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.api.routes import admin, model_profiles
from app.core.app_config import AppConfigStore, get_app_config


def _client(tmp: str) -> TestClient:
    store = AppConfigStore(Path(tmp) / "app-config.yaml")
    app = FastAPI()
    app.include_router(model_profiles.router)
    app.include_router(admin.router)
    # 模拟运行中的管线/worker(app.state 优先分支),供热替换断言使用
    app.state.rag_pipeline = types.SimpleNamespace(embedding=None, llm=None, rerank=None)
    app.state.document_worker = types.SimpleNamespace(embedding=None, llm=None, vision_config=None)
    app.dependency_overrides[get_current_admin] = lambda: object()
    app.dependency_overrides[get_app_config] = lambda: store
    return TestClient(app)


def test_crud_and_active_flow():
    """新增自动首启、切换、改(active/非 active)、删、422 错误路径。"""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        # 新增:该类型无启用配置时自动启用
        r = c.post("/api/admin/model-profiles", json={"type": "llm", "name": "mimo", "base_url": "https://a", "api_key": "k", "model": "m1"})
        assert r.status_code == 200 and r.json()["success"], r.text
        r = c.get("/api/admin/model-profiles")
        data = r.json()["data"]["llm"]
        assert data["active"] == "mimo", data
        assert data["profiles"]["mimo"]["api_key_configured"] is True
        assert "api_key" not in data["profiles"]["mimo"]
        # 改 active 配置 → 生效
        r = c.put("/api/admin/model-profiles/llm/mimo", json={"model": "m1b"})
        assert r.json()["success"], r.text
        data = c.get("/api/admin/model-profiles").json()["data"]["llm"]
        assert data["profiles"]["mimo"]["model"] == "m1b", data
        # 新增第二套(非 active)
        c.post("/api/admin/model-profiles", json={"type": "llm", "name": "bak", "base_url": "https://b", "api_key": "k2", "model": "m2"})
        # 改非 active 配置 → active 视图不变
        r = c.put("/api/admin/model-profiles/llm/bak", json={"model": "m2b"})
        assert r.json()["success"], r.text
        data = c.get("/api/admin/model-profiles").json()["data"]["llm"]
        assert data["active"] == "mimo", data
        assert data["profiles"]["mimo"]["model"] == "m1b", data
        assert data["profiles"]["bak"]["model"] == "m2b", data
        # 切换
        r = c.put("/api/admin/model-profiles/active", json={"type": "llm", "name": "bak"})
        assert r.json()["data"]["active"] == "bak", r.text
        # 启用中的删除被拒
        r = c.delete("/api/admin/model-profiles/llm/bak")
        assert r.status_code == 422 and r.json()["success"] is False
        # 切回后可删
        c.put("/api/admin/model-profiles/active", json={"type": "llm", "name": "mimo"})
        r = c.delete("/api/admin/model-profiles/llm/bak")
        assert r.json()["success"], r.text
        # 重名 422
        r = c.post("/api/admin/model-profiles", json={"type": "llm", "name": "mimo", "base_url": "x", "api_key": "", "model": ""})
        assert r.status_code == 422


def test_embed_llm_cannot_disable():
    """embedding/llm 不允许停用(active=null);rerank/vision 可以。"""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        c.post("/api/admin/model-profiles", json={"type": "embedding", "name": "bge", "base_url": "http://localhost:8080", "api_key": "-", "model": "bge-m3"})
        r = c.put("/api/admin/model-profiles/active", json={"type": "embedding", "name": None})
        assert r.status_code == 422, r.text
        r = c.put("/api/admin/model-profiles/active", json={"type": "rerank", "name": None})
        assert r.json()["success"], r.text


def test_incomplete_first_profile_rejected():
    """首个配置会被自动启用:缺 base_url/model 应 422 且不落盘(不留半成品)。"""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        r = c.post("/api/admin/model-profiles", json={"type": "rerank", "name": "r", "base_url": "", "model": ""})
        assert r.status_code == 422 and r.json()["success"] is False, r.text
        data = c.get("/api/admin/model-profiles").json()["data"]["rerank"]
        assert data["profiles"] == {}, data
        assert data["active"] is None
        # 补全后可创建并自动启用
        r = c.post("/api/admin/model-profiles", json={"type": "rerank", "name": "r", "base_url": "https://r", "model": "rm"})
        assert r.json()["success"] and r.json()["data"]["active"] == "r", r.text


def test_legacy_models_endpoints_write_file():
    """旧 GET/PUT /models/{type} 读写配置文件(适配器,Plan 2 下线)。"""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        r = c.put("/api/admin/models/llm", json={"base_url": "https://legacy", "api_key": "sk-l", "model": "lm1"})
        assert r.json()["success"], r.text
        r = c.get("/api/admin/models/llm")
        data = r.json()["data"]
        assert data["base_url"] == "https://legacy" and data["model"] == "lm1", data
        assert data["api_key_configured"] is True


def test_legacy_disable_reenable_flow():
    """旧端点:停用后再次写入不得因 default 已存在而 422;停用态仍展示已存字段。"""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        # 首次写入:建 default 并启用
        r = c.put("/api/admin/models/rerank", json={"base_url": "https://r", "api_key": "k", "model": "rm"})
        assert r.json()["data"]["enabled"] is True, r.text
        # 停用
        r = c.put("/api/admin/models/rerank", json={"enabled": False})
        assert r.json()["success"] and r.json()["data"]["enabled"] is False, r.text
        # 停用态仍能看到已存 default 字段
        assert r.json()["data"]["base_url"] == "https://r", r.json()["data"]
        assert r.json()["data"]["api_key_configured"] is True
        # 重新写入并启用:不得 422「配置名已存在」
        r = c.put("/api/admin/models/rerank", json={"base_url": "https://r2", "api_key": "k", "model": "rm2"})
        assert r.json()["success"], r.text
        assert r.json()["data"]["enabled"] is True
        assert r.json()["data"]["base_url"] == "https://r2" and r.json()["data"]["model"] == "rm2"


def test_api_triggers_swap():
    """活跃切换/活跃配置修改真正热替换 app.state 实例;非活跃新增不动运行实例。"""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        app = c.app
        c.post("/api/admin/model-profiles", json={"type": "llm", "name": "A", "base_url": "https://a", "api_key": "ka", "model": "ma"})
        first = app.state.rag_pipeline.llm
        assert first is not None and first.model == "ma", first
        # 新增非活跃配置 → 运行实例不变
        c.post("/api/admin/model-profiles", json={"type": "llm", "name": "B", "base_url": "https://b", "api_key": "kb", "model": "mb"})
        assert app.state.rag_pipeline.llm is first, "非活跃新增不得替换运行实例"
        # 切换活跃到 B → 实例被替换
        c.put("/api/admin/model-profiles/active", json={"type": "llm", "name": "B"})
        second = app.state.rag_pipeline.llm
        assert second is not None and second.model == "mb", second
        assert second is not first


def test_swap_falls_back_to_main_globals():
    """app.state 未挂 pipeline/worker 时热替换回退 main 模块全局;挂有时 state 优先。"""
    import types

    import app.main as main_module
    from app.services.model_swap import apply_model_change

    fake_pipeline = types.SimpleNamespace(embedding=None, llm=None, rerank=None)
    fake_worker = types.SimpleNamespace(embedding=None, llm=None, vision_config=None)
    old_pipeline = getattr(main_module, "rag_pipeline", None)
    old_worker = getattr(main_module, "document_worker", None)
    try:
        main_module.rag_pipeline = fake_pipeline
        main_module.document_worker = fake_worker
        with tempfile.TemporaryDirectory() as tmp:
            store = AppConfigStore(Path(tmp) / "app-config.yaml")
            store.add_profile("embedding", "bge", {
                "base_url": "http://localhost:8080", "api_key": "-", "model": "bge-m3",
            })
            store.set_active("embedding", "bge")

            # 分支 1:app.state 无 pipeline/worker → 回退 main 模块全局
            app = types.SimpleNamespace(state=types.SimpleNamespace())
            apply_model_change(app, "embedding", store)
            assert fake_pipeline.embedding is not None, "回退分支未命中:main 全局 pipeline 未被替换"
            assert fake_pipeline.embedding.base_url == "http://localhost:8080", fake_pipeline.embedding.base_url
            assert fake_worker.embedding is fake_pipeline.embedding, "worker 应共享同一 embedding 实例"

            # 分支 2:app.state 挂有 pipeline/worker → 优先替换 state 实例,不动 main 全局
            main_embedding_before = fake_pipeline.embedding
            state_pipeline = types.SimpleNamespace(embedding=None, llm=None, rerank=None)
            state_worker = types.SimpleNamespace(embedding=None, llm=None, vision_config=None)
            app2 = types.SimpleNamespace(state=types.SimpleNamespace(
                rag_pipeline=state_pipeline, document_worker=state_worker,
            ))
            apply_model_change(app2, "embedding", store)
            assert state_pipeline.embedding is not None, "state 优先分支未命中"
            assert state_pipeline.embedding is not main_embedding_before
            assert state_worker.embedding is state_pipeline.embedding
            assert fake_pipeline.embedding is main_embedding_before, "state 分支不得改动 main 全局"
    finally:
        main_module.rag_pipeline = old_pipeline
        main_module.document_worker = old_worker


def test_test_endpoint_uses_named_profile():
    """/models/{type}/test 可选 {name} body:指定配置测指定,缺省测 active(切换后跟随)。"""
    import httpx

    captured: list = []
    orig_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={
            "id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
        })

    def fake_async_client(*args, **kwargs):
        # 打桩 AsyncClient 构造:注入 MockTransport,其余参数(timeout 等)原样透传
        kwargs.setdefault("transport", httpx.MockTransport(handler))
        return orig_async_client(*args, **kwargs)

    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        c.post("/api/admin/model-profiles", json={"type": "llm", "name": "A", "base_url": "https://a.example", "api_key": "sk-a", "model": "ma"})
        c.post("/api/admin/model-profiles", json={"type": "llm", "name": "B", "base_url": "https://b.example", "api_key": "sk-b", "model": "mb"})
        httpx.AsyncClient = fake_async_client
        try:
            # 指定 name=B → 测的是 B 的配置而非 active
            r = c.post("/api/admin/models/llm/test", json={"name": "B"})
            body = r.json()
            assert body["success"] and body["data"]["status"] == "ok", r.text
            assert body["data"]["model"] == "mb", body
            req = captured[-1]
            assert "b.example" in str(req.url), req.url
            assert req.headers["Authorization"] == "Bearer sk-b", req.headers
            # 不带 body → 测 active(A)
            r = c.post("/api/admin/models/llm/test")
            body = r.json()
            assert body["success"] and body["data"]["status"] == "ok", r.text
            assert body["data"]["model"] == "ma", body
            req = captured[-1]
            assert "a.example" in str(req.url), req.url
            assert req.headers["Authorization"] == "Bearer sk-a", req.headers
            # 切换 active 到 B 后,不带 body 跟随 active
            c.put("/api/admin/model-profiles/active", json={"type": "llm", "name": "B"})
            r = c.post("/api/admin/models/llm/test")
            body = r.json()
            assert body["data"]["model"] == "mb", body
            req = captured[-1]
            assert "b.example" in str(req.url), req.url
            assert req.headers["Authorization"] == "Bearer sk-b", req.headers
        finally:
            httpx.AsyncClient = orig_async_client


def main() -> int:
    tests = [
        test_crud_and_active_flow,
        test_embed_llm_cannot_disable,
        test_incomplete_first_profile_rejected,
        test_legacy_models_endpoints_write_file,
        test_legacy_disable_reenable_flow,
        test_api_triggers_swap,
        test_swap_falls_back_to_main_globals,
        test_test_endpoint_uses_named_profile,
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
