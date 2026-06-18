#!/usr/bin/env python
"""把历史本地视频（DB 中 file_url 为 /uploads/...）迁移到阿里云 OSS。

做什么：
  - 遍历所有 file_url 以 /uploads/ 开头的视频；
  - 把本地文件上传到 OSS：videos/{创建月份}/{原文件名}；
  - 把 DB 的 file_url 改成 OSS 规范地址（学员端会自动签名播放）；
  - 本地文件保留不删（作为备份；验证无误后可再手动清理）。

安全：
  - 默认 dry-run，只打印计划，不动任何东西；
  - 加 --apply 才真正上传 + 改库；
  - 幂等：已是 OSS 地址的视频自动跳过，可重复运行续传。

用法：
    cd backend
    .venv/Scripts/python.exe scripts/migrate_videos_to_oss.py            # 预览
    .venv/Scripts/python.exe scripts/migrate_videos_to_oss.py --apply    # 执行

前置：.env 里 OSS_ENABLED=true 且 OSS 配置正确。
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


async def main(apply: bool) -> None:
    if not oss_storage.is_enabled():
        print("✗ OSS 未启用（.env 里 SALES_TRAINING_OSS_ENABLED=true）。中止。")
        return

    async with async_session_factory() as session:
        videos = (await session.execute(select(Video))).scalars().all()

    locals_ = [v for v in videos if ops.is_local_url(v.file_url)]
    print(f"模式：{'APPLY（真实执行）' if apply else 'DRY-RUN（仅预览）'}")
    print(f"视频总数 {len(videos)}，其中待迁移本地视频 {len(locals_)} 个\n")

    migrated = skipped = failed = 0
    total_bytes = 0
    for v in locals_:
        basename = ops.basename_of(v.file_url)
        local_path = UPLOAD_DIR / v.file_url.removeprefix("/uploads/")
        if not local_path.exists():
            print(f"  [skip] id={v.id} 本地文件缺失：{local_path}")
            skipped += 1
            continue

        key = ops.migration_object_key(v.created_at, basename)
        size = local_path.stat().st_size
        total_bytes += size
        print(f"  id={v.id} {size/1024/1024:.1f}MB  {v.file_url}  ->  {key}")

        if apply:
            try:
                url = await asyncio.to_thread(oss_storage.upload_file, local_path, key)
                async with async_session_factory() as session:
                    async with session.begin():
                        fresh = await session.get(Video, v.id)
                        if fresh:
                            fresh.file_url = url
                migrated += 1
            except Exception as exc:  # noqa: BLE001
                print(f"     ✗ 失败：{exc}")
                failed += 1

    print("\n──────── 汇总 ────────")
    print(f"待迁移 {len(locals_)} 个，合计 {total_bytes/1024/1024/1024:.1f} GB")
    if apply:
        print(f"成功 {migrated}，跳过 {skipped}，失败 {failed}")
        print("本地文件已保留（备份）。验证 OSS 播放无误后，可用 cleanup 脚本清理本地原件。")
    else:
        print("这是预览。确认无误后加 --apply 执行。")


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv))
