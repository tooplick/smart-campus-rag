"""迁移转换测试:system_configs 行集 → app-config.yaml 结构(build_config_from_rows)。

无需 pytest,可直接运行::

    uv run python tests/test_config_migration.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.app_config import AppConfigError, build_config_from_rows


def test_build_config_from_rows():
    """enabled=false 不设 active;rag 白名单过滤;非 model/rag 前缀忽略。"""
    rows = [
        ("model.embedding.base_url", "http://localhost:8080", "string"),
        ("model.embedding.api_key", "-", "secret"),
        ("model.embedding.model", "bge-m3", "string"),
        ("model.embedding.enabled", "true", "string"),
        ("model.vision.enabled", "false", "string"),
        ("model.vision.base_url", "https://v.test", "string"),
        ("model.vision.api_key", "sk-v", "secret"),
        ("model.vision.model", "v1", "string"),
        ("rag.vector_weight", "0.7", "float"),
        ("rag.bogus", "1", "int"),
        ("other.key", "x", "string"),
    ]
    config = build_config_from_rows(rows)
    assert config["models"]["embedding"]["active"] == "default", config
    assert config["models"]["embedding"]["profiles"]["default"]["model"] == "bge-m3"
    assert config["models"]["vision"]["active"] is None, config
    assert config["rag"] == {"vector_weight": 0.7}, config["rag"]
    assert list(config.keys()) == ["models", "rag"]


def test_bad_rag_value_in_rows():
    """行集里 rag 值类型非法时抛 AppConfigError(而非裸 ValueError)。"""
    try:
        build_config_from_rows([("rag.chunk_size", "abc", "int")])
    except AppConfigError:
        return
    raise AssertionError("应当抛 AppConfigError")


def test_refuse_without_force():
    """目标文件已存在且无 --force:退出码 1,文件内容字节级不变(不依赖 DB,拒绝先于查库)。"""
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "app-config.yaml"
        known = "models: {llm: {active: default}}\nrag: {chunk_size: 600}\n"
        # 字节级写入:避免 Windows 文本模式 \n → \r\n 转换干扰字节级断言
        target.write_bytes(known.encode("utf-8"))
        env = {
            **os.environ,
            "APP_CONFIG_PATH": str(target),
            "PYTHONIOENCODING": "utf-8",  # 子进程中文输出走 UTF-8,避免 Windows GBK 解码失败
        }
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "migrate-config-to-file.py")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(root),
        )
        assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
        assert "拒绝执行" in proc.stdout  # 防「子进程崩溃即假 PASS」:须走到拒绝分支并输出原因
        assert target.read_bytes() == known.encode("utf-8"), "拒绝路径不得改写目标文件"


def main() -> int:
    tests = [test_build_config_from_rows, test_bad_rag_value_in_rows, test_refuse_without_force]
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
