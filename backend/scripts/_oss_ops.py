"""迁移 / 清理脚本共用的纯逻辑（无副作用，便于单测）。"""

from datetime import datetime


def is_local_url(file_url: str) -> bool:
    """file_url 是否为本地 /uploads 路径（区别于 OSS 绝对地址）。"""
    return bool(file_url) and file_url.startswith("/uploads/")


def basename_of(file_url: str) -> str:
    """取 URL/路径最后一段文件名。"""
    return file_url.rsplit("/", 1)[-1]


def migration_object_key(created_at: datetime | None, basename: str) -> str:
    """老视频迁移到 OSS 的 object key：videos/{YYYYMM}/{原文件名}。

    月份取视频 created_at；缺失则归到 videos/legacy/ 下。保留原 uuid 文件名便于追溯。
    """
    month = created_at.strftime("%Y%m") if created_at is not None else "legacy"
    return f"videos/{month}/{basename}"


def local_orphans(referenced_basenames: set[str], disk_basenames: set[str]) -> list[str]:
    """磁盘上存在、但 DB 未引用的本地视频文件名（升序）。"""
    return sorted(disk_basenames - referenced_basenames)


def oss_orphans(referenced_keys: set[str], all_keys: list[str]) -> list[str]:
    """OSS 桶里存在、但 DB 未引用的 object key（保持原顺序）。"""
    return [k for k in all_keys if k not in referenced_keys]
