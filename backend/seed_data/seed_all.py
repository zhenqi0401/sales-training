#!/usr/bin/env python
"""Master seeder script — populates the database with initial reference data."""

import asyncio
import io
import sys
from pathlib import Path

# Fix Windows terminal encoding for Chinese output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory, engine
from app.core.security import hash_password
from app.models.base import Base
from app.models.category import Category
from app.models.store import Store
from app.models.user import User

# Product category codes from requirements
PRODUCT_CATEGORIES = [
    {"name": "青控", "code": "qingkong", "description": "近视防控产品培训"},
    {"name": "斜弱视", "code": "xieruoshi", "description": "斜弱视产品培训"},
    {"name": "角塑", "code": "jiaosu", "description": "角膜塑形镜培训"},
    {"name": "眼镜", "code": "yanjiang", "description": "眼镜产品培训"},
    {"name": "周边产品", "code": "zhoubian", "description": "周边产品培训"},
    {"name": "功能性眼镜", "code": "gongneng", "description": "功能性眼镜培训"},
    {"name": "企业文化", "code": "qiwenhua", "description": "企业文化宣导"},
]

# Unified role accounts for testing
ADMINS = [
    {"username": "admin", "phone": "13800000000", "password": "admin123",
     "real_name": "超级管理员", "role": "admin"},
    {"username": "admin2", "phone": "13800000001", "password": "admin123",
     "real_name": "培训管理员", "role": "admin"},
]
# 培训端测试账号 — 初始密码统一为 123456，首次登录强制改密
TRAINING_USERS = [
    {"username": "sales1", "phone": "13800000002", "password": "123456",
     "real_name": "张销售", "role": "sales"},
    {"username": "student", "phone": "13800000003", "password": "123456",
     "real_name": "李学员", "role": "student"},
]

STORES = [
    {"name": "总部", "code": "HQ", "sort_order": 0},
    {"name": "旗舰店", "code": "FLAGSHIP", "sort_order": 1},
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        from sqlalchemy import select

        # --- Categories ---
        for cat_data in PRODUCT_CATEGORIES:
            existing = await session.scalar(
                select(Category).where(Category.code == cat_data["code"])
            )
            if existing is None:
                session.add(Category(**cat_data, sort_order=0, is_active=True))

        # --- Stores ---
        for store_data in STORES:
            existing = await session.scalar(
                select(Store).where(Store.code == store_data["code"])
            )
            if existing is None:
                session.add(Store(**store_data, is_active=True))

        # --- Admin users ---
        for admin_data in ADMINS:
            existing = await session.scalar(
                select(User).where(User.username == admin_data["username"])
            )
            if existing is None:
                session.add(User(
                    username=admin_data["username"],
                    phone=admin_data["phone"],
                    password_hash=hash_password(admin_data["password"]),
                    real_name=admin_data["real_name"],
                    role=admin_data["role"],
                    is_active=True,
                ))

        # --- Training users (must_change_password on first login) ---
        for user_data in TRAINING_USERS:
            existing = await session.scalar(
                select(User).where(User.username == user_data["username"])
            )
            if existing is None:
                session.add(User(
                    username=user_data["username"],
                    phone=user_data["phone"],
                    password_hash=hash_password(user_data["password"]),
                    real_name=user_data["real_name"],
                    role=user_data["role"],
                    is_active=True,
                    must_change_password=True,
                ))

        await session.commit()

    print("Seed data inserted successfully.")
    print(f"  {len(PRODUCT_CATEGORIES)} product categories")
    print(f"  {len(STORES)} stores")
    print(f"  {len(ADMINS)} admin users:")
    for a in ADMINS:
        print(f"    {a['username']:<10} / {a['password']:<12} role={a['role']}")
    print(f"  {len(TRAINING_USERS)} training users (init password=123456, must change on first login):")
    for u in TRAINING_USERS:
        print(f"    {u['username']:<10} / {u['phone']:<14} role={u['role']}")


if __name__ == "__main__":
    asyncio.run(seed())
