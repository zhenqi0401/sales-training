#!/usr/bin/env python
"""Batch import videos from training video folder structure into the database.

Walks C:\\Users\\Admin\\Desktop\\培训视频 and for every video file (.mp4/.mov/.avi):
  - Matches the containing sub-folder to a second-level Category (by name + parent).
  - Copies the file into uploads/videos/{uuid}.{ext} and runs fast-start remux.
  - Creates a Video record with status="draft", title = filename (no extension).
  - Idempotent: skips videos already imported (matched by title + category_id).

Usage:
    cd backend
    uv run python seed_data/import_videos.py
"""

import asyncio
import io
import shutil
import sys
import uuid
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.models.base import Base
from app.models.category import Category
from app.models.video import Video
from app.services.video_processing import prepare_playable_mp4_fast

VIDEO_DIR = Path(r"C:\Users\Admin\Desktop\培训视频")
UPLOAD_DIR = Path(settings.upload_dir)
VIDEO_STORE = UPLOAD_DIR / "videos"
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi"}


async def import_videos():
    if not VIDEO_DIR.exists():
        print(f"ERROR: Directory not found: {VIDEO_DIR}")
        return

    VIDEO_STORE.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        imported = 0
        skipped = 0
        errors = 0

        # Walk through each parent folder -> child folder -> video files
        for parent_dir in sorted(VIDEO_DIR.iterdir()):
            if not parent_dir.is_dir():
                continue

            for child_dir in sorted(parent_dir.iterdir()):
                if not child_dir.is_dir():
                    continue

                child_name = child_dir.name

                # Find the parent category
                parent_cat = (
                    await session.execute(
                        select(Category).where(
                            Category.name == parent_dir.name,
                            Category.parent_id.is_(None),
                        )
                    )
                ).scalar_one_or_none()

                if not parent_cat:
                    print(f"  [WARN] Parent category not found: {parent_dir.name}")
                    continue

                # Find the child category
                child_cat = (
                    await session.execute(
                        select(Category).where(
                            Category.name == child_name,
                            Category.parent_id == parent_cat.id,
                        )
                    )
                ).scalar_one_or_none()

                if not child_cat:
                    print(f"  [WARN] Child category not found: {parent_dir.name}/{child_name}")
                    continue

                # Process each video file in the child folder
                for video_file in sorted(child_dir.iterdir()):
                    if not video_file.is_file():
                        continue

                    ext = video_file.suffix.lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        continue

                    title = video_file.stem

                    # Check if already imported (match by title + category)
                    existing = (
                        await session.execute(
                            select(Video).where(
                                Video.title == title,
                                Video.category_id == child_cat.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if existing:
                        print(f"  [Skip] {parent_dir.name}/{child_name}/{video_file.name}")
                        skipped += 1
                        continue

                    try:
                        # Copy file to uploads/videos with UUID name
                        dest_name = f"{uuid.uuid4().hex}{ext}"
                        dest_path = VIDEO_STORE / dest_name
                        shutil.copy2(str(video_file), str(dest_path))

                        # Run fast-start remux to make it web-playable
                        result = await asyncio.to_thread(
                            prepare_playable_mp4_fast, dest_path, UPLOAD_DIR
                        )

                        # Create Video record
                        video = Video(
                            title=title,
                            category_id=child_cat.id,
                            file_url=result.file_url,
                            cover_url=result.cover_url,
                            duration=result.duration or 0,
                            resolution=result.resolution or "",
                            file_size=result.file_size or 0,
                            status="draft",
                            sort_order=0,
                            is_required=False,
                            est_duration=(
                                (result.duration or 0) // 60
                                + (1 if (result.duration or 0) % 60 > 0 else 0)
                            ),
                        )
                        session.add(video)
                        await session.flush()

                        imported += 1
                        print(
                            f"  [OK] {parent_dir.name}/{child_name}/{video_file.name} "
                            f"→ id={video.id} size={result.file_size}"
                        )
                    except Exception as exc:
                        errors += 1
                        print(f"  [ERROR] {parent_dir.name}/{child_name}/{video_file.name}: {exc}")

        await session.commit()

    print(f"\nDone. Imported: {imported}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    asyncio.run(import_videos())
