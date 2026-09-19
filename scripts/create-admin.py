"""Create initial admin user with default credentials."""
import asyncio
import sys
sys.path.insert(0, "backend")

from app.core.database import engine, async_session, Base
from app.core.security import hash_password
from app.models.admin import Admin


async def create_admin():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        existing = await session.get(Admin, 1)
        if existing:
            print("Admin already exists. Skipping.")
            return

        admin = Admin(
            id=1,
            username="admin",
            password_hash=hash_password("admin"),
            must_change_password=True,
            status=1,
        )
        session.add(admin)
        await session.commit()
        print("Initial admin created: admin/admin")


if __name__ == "__main__":
    asyncio.run(create_admin())
