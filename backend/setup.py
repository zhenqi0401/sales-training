#!/usr/bin/env python
"""Setup script — creates tables and seeds initial data. Single command start.
Usage: uv run python setup.py
"""
import io
import os
import sys

os.environ["PYTHONUTF8"] = "1"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import engine, async_session_factory
from app.core.security import hash_password
from app.models.base import Base
from app.models.category import Category
from app.models.store import Store
from app.models.user import User


PRODUCT_CATEGORIES = [
    {"name": "青控", "code": "qingkong", "description": "近视防控产品培训"},
    {"name": "斜弱视", "code": "xieruoshi", "description": "斜弱视产品培训"},
    {"name": "角塑", "code": "jiaosu", "description": "角膜塑形镜培训"},
    {"name": "眼镜", "code": "yanjiang", "description": "眼镜产品培训"},
    {"name": "周边产品", "code": "zhoubian", "description": "周边产品培训"},
    {"name": "功能性眼镜", "code": "gongneng", "description": "功能性眼镜培训"},
    {"name": "企业文化", "code": "qiwenhua", "description": "企业文化宣导"},
]

STORES = [
    {"name": "总部", "code": "HQ", "sort_order": 0},
    {"name": "旗舰店", "code": "FLAGSHIP", "sort_order": 1},
]


async def setup():
    # Step 1: Create all tables
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    # Step 2: Seed data
    async with async_session_factory() as session:
        from sqlalchemy import select

        for cat_data in PRODUCT_CATEGORIES:
            result = await session.execute(
                select(Category).where(Category.code == cat_data["code"])
            )
            if result.scalar_one_or_none() is None:
                session.add(Category(**cat_data, sort_order=0, is_active=True))

        for store_data in STORES:
            result = await session.execute(
                select(Store).where(Store.code == store_data["code"])
            )
            if result.scalar_one_or_none() is None:
                session.add(Store(**store_data, is_active=True))

        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        if result.scalar_one_or_none() is None:
            session.add(User(
                username="admin",
                phone="13800000000",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                role="super_admin",
                is_active=True,
            ))

        await session.commit()

    print("Seed data inserted:")
    print(f"  Categories: {len(PRODUCT_CATEGORIES)}")
    print(f"  Stores: {len(STORES)}")
    print("  Admin: admin / admin123")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(setup())
