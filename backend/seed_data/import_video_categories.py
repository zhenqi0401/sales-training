#!/usr/bin/env python
"""Import video categories from the training video folder structure.

Folder layout:
    C:\\Users\\Admin\\Desktop\\培训视频\\
        产品培训\\
            伟星合集\\
            依视路合集\\
            ...
        全面AI化\\
            AI化介绍\\
        技能培训\\
            IAOA培训\\
            ...
        运营管理\\
            公司介绍\\
            ...

Each top-level folder becomes a root category; each sub-folder becomes a child
category under its parent.  Codes are auto-generated via pypinyin.

Idempotent: existing categories are not duplicated.
"""

import asyncio
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypinyin import lazy_pinyin
from sqlalchemy import select

from app.core.database import async_session_factory, engine
from app.models.base import Base
from app.models.category import Category

VIDEO_DIR = Path(r"C:\Users\Admin\Desktop\培训视频")


def make_code(name: str) -> str:
    """Generate a pinyin-based code from a Chinese name."""
    code = "_".join(lazy_pinyin(name.strip()))
    return code if code else "unknown"


async def get_or_create_category(session, name: str, parent_id: int | None = None) -> Category:
    """Create a category (idempotent).  Finds by name + parent_id."""
    result = await session.execute(
        select(Category)
        .where(Category.name == name, Category.parent_id == parent_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    code = make_code(name)
    # Ensure code uniqueness
    base_code = code
    suffix = 2
    while (await session.execute(select(Category).where(Category.code == code))).scalar_one_or_none():
        code = f"{base_code}_{suffix}"
        suffix += 1

    category = Category(
        name=name,
        code=code,
        parent_id=parent_id,
        sort_order=0,
        is_active=True,
    )
    session.add(category)
    await session.flush()
    return category


async def import_categories():
    if not VIDEO_DIR.exists():
        print(f"ERROR: Directory not found: {VIDEO_DIR}")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        created_parents = 0
        created_children = 0

        for parent_dir in sorted(VIDEO_DIR.iterdir()):
            if not parent_dir.is_dir():
                continue

            parent_name = parent_dir.name
            parent = await get_or_create_category(session, parent_name)
            is_new_parent = parent.id is not None and not created_parents  # track roughly
            print(f"  [Parent] {parent_name}  (code={parent.code})")

            for child_dir in sorted(parent_dir.iterdir()):
                if not child_dir.is_dir():
                    continue

                child_name = child_dir.name
                existing = await session.execute(
                    select(Category).where(
                        Category.name == child_name,
                        Category.parent_id == parent.id,
                    )
                )
                if existing.scalar_one_or_none():
                    print(f"    [Skip] {child_name} (already exists)")
                    continue

                child = await get_or_create_category(session, child_name, parent_id=parent.id)
                created_children += 1
                print(f"    [Child] {child_name}  (code={child.code})")

            created_parents += 1

        await session.commit()

    print(f"\nDone.  Created/verified {created_parents} parent categories, "
          f"{created_children} new child categories.")


if __name__ == "__main__":
    asyncio.run(import_categories())
