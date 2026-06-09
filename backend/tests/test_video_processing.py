import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.video_processing import (
    ensure_video_tools_available,
    build_mobile_video_filter,
    compress_mobile_mp4_in_place,
    prepare_playable_mp4_fast,
    resolve_video_tool,
    transcode_to_mobile_mp4,
)


class MobileVideoFilterTest(unittest.TestCase):
    def test_landscape_video_fits_720p_mobile_box(self):
        self.assertEqual(
            build_mobile_video_filter(1920, 1080),
            "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,"
            "fps=fps=30,"
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        )

    def test_portrait_video_fits_phone_portrait_box(self):
        self.assertEqual(
            build_mobile_video_filter(1080, 1920),
            "scale='min(720,iw)':'min(1280,ih)':force_original_aspect_ratio=decrease,"
            "fps=fps=30,"
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        )

    def test_square_video_fits_square_mobile_box(self):
        self.assertEqual(
            build_mobile_video_filter(1440, 1440),
            "scale='min(720,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,"
            "fps=fps=30,"
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        )


class MobileTranscodeTest(unittest.TestCase):
    def test_resolve_video_tool_finds_winget_install_when_path_is_missing(self):
        winget_ffmpeg = (
            Path("C:/Users/Admin/AppData/Local/Microsoft/WinGet/Packages")
            / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
            / "ffmpeg-8.1.1-full_build"
            / "bin"
            / "ffmpeg.exe"
        )

        with (
            patch("app.services.video_processing.shutil.which", return_value=None),
            patch("app.services.video_processing.Path.home", return_value=Path("C:/Users/Admin")),
            patch("app.services.video_processing.Path.exists", return_value=True),
            patch("app.services.video_processing.Path.glob", return_value=[winget_ffmpeg.parent]),
        ):
            self.assertEqual(resolve_video_tool("ffmpeg"), str(winget_ffmpeg))

    def test_missing_ffmpeg_tools_reports_clear_error(self):
        with (
            patch("app.services.video_processing.shutil.which", return_value=None),
            patch("app.services.video_processing.Path.exists", return_value=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "ffmpeg.*ffprobe"):
                ensure_video_tools_available()

    def test_prepare_playable_mp4_fast_remuxes_mp4_without_reencoding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_root = Path(temp_dir)
            source_path = upload_root / "videos" / "lesson.mp4"
            source_path.parent.mkdir(parents=True)
            source_path.write_bytes(b"original")

            def fake_run(cmd, **kwargs):
                if cmd[0] == "ffprobe":
                    return MagicMock(
                        stdout=json.dumps(
                            {
                                "streams": [{"width": 1920, "height": 1080}],
                                "format": {"duration": "30.2"},
                            }
                        ),
                        returncode=0,
                    )
                output_path = Path(cmd[-1])
                output_path.write_bytes(b"remuxed")
                return MagicMock(stdout="", stderr="", returncode=0)

            with (
                patch("app.services.video_processing.resolve_video_tool", side_effect=lambda tool: tool),
                patch("app.services.video_processing.subprocess.run", side_effect=fake_run) as run,
            ):
                result = prepare_playable_mp4_fast(source_path, upload_root)

            ffmpeg_cmd = next(
                call.args[0]
                for call in run.call_args_list
                if "copy" in call.args[0]
            )
            self.assertIn("-c", ffmpeg_cmd)
            self.assertIn("copy", ffmpeg_cmd)
            self.assertNotIn("libx264", ffmpeg_cmd)
            self.assertEqual(result.file_url, "/uploads/videos/lesson.mp4")
            self.assertEqual(result.file_size, len(b"remuxed"))
            self.assertEqual(result.resolution, "1920x1080")

    def test_compress_mobile_mp4_in_place_replaces_same_public_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_root = Path(temp_dir)
            final_path = upload_root / "videos" / "lesson.mp4"
            final_path.parent.mkdir(parents=True)
            final_path.write_bytes(b"playable")

            def fake_run(cmd, **kwargs):
                if cmd[0] == "ffprobe":
                    return MagicMock(
                        stdout=json.dumps(
                            {
                                "streams": [{"width": 1920, "height": 1080}],
                                "format": {"duration": "30.2"},
                            }
                        ),
                        returncode=0,
                    )
                output_path = Path(cmd[-1])
                output_path.write_bytes(b"compressed")
                return MagicMock(stdout="", stderr="", returncode=0)

            with (
                patch("app.services.video_processing.resolve_video_tool", side_effect=lambda tool: tool),
                patch("app.services.video_processing.subprocess.run", side_effect=fake_run) as run,
            ):
                result = compress_mobile_mp4_in_place(final_path, upload_root)

            ffmpeg_cmd = next(
                call.args[0]
                for call in run.call_args_list
                if "libx264" in call.args[0]
            )
            self.assertIn("libx264", ffmpeg_cmd)
            self.assertEqual(result.file_url, "/uploads/videos/lesson.mp4")
            self.assertEqual(final_path.read_bytes(), b"compressed")

    def test_transcode_uses_fast_mobile_mp4_settings_and_removes_original(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_root = Path(temp_dir)
            source_path = upload_root / "videos" / "lesson.mov"
            source_path.parent.mkdir(parents=True)
            source_path.write_bytes(b"original")

            def fake_run(cmd, **kwargs):
                if cmd[0] == "ffprobe":
                    return MagicMock(
                        stdout=json.dumps(
                            {
                                "streams": [{"width": 1080, "height": 1920}],
                                "format": {"duration": "65.4"},
                            }
                        ),
                        returncode=0,
                    )
                output_path = Path(cmd[-1])
                output_path.write_bytes(b"compressed")
                return MagicMock(stdout="", stderr="", returncode=0)

            with (
                patch(
                    "app.services.video_processing.resolve_video_tool",
                    side_effect=lambda tool: tool,
                ),
                patch("app.services.video_processing.subprocess.run", side_effect=fake_run) as run,
            ):
                result = transcode_to_mobile_mp4(source_path, upload_root)

            ffmpeg_cmd = next(
                call.args[0]
                for call in run.call_args_list
                if "libx264" in call.args[0]
            )
            self.assertIn("-preset", ffmpeg_cmd)
            self.assertIn("veryfast", ffmpeg_cmd)
            self.assertIn("-crf", ffmpeg_cmd)
            self.assertIn("28", ffmpeg_cmd)
            self.assertIn("-vf", ffmpeg_cmd)
            self.assertIn("min(720,iw)", ffmpeg_cmd[ffmpeg_cmd.index("-vf") + 1])
            self.assertIn("-map", ffmpeg_cmd)
            self.assertIn("0:v:0", ffmpeg_cmd)
            self.assertIn("0:a:0?", ffmpeg_cmd)
            self.assertIn("-b:a", ffmpeg_cmd)
            self.assertIn("96k", ffmpeg_cmd)

            self.assertEqual(result.file_url, "/uploads/videos/lesson.mp4")
            self.assertEqual(result.resolution, "1080x1920")
            self.assertEqual(result.duration, 65)
            self.assertEqual(result.file_size, len(b"compressed"))
            self.assertFalse(source_path.exists())


if __name__ == "__main__":
    unittest.main()
