"""Initialize database tables."""
import asyncio
import sys
sys.path.insert(0, "backend")

from app.core.database import engine, Base
from app.models import *  # noqa: F401, F403


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
