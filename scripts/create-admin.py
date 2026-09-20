#!/usr/bin/env python3
"""Create or reset the admin user with bcrypt 3.x compatible hash."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from sqlalchemy import text
from app.core.database import engine
from app.core.security import hash_password


async def main():
    password = "admin"
    hashed = hash_password(password)

    async with engine.begin() as conn:
        # Check if admin exists
        result = await conn.execute(text("SELECT id FROM admin WHERE id = 1"))
        exists = result.fetchone()

        if exists:
            await conn.execute(
                text("UPDATE admin SET password_hash = :hash, must_change_password = true WHERE id = 1"),
                {"hash": hashed},
            )
            print(f"Admin password reset. hash={hashed[:20]}...")
        else:
            await conn.execute(
                text("INSERT INTO admin (id, username, password_hash, must_change_password, status) VALUES (1, 'admin', :hash, true, 1)"),
                {"hash": hashed},
            )
            print(f"Admin created. hash={hashed[:20]}...")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
