import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.v1 import videos
from app.models.category import Category
from app.models.video import Video
from app.schemas.video import VideoStatusUpdate


class VideoUploadWithoutTranscodeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.temp_dir.name)
        self.patches = [
            patch.object(videos, "UPLOAD_DIR", self.upload_root),
            patch.object(videos, "VIDEO_DIR", self.upload_root / "videos"),
            patch.object(videos, "COVER_DIR", self.upload_root / "covers"),
            patch.object(videos, "CHUNK_DIR", self.upload_root / "chunks"),
            # 本地存储用例：与环境 .env 的 OSS_ENABLED 解耦，强制走本地分支
            patch.object(videos.oss_storage, "is_enabled", return_value=False),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    async def test_upload_init_accepts_mp4_without_ffmpeg(self):
        result = await videos.init_chunked_upload(filename="lesson.mp4", file_size=12, user=None)

        self.assertTrue(result["upload_id"])
        self.assertTrue((videos.CHUNK_DIR / result["upload_id"] / "meta.json").exists())

    async def test_upload_init_rejects_non_mp4_after_transcode_removal(self):
        with self.assertRaises(HTTPException) as raised:
            await videos.init_chunked_upload(filename="lesson.mov", file_size=12, user=None)

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("mp4", raised.exception.detail.lower())

    async def test_merge_chunks_saves_original_mp4_without_processing(self):
        videos.ensure_upload_dirs()
        upload_id = "upload-demo"
        chunk_dir = videos.CHUNK_DIR / upload_id
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "meta.json").write_text(
            json.dumps({"filename": "lesson.mp4", "file_size": 10}),
            encoding="utf-8",
        )
        (chunk_dir / "00000").write_bytes(b"hello")
        (chunk_dir / "00001").write_bytes(b"world")

        result = await videos.merge_chunks(upload_id=upload_id, user=None)

        stored_file = self.upload_root / result["file_url"].removeprefix("/uploads/")
        self.assertEqual(stored_file.read_bytes(), b"helloworld")
        self.assertEqual(result["file_size"], 10)
        self.assertEqual(result["duration"], 0)
        self.assertEqual(result["resolution"], "")
        self.assertEqual(result["cover_url"], "")
        self.assertFalse(result["compressed"])
        self.assertFalse(result["compression_pending"])
        self.assertFalse(chunk_dir.exists())


class VideoUploadToOssTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.temp_dir.name)
        self.patches = [
            patch.object(videos, "UPLOAD_DIR", self.upload_root),
            patch.object(videos, "VIDEO_DIR", self.upload_root / "videos"),
            patch.object(videos, "COVER_DIR", self.upload_root / "covers"),
            patch.object(videos, "CHUNK_DIR", self.upload_root / "chunks"),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    async def test_merge_uploads_to_oss_and_removes_local_file(self):
        videos.ensure_upload_dirs()
        upload_id = "oss-upload"
        chunk_dir = videos.CHUNK_DIR / upload_id
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "meta.json").write_text(
            json.dumps({"filename": "lesson.mp4", "file_size": 10}),
            encoding="utf-8",
        )
        (chunk_dir / "00000").write_bytes(b"hello")
        (chunk_dir / "00001").write_bytes(b"world")

        oss_url = "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/deadbeef.mp4"
        upload_file = MagicMock(return_value=oss_url)
        with (
            patch.object(videos.oss_storage, "is_enabled", return_value=True),
            patch.object(
                videos.oss_storage, "build_object_key", return_value="videos/202606/deadbeef.mp4"
            ),
            patch.object(videos.oss_storage, "upload_file", upload_file),
        ):
            result = await videos.merge_chunks(upload_id=upload_id, user=None)

        # file_url 应为 OSS 公共地址
        self.assertEqual(result["file_url"], oss_url)
        self.assertEqual(result["file_size"], 10)
        self.assertFalse(result["compressed"])

        # upload_file 收到本地合并文件路径 + 带日期前缀的 key
        upload_file.assert_called_once()
        local_path, object_key = upload_file.call_args[0]
        self.assertEqual(object_key, "videos/202606/deadbeef.mp4")
        # 上传后本地临时文件应被删除
        self.assertFalse(Path(local_path).exists())
        self.assertFalse(chunk_dir.exists())


class MaterializeVideoForProcessingTest(unittest.IsolatedAsyncioTestCase):
    async def test_local_url_maps_to_upload_dir(self):
        with patch.object(videos, "UPLOAD_DIR", Path("/data/uploads")):
            path, is_temp = await videos._materialize_video_for_processing(
                "/uploads/videos/x.mp4"
            )
        self.assertEqual(path, Path("/data/uploads/videos/x.mp4"))
        self.assertFalse(is_temp)

    async def test_oss_url_downloads_to_temp(self):
        fake_temp = Path("/tmp/oss_abc.mp4")
        with patch.object(
            videos.oss_storage, "download_to_temp", return_value=fake_temp
        ) as download:
            path, is_temp = await videos._materialize_video_for_processing(
                "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/x.mp4"
            )
        download.assert_called_once_with(
            "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/x.mp4"
        )
        self.assertEqual(path, fake_temp)
        self.assertTrue(is_temp)


class _FakeSession:
    def __init__(self, video):
        self.video = video
        self.flushed = False

    async def get(self, model, id_):
        if model is Category:
            return None
        return self.video

    async def flush(self):
        self.flushed = True


class _FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args):
        self.tasks.append((func, args))


class VideoPublishPipelineStatusTest(unittest.IsolatedAsyncioTestCase):
    async def test_publishing_draft_moves_directly_to_generating(self):
        video = Video(
            id=8,
            title="Lesson",
            file_url="/uploads/videos/lesson.mp4",
            category_id=3,
            status="draft",
        )
        session = _FakeSession(video)
        tasks = _FakeBackgroundTasks()

        with (
            patch.object(videos, "ensure_video_schema", AsyncMock()),
            patch.object(videos, "load_lookup_data", AsyncMock(return_value=({}, {}))),
        ):
            response = await videos.update_video_status(
                video_id=8,
                body=VideoStatusUpdate(status="published"),
                session=session,
                user=SimpleNamespace(id=1),
                background_tasks=tasks,
            )

        self.assertEqual(video.status, "generating")
        self.assertEqual(response.status, "generating")
        self.assertEqual(len(tasks.tasks), 1)
        self.assertIs(tasks.tasks[0][0], videos._generate_questions_and_publish)

    async def test_retry_legacy_transcoding_moves_to_generating(self):
        video = Video(
            id=9,
            title="Legacy",
            file_url="/uploads/videos/legacy.mp4",
            category_id=3,
            status="transcoding",
        )
        session = _FakeSession(video)
        tasks = _FakeBackgroundTasks()

        with (
            patch.object(videos, "ensure_video_schema", AsyncMock()),
            patch.object(videos, "load_lookup_data", AsyncMock(return_value=({}, {}))),
        ):
            response = await videos.retry_video_pipeline(
                video_id=9,
                session=session,
                user=SimpleNamespace(id=1),
                background_tasks=tasks,
            )

        self.assertEqual(video.status, "generating")
        self.assertEqual(response.status, "generating")
        self.assertEqual(len(tasks.tasks), 1)
        self.assertIs(tasks.tasks[0][0], videos._generate_questions_and_publish)


class _DeleteFakeSession:
    def __init__(self, video):
        self.video = video
        self.deleted = False

    async def get(self, model, id_):
        return self.video

    async def delete(self, obj):
        self.deleted = True

    async def flush(self):
        pass


class DeleteVideoCleansOssTest(unittest.IsolatedAsyncioTestCase):
    async def test_deletes_oss_object_for_oss_video(self):
        oss_url = "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
        video = Video(id=5, title="x", file_url=oss_url, category_id=1, status="published")
        session = _DeleteFakeSession(video)

        delete_object = MagicMock()
        with (
            patch.object(videos, "ensure_video_schema", AsyncMock()),
            patch.object(videos.oss_storage, "delete_object", delete_object),
        ):
            await videos.delete_video(video_id=5, session=session, user=SimpleNamespace(id=1))

        self.assertTrue(session.deleted)
        delete_object.assert_called_once_with(oss_url)

    async def test_skips_oss_delete_for_local_video(self):
        video = Video(
            id=6, title="x", file_url="/uploads/videos/abc.mp4", category_id=1, status="published"
        )
        session = _DeleteFakeSession(video)

        delete_object = MagicMock()
        with (
            patch.object(videos, "ensure_video_schema", AsyncMock()),
            patch.object(videos.oss_storage, "delete_object", delete_object),
        ):
            await videos.delete_video(video_id=6, session=session, user=SimpleNamespace(id=1))

        self.assertTrue(session.deleted)
        delete_object.assert_not_called()


if __name__ == "__main__":
    unittest.main()
