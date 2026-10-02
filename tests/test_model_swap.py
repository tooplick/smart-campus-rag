"""模型热替换测试:切换启用配置后管线/worker 实例被替换。

无需 pytest,可直接运行::

    uv run python tests/test_model_swap.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.app_config import AppConfigError, AppConfigStore
from app.services.model_swap import apply_model_change


def _fake_app(store: AppConfigStore) -> SimpleNamespace:
    rag_config = SimpleNamespace(embedding_batch_size=32)
    pipeline = SimpleNamespace(embedding=None, llm=None, rerank=None)
    worker = SimpleNamespace(embedding=None, llm=None, vision_config=None)
    return SimpleNamespace(state=SimpleNamespace(
        rag_config=rag_config, rag_pipeline=pipeline, document_worker=worker,
    ))


def test_swap_embedding_and_llm():
    with tempfile.TemporaryDirectory() as tmp:
        store = AppConfigStore(Path(tmp) / "app-config.yaml")
        store.add_profile("embedding", "b1", {"base_url": "http://e1", "api_key": "k", "model": "bge-m3"})
        store.add_profile("embedding", "b2", {"base_url": "http://e2", "api_key": "k", "model": "bge-m3"})
        store.add_profile("llm", "l1", {"base_url": "http://l1", "api_key": "k", "model": "m"})
        store.set_active("embedding", "b1")
        store.set_active("llm", "l1")
        app = _fake_app(store)

        apply_model_change(app, "embedding", store)
        assert app.state.rag_pipeline.embedding is app.state.document_worker.embedding
        first = app.state.rag_pipeline.embedding
        assert first.base_url == "http://e1"

        store.set_active("embedding", "b2")
        apply_model_change(app, "embedding", store)
        assert app.state.rag_pipeline.embedding is not first
        assert app.state.rag_pipeline.embedding.base_url == "http://e2"

        apply_model_change(app, "llm", store)
        assert app.state.rag_pipeline.llm.base_url == "http://l1"
        assert app.state.document_worker.llm is app.state.rag_pipeline.llm


def test_swap_rerank_vision_and_guard():
    with tempfile.TemporaryDirectory() as tmp:
        store = AppConfigStore(Path(tmp) / "app-config.yaml")
        app = _fake_app(store)
        # rerank 未启用 → 置 None
        apply_model_change(app, "rerank", store)
        assert app.state.rag_pipeline.rerank is None
        store.add_profile("rerank", "r1", {"base_url": "http://r", "api_key": "k", "model": "rr"})
        store.set_active("rerank", "r1")
        apply_model_change(app, "rerank", store)
        assert app.state.rag_pipeline.rerank is not None
        # vision 未启用 → worker.vision_config None
        apply_model_change(app, "vision", store)
        assert app.state.document_worker.vision_config is None
        # embedding 无启用配置 → 报错
        try:
            apply_model_change(app, "embedding", store)
            raise AssertionError("应当拒绝无启用配置的 embedding")
        except AppConfigError:
            pass


def main() -> int:
    tests = [test_swap_embedding_and_llm, test_swap_rerank_vision_and_guard]
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
