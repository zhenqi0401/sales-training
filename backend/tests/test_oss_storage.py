"""Tests for the OSS object-storage helper (app.services.oss_storage).

oss2 网络调用全部 mock，只验证我们这层封装的 key/URL 逻辑与调用契约。
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services import oss_storage


class _SettingsCtx:
    """Patch the OSS-related settings fields onto the live settings object."""

    def __init__(self, **overrides):
        self.overrides = {
            "oss_enabled": True,
            "oss_access_key_id": "ak-id",
            "oss_access_key_secret": "ak-secret",
            "oss_bucket": "my-bucket",
            "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "oss_public_base_url": "",
            **overrides,
        }
        self.patches = []

    def __enter__(self):
        for key, value in self.overrides.items():
            p = patch.object(oss_storage.settings, key, value)
            p.start()
            self.patches.append(p)
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()


class BuildPublicUrlTest(unittest.TestCase):
    def test_default_url_uses_bucket_and_endpoint(self):
        with _SettingsCtx():
            url = oss_storage.build_public_url("videos/202606/abc.mp4")
        self.assertEqual(
            url, "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
        )

    def test_custom_base_url_is_used_when_set(self):
        with _SettingsCtx(oss_public_base_url="https://cdn.example.com"):
            url = oss_storage.build_public_url("videos/202606/abc.mp4")
        self.assertEqual(url, "https://cdn.example.com/videos/202606/abc.mp4")

    def test_custom_base_url_trailing_slash_is_normalized(self):
        with _SettingsCtx(oss_public_base_url="https://cdn.example.com/"):
            url = oss_storage.build_public_url("videos/202606/abc.mp4")
        self.assertEqual(url, "https://cdn.example.com/videos/202606/abc.mp4")


class ObjectKeyFromUrlTest(unittest.TestCase):
    def test_extracts_key_from_default_url(self):
        with _SettingsCtx():
            key = oss_storage.object_key_from_url(
                "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
            )
        self.assertEqual(key, "videos/202606/abc.mp4")

    def test_extracts_key_from_custom_base_url(self):
        with _SettingsCtx(oss_public_base_url="https://cdn.example.com"):
            key = oss_storage.object_key_from_url(
                "https://cdn.example.com/videos/202606/abc.mp4"
            )
        self.assertEqual(key, "videos/202606/abc.mp4")

    def test_bare_key_is_returned_as_is(self):
        with _SettingsCtx():
            key = oss_storage.object_key_from_url("videos/202606/abc.mp4")
        self.assertEqual(key, "videos/202606/abc.mp4")


class IsOssUrlTest(unittest.TestCase):
    def test_absolute_http_url_is_oss(self):
        self.assertTrue(oss_storage.is_oss_url("https://x.aliyuncs.com/videos/a.mp4"))

    def test_local_uploads_path_is_not_oss(self):
        self.assertFalse(oss_storage.is_oss_url("/uploads/videos/a.mp4"))


class UploadFileTest(unittest.TestCase):
    def test_uploads_local_file_and_returns_public_url(self):
        fake_bucket = MagicMock()
        with _SettingsCtx(), patch.object(
            oss_storage, "_get_bucket", return_value=fake_bucket
        ):
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / "abc.mp4"
                src.write_bytes(b"video-bytes")
                url = oss_storage.upload_file(src, "videos/202606/abc.mp4")

        fake_bucket.put_object_from_file.assert_called_once_with(
            "videos/202606/abc.mp4", str(src)
        )
        self.assertEqual(
            url, "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
        )


class DownloadToTempTest(unittest.TestCase):
    def test_downloads_object_to_existing_temp_mp4(self):
        fake_bucket = MagicMock()

        def fake_get(key, local_path):
            Path(local_path).write_bytes(b"downloaded")

        fake_bucket.get_object_to_file.side_effect = fake_get

        with _SettingsCtx(), patch.object(
            oss_storage, "_get_bucket", return_value=fake_bucket
        ):
            temp_path = oss_storage.download_to_temp(
                "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
            )

        try:
            self.assertTrue(temp_path.exists())
            self.assertEqual(temp_path.suffix, ".mp4")
            args = fake_bucket.get_object_to_file.call_args[0]
            self.assertEqual(args[0], "videos/202606/abc.mp4")
            self.assertEqual(temp_path.read_bytes(), b"downloaded")
        finally:
            temp_path.unlink(missing_ok=True)


class GetBucketEndpointTest(unittest.TestCase):
    def test_endpoint_without_scheme_is_normalized_to_https(self):
        with _SettingsCtx(oss_endpoint="oss-cn-hangzhou.aliyuncs.com"), patch(
            "oss2.Auth"
        ), patch("oss2.Bucket") as bucket_cls:
            oss_storage._get_bucket()
        endpoint_arg = bucket_cls.call_args[0][1]
        self.assertEqual(endpoint_arg, "https://oss-cn-hangzhou.aliyuncs.com")

    def test_endpoint_with_scheme_is_left_as_is(self):
        with _SettingsCtx(oss_endpoint="https://oss-cn-hangzhou.aliyuncs.com"), patch(
            "oss2.Auth"
        ), patch("oss2.Bucket") as bucket_cls:
            oss_storage._get_bucket()
        endpoint_arg = bucket_cls.call_args[0][1]
        self.assertEqual(endpoint_arg, "https://oss-cn-hangzhou.aliyuncs.com")


class SignUrlTest(unittest.TestCase):
    def test_signs_get_url_for_object_key(self):
        fake_bucket = MagicMock()
        fake_bucket.sign_url.return_value = "https://signed.example/abc.mp4?Signature=xxx"
        with _SettingsCtx(), patch.object(
            oss_storage, "_get_bucket", return_value=fake_bucket
        ):
            url = oss_storage.sign_url(
                "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4",
                expires=3600,
            )
        fake_bucket.sign_url.assert_called_once_with(
            "GET", "videos/202606/abc.mp4", 3600, slash_safe=True
        )
        self.assertEqual(url, "https://signed.example/abc.mp4?Signature=xxx")


class ToPlayableUrlTest(unittest.TestCase):
    def test_oss_url_is_signed(self):
        with _SettingsCtx(), patch.object(
            oss_storage, "sign_url", return_value="https://signed"
        ) as sign:
            out = oss_storage.to_playable_url(
                "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
            )
        sign.assert_called_once()
        self.assertEqual(out, "https://signed")

    def test_local_path_is_returned_unchanged(self):
        with _SettingsCtx(), patch.object(oss_storage, "sign_url") as sign:
            out = oss_storage.to_playable_url("/uploads/videos/abc.mp4")
        sign.assert_not_called()
        self.assertEqual(out, "/uploads/videos/abc.mp4")

    def test_empty_value_is_returned_unchanged(self):
        with _SettingsCtx(), patch.object(oss_storage, "sign_url") as sign:
            out = oss_storage.to_playable_url("")
        sign.assert_not_called()
        self.assertEqual(out, "")


class DeleteObjectTest(unittest.TestCase):
    def test_deletes_object_by_key_resolved_from_url(self):
        fake_bucket = MagicMock()
        with _SettingsCtx(), patch.object(
            oss_storage, "_get_bucket", return_value=fake_bucket
        ):
            oss_storage.delete_object(
                "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
            )
        fake_bucket.delete_object.assert_called_once_with("videos/202606/abc.mp4")


if __name__ == "__main__":
    unittest.main()
