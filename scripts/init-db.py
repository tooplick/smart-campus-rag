"""Initialize database tables."""
import asyncio
import sys
from pathlib import Path

# 项目根入 path(与 init-qdrant.py 一致;旧的 "backend" 目录已不存在)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import engine, Base
from app.models import *  # noqa: F401, F403


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
