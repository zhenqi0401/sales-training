#!/usr/bin/env python
"""Reset passwords for existing training users (sales/student) to "123456"
and set must_change_password=True so they are forced to change on next login.

Usage:  cd backend && uv run python seed_data/fix_training_passwords.py
"""
import asyncio
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User
from sqlalchemy import select, update


async def fix():
    async with async_session_factory() as session:
        # Find all sales/student users
        result = await session.execute(
            select(User).where(User.role.in_(["sales", "student"]))
        )
        users = result.scalars().all()

        if not users:
            print("No training users found in database.")
            return

        new_hash = hash_password("123456")
        count = 0
        for user in users:
            user.password_hash = new_hash
            user.must_change_password = True
            count += 1
            print(f"  Updated: {user.username} ({user.phone}) role={user.role}")

        await session.commit()
        print(f"\nDone. {count} training user(s) reset to password=123456, must_change_password=True.")


if __name__ == "__main__":
    asyncio.run(fix())
