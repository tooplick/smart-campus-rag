"""一次性初始化入口(幂等,供 Docker 启动流程调用)。

依次执行:建表 → 初始化 Qdrant 集合 → 仅在 admin 表为空时创建初始管理员。
与 create-admin.py 的区别:该脚本会**重置**密码,不适合自动流程;本脚本绝不改动已有管理员。
"""
import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(script_name: str):
    """加载 scripts/ 下的脚本模块(文件名带连字符,不能直接 import)。"""
    spec = importlib.util.spec_from_file_location(script_name.replace("-", "_"), ROOT / "scripts" / script_name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def main():
    # 1. 建表(create_all 幂等)
    db = _load("init-db.py")
    await db.init_db()

    # 2. Qdrant 集合与索引(已存在则跳过)
    await _load("init-qdrant.py").main()

    # 3. 仅首次创建管理员;已有管理员一律不动(避免自动流程重置密码)
    from sqlalchemy import text
    from app.core.database import engine
    from app.core.security import hash_password

    async with engine.begin() as conn:
        count = (await conn.execute(text("SELECT COUNT(*) FROM admin"))).scalar()
        if count:
            print(f"Admin already exists ({count} row(s)), skip creation.")
        else:
            await conn.execute(
                text(
                    "INSERT INTO admin (id, username, password_hash, must_change_password, status) "
                    "VALUES (1, 'admin', :hash, true, 1)"
                ),
                {"hash": hash_password("admin")},
            )
            print("Admin created: admin / admin (must change password on first login).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
