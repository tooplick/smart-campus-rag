"""一次性迁移:system_configs 的 model.* / rag.* → app-config.yaml。

用法:uv run python scripts/migrate-config-to-file.py [--force]

- 目标文件已存在时拒绝执行(--force 覆盖)
- 不删除 system_configs 原数据(遗留表本期不删)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.app_config import build_config_from_rows, write_config
from app.core.config import get_settings
from app.core.database import async_session
from app.models.system_config import SystemConfig


async def _load_rows() -> list[tuple[str, str | None, str]]:
    async with async_session() as db:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key.like("model.%") | SystemConfig.config_key.like("rag.%"))
        )
        return [(r.config_key, r.config_value, r.value_type) for r in result.scalars().all()]


def _count_keys(config: dict[str, Any]) -> int:
    """统计实际落盘的叶子配置键数(models.{type}.active + profile 字段 + rag.* 键)。"""
    n = 0
    for section in config.get("models", {}).values():
        n += 1  # active 指针
        n += len(section.get("profiles", {}).get("default", {}))
    n += len(config.get("rag", {}))
    return n


async def main() -> int:
    parser = argparse.ArgumentParser(description="迁移 system_configs 到 app-config.yaml")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的配置文件")
    args = parser.parse_args()

    target = Path(get_settings().APP_CONFIG_PATH)
    if target.exists() and not args.force:
        print(f"拒绝执行:{target} 已存在(用 --force 覆盖)")
        return 1

    try:
        rows = await _load_rows()
        config = build_config_from_rows(rows)
        # 原子写(临时文件 + os.replace):--force 覆盖既有文件时避免写一半损坏
        write_config(target, config)
    except Exception as e:  # 一次性运维脚本:DB/写盘失败打印错误退出,不裸抛 traceback
        print(f"迁移失败:{type(e).__name__}: {e}")
        return 1

    print(f"读取 {len(rows)} 行,落盘 {_count_keys(config)} 键 → {target}")
    print("提示:system_configs 原数据保留未删;后续配置读写一律走该文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
