#!/usr/bin/env python
"""清理孤儿视频文件：磁盘 / OSS 上存在、但数据库未引用的视频。

⚠️ 运行时机：请在「迁移脚本之前」运行本地清理。
   因为迁移会把 DB 的 file_url 改成 OSS 地址，届时本地原件会变成"未引用"，
   若迁移后再跑本地清理会把刚迁移的原件也当孤儿列出。
   OSS 孤儿清理则任何时候都安全。

安全：
  - 默认 dry-run，只列清单 + 合计大小，不删任何东西；
  - 加 --apply 才真正删除；
  - 可单独只清一侧：--local-only / --oss-only。

用法：
    cd backend
    .venv/Scripts/python.exe scripts/cleanup_orphans.py                # 列清单
    .venv/Scripts/python.exe scripts/cleanup_orphans.py --apply        # 删除
    .venv/Scripts/python.exe scripts/cleanup_orphans.py --oss-only --apply
"""

import asyncio
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.video import Video
from app.services import oss_storage
from scripts import _oss_ops as ops

UPLOAD_DIR = Path(settings.upload_dir)
VIDEO_DIR = UPLOAD_DIR / "videos"


async def _load_videos() -> list[Video]:
    async with async_session_factory() as session:
        return list((await session.execute(select(Video))).scalars().all())


def cleanup_local(videos: list[Video], apply: bool) -> None:
    referenced = {ops.basename_of(v.file_url) for v in videos if ops.is_local_url(v.file_url)}
    on_disk = {p.name for p in VIDEO_DIR.glob("*") if p.is_file()}
    orphans = ops.local_orphans(referenced, on_disk)

    total = 0
    print(f"\n=== 本地孤儿视频（{VIDEO_DIR}）===")
    for name in orphans:
        size = (VIDEO_DIR / name).stat().st_size
        total += size
        print(f"  {size/1024/1024:.1f}MB  {name}")
    print(f"合计 {len(orphans)} 个，{total/1024/1024/1024:.2f} GB")

    if apply:
        for name in orphans:
            (VIDEO_DIR / name).unlink(missing_ok=True)
        print(f"已删除 {len(orphans)} 个本地孤儿文件。")


async def cleanup_oss(videos: list[Video], apply: bool) -> None:
    if not oss_storage.is_enabled():
        print("\n=== OSS 孤儿 === OSS 未启用，跳过。")
        return
    import oss2

    referenced = {
        oss_storage.object_key_from_url(v.file_url)
        for v in videos
        if v.file_url and oss_storage.is_oss_url(v.file_url)
    }
    bucket = oss_storage._get_bucket()
    all_keys = [o.key for o in oss2.ObjectIterator(bucket, prefix="videos/")]
    orphans = ops.oss_orphans(referenced, all_keys)

    print("\n=== OSS 孤儿对象（videos/ 前缀）===")
    for key in orphans:
        print(f"  {key}")
    print(f"合计 {len(orphans)} 个")

    if apply:
        for key in orphans:
            await asyncio.to_thread(bucket.delete_object, key)
        print(f"已删除 {len(orphans)} 个 OSS 孤儿对象。")


async def main(apply: bool, local: bool, oss: bool) -> None:
    print(f"模式：{'APPLY（真实删除）' if apply else 'DRY-RUN（仅列清单）'}")
    videos = await _load_videos()
    if local:
        cleanup_local(videos, apply)
    if oss:
        await cleanup_oss(videos, apply)
    if not apply:
        print("\n这是清单预览。确认无误后加 --apply 删除。")


if __name__ == "__main__":
    args = sys.argv[1:]
    do_local = "--oss-only" not in args
    do_oss = "--local-only" not in args
    asyncio.run(main(apply="--apply" in args, local=do_local, oss=do_oss))
