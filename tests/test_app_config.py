"""app-config.yaml 存储测试:模型 profile CRUD / active 切换 / rag 参数读写。

无需 pytest,可直接运行::

    uv run python tests/test_app_config.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.app_config import (
    RAG_DEFAULTS,
    AppConfigError,
    AppConfigStore,
    build_config_from_rows,
)


def _store(tmp: str) -> AppConfigStore:
    return AppConfigStore(Path(tmp) / "app-config.yaml")


def test_missing_file_defaults():
    """文件不存在时:rag 返回代码默认值,模型无启用配置。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        rag = s.get_rag()
        assert rag["chunk_size"] == 600, rag
        assert rag["similarity_threshold"] == 0.6, rag
        assert s.get_active_profile("llm") is None
        assert s.list_profiles("llm") == {"active": None, "profiles": {}}


def test_profile_crud_and_active():
    """增改查删与启用切换的完整闭环。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        s.add_profile("llm", "mimo", {"base_url": "https://api.test", "api_key": "sk-1", "model": "m1"})
        s.add_profile("llm", "bak", {"base_url": "https://api.bak", "api_key": "sk-2", "model": "m2"})
        active = s.set_active("llm", "mimo")
        assert active == {"name": "mimo", "base_url": "https://api.test", "api_key": "sk-1", "model": "m1"}
        s.update_profile("llm", "mimo", {"model": "m1.5"})
        assert s.get_profile("llm", "mimo")["model"] == "m1.5"
        # 启用中的配置禁止删除
        try:
            s.delete_profile("llm", "mimo")
            raise AssertionError("应当拒绝删除启用中的配置")
        except AppConfigError:
            pass
        s.set_active("llm", "bak")
        s.delete_profile("llm", "mimo")
        assert "mimo" not in s.list_profiles("llm")["profiles"]
        # 停用
        assert s.set_active("llm", None) is None
        assert s.get_active_profile("llm") is None


def test_profile_errors():
    """非法类型、重名、不存在、空名、未知字段均报错。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        for fn in (
            lambda: s.add_profile("audio", "x", {}),
            lambda: s.add_profile("llm", "  ", {}),
            lambda: s.add_profile("llm", "x", {"nope": "1"}),
        ):
            try:
                fn()
                raise AssertionError("应当抛 AppConfigError")
            except AppConfigError:
                pass
        s.add_profile("llm", "x", {"base_url": "u", "api_key": "k", "model": "m"})
        try:
            s.add_profile("llm", "x", {})
            raise AssertionError("应当拒绝重名")
        except AppConfigError:
            pass
        try:
            s.set_active("llm", "ghost")
            raise AssertionError("应当拒绝启用不存在的配置")
        except AppConfigError:
            pass


def test_activate_incomplete_profile_rejected():
    """启用缺 base_url/model 的配置应报错且不改变 active;补全后可启用。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        s.add_profile("llm", "empty", {"base_url": "", "api_key": "k", "model": ""})
        try:
            s.set_active("llm", "empty")
            raise AssertionError("应当拒绝启用不完整配置")
        except AppConfigError:
            pass
        assert s.get_active_profile("llm") is None
        # 补全后可正常启用
        s.update_profile("llm", "empty", {"base_url": "https://x", "model": "m"})
        assert s.set_active("llm", "empty")["name"] == "empty"


def test_rag_read_write():
    """rag 参数写入后读回;未知键拒绝;缺项回退默认。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        s.save_rag({"chunk_size": 800, "similarity_threshold": 0.75})
        rag = s.get_rag()
        assert rag["chunk_size"] == 800, rag
        assert rag["similarity_threshold"] == 0.75, rag
        assert rag["final_top_k"] == 5, rag  # 缺项回退默认
        try:
            s.save_rag({"unknown_key": 1})
            raise AssertionError("应当拒绝未知 RAG 键")
        except AppConfigError:
            pass


def test_build_config_from_rows():
    """system_configs 行集 → 文件结构:enabled=false 不设 active;rag 白名单过滤。"""
    rows = [
        ("model.llm.base_url", "https://api.test", "string"),
        ("model.llm.api_key", "sk-1", "secret"),
        ("model.llm.model", "m1", "string"),
        ("model.llm.enabled", "true", "string"),
        ("model.rerank.enabled", "false", "string"),
        ("model.rerank.base_url", "https://r.test", "string"),
        ("model.rerank.api_key", "sk-r", "secret"),
        ("model.rerank.model", "r1", "string"),
        ("rag.chunk_size", "800", "int"),
        ("rag.bogus", "1", "int"),
        ("other.key", "x", "string"),
    ]
    config = build_config_from_rows(rows)
    assert config["models"]["llm"]["active"] == "default"
    assert config["models"]["llm"]["profiles"]["default"]["base_url"] == "https://api.test"
    assert config["models"]["rerank"]["active"] is None
    assert config["rag"] == {"chunk_size": 800}, config["rag"]
    assert list(config.keys()) == ["models", "rag"]


def test_corrupt_yaml_file():
    """损坏 YAML 一律抛 AppConfigError(不裸抛 yaml.ParserError)。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "app-config.yaml"
        path.write_text("models: [unclosed\n  broken: {", encoding="utf-8")
        s = AppConfigStore(path)
        for fn in (s.get_rag, lambda: s.list_profiles("llm")):
            try:
                fn()
                raise AssertionError("应当抛 AppConfigError")
            except AppConfigError:
                pass


def test_bad_structure_and_rag_values():
    """models/rag/profiles 非映射、rag 坏值强转失败均抛 AppConfigError;save_rag 中途非法键不落盘。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "app-config.yaml"
        s = AppConfigStore(path)
        # models: null / models: 5
        for content in ("models: null\nrag: {}", "models: 5\nrag: {}"):
            path.write_text(content, encoding="utf-8")
            try:
                s.list_profiles("llm")
                raise AssertionError("应当抛 AppConfigError")
            except AppConfigError:
                pass
        # profiles: [1] 时 add_profile 不得裸抛 TypeError
        path.write_text("models: {llm: {profiles: [1]}}\nrag: {}", encoding="utf-8")
        try:
            s.add_profile("llm", "x", {"base_url": "u", "api_key": "k", "model": "m"})
            raise AssertionError("应当抛 AppConfigError")
        except AppConfigError:
            pass
        # rag 坏值类型强转失败
        path.write_text("models: {}\nrag: {chunk_size: abc}", encoding="utf-8")
        try:
            s.get_rag()
            raise AssertionError("应当抛 AppConfigError")
        except AppConfigError:
            pass
        # save_rag 中途非法键:文件内容不变
        path.write_text("models: {}\nrag: {chunk_size: 800}", encoding="utf-8")
        before = path.read_text(encoding="utf-8")
        try:
            s.save_rag({"chunk_overlap": 10, "unknown_key": 1})
            raise AssertionError("应当拒绝未知 RAG 键")
        except AppConfigError:
            pass
        assert path.read_text(encoding="utf-8") == before, "中途失败不应落盘"


def test_unreadable_file_encoding():
    """非 UTF-8 字节的配置文件:get_rag 抛 AppConfigError(不裸抛 UnicodeDecodeError)。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "app-config.yaml"
        path.write_bytes(b"\xff\xfe\x00")
        s = AppConfigStore(path)
        try:
            s.get_rag()
            raise AssertionError("应当抛 AppConfigError")
        except AppConfigError:
            pass


def test_rag_defaults_match_ragconfig():
    """RAG_DEFAULTS 与 RAGConfig 默认值保持一致,防两处漂移。"""
    from app.rag.config import RAGConfig

    cfg = RAGConfig()
    assert {k: getattr(cfg, k) for k in RAG_DEFAULTS} == dict(RAG_DEFAULTS)


def main() -> int:
    tests = [
        test_missing_file_defaults,
        test_profile_crud_and_active,
        test_profile_errors,
        test_activate_incomplete_profile_rejected,
        test_rag_read_write,
        test_build_config_from_rows,
        test_corrupt_yaml_file,
        test_bad_structure_and_rag_values,
        test_unreadable_file_encoding,
        test_rag_defaults_match_ragconfig,
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
