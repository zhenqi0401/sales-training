"""迁移 / 清理脚本的纯逻辑单测（不碰真实 OSS / DB / 磁盘）。"""

import unittest
from datetime import datetime

from scripts import _oss_ops as ops


class MigrationObjectKeyTest(unittest.TestCase):
    def test_uses_created_at_month_and_keeps_basename(self):
        key = ops.migration_object_key(datetime(2025, 3, 9), "abc123.mp4")
        self.assertEqual(key, "videos/202503/abc123.mp4")

    def test_missing_created_at_falls_back_to_legacy(self):
        key = ops.migration_object_key(None, "abc123.mp4")
        self.assertEqual(key, "videos/legacy/abc123.mp4")


class LocalOrphansTest(unittest.TestCase):
    def test_returns_disk_files_not_referenced(self):
        referenced = {"a.mp4", "b.mp4"}
        on_disk = {"a.mp4", "b.mp4", "junk1.mp4", "junk2.mp4"}
        self.assertEqual(ops.local_orphans(referenced, on_disk), ["junk1.mp4", "junk2.mp4"])

    def test_empty_when_all_referenced(self):
        self.assertEqual(ops.local_orphans({"a.mp4"}, {"a.mp4"}), [])


class OssOrphansTest(unittest.TestCase):
    def test_returns_keys_not_referenced(self):
        referenced = {"videos/202606/keep.mp4"}
        all_keys = ["videos/202606/keep.mp4", "videos/202606/junk.mp4"]
        self.assertEqual(ops.oss_orphans(referenced, all_keys), ["videos/202606/junk.mp4"])


class IsLocalUrlTest(unittest.TestCase):
    def test_local_and_oss_and_empty(self):
        self.assertTrue(ops.is_local_url("/uploads/videos/a.mp4"))
        self.assertFalse(ops.is_local_url("https://x.oss-cn-hangzhou.aliyuncs.com/videos/a.mp4"))
        self.assertFalse(ops.is_local_url(""))


if __name__ == "__main__":
    unittest.main()
