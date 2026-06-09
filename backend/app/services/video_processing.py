"""Utilities for compressing uploaded videos for mobile playback."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VideoMetadata:
    duration: int
    width: int
    height: int

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}" if self.width and self.height else ""


@dataclass(frozen=True)
class MobileVideoResult:
    file_url: str
    file_size: int
    duration: int
    resolution: str
    cover_url: str


def resolve_video_tool(tool: str) -> str | None:
    """Return an executable path for ffmpeg/ffprobe, including WinGet installs."""
    path_tool = shutil.which(tool)
    if path_tool:
        return path_tool

    if tool not in {"ffmpeg", "ffprobe"}:
        return None

    winget_root = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    package_dirs = [
        winget_root / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
        winget_root / "BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe",
        winget_root / "FFmpeg.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    ]
    for package_dir in package_dirs:
        if not package_dir.exists():
            continue
        for bin_dir in package_dir.glob("*/bin"):
            exe_path = bin_dir / f"{tool}.exe"
            if exe_path.exists():
                return str(exe_path)

    return None


def ensure_video_tools_available() -> None:
    """Fail early when ffmpeg or ffprobe is not available on PATH."""
    missing = [tool for tool in ("ffmpeg", "ffprobe") if resolve_video_tool(tool) is None]
    if missing:
        raise RuntimeError(
            "ffmpeg/ffprobe 未安装或未加入 PATH，请先安装 ffmpeg 并确认 ffmpeg -version 可用"
        )


def public_upload_url(path: Path, upload_root: Path) -> str:
    relative = path.relative_to(upload_root).as_posix()
    return f"/uploads/{relative}"


def probe_video(path: Path) -> VideoMetadata:
    """Read duration and video dimensions with ffprobe."""
    ensure_video_tools_available()
    result = subprocess.run(
        [
            resolve_video_tool("ffprobe") or "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    data: dict[str, Any] = json.loads(result.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    duration = int(float((data.get("format") or {}).get("duration") or 0))
    return VideoMetadata(
        duration=duration,
        width=int(stream.get("width") or 0),
        height=int(stream.get("height") or 0),
    )


def build_mobile_video_filter(width: int, height: int) -> str:
    """Return an ffmpeg filter that keeps aspect ratio and fits phone screens."""
    if width > height:
        max_width, max_height = 1280, 720
    elif height > width:
        max_width, max_height = 720, 1280
    else:
        max_width, max_height = 720, 720

    return (
        f"scale='min({max_width},iw)':'min({max_height},ih)':force_original_aspect_ratio=decrease,"
        "fps=fps=30,"
        "pad=ceil(iw/2)*2:ceil(ih/2)*2"
    )


def generate_mobile_cover(video_path: Path, upload_root: Path) -> str:
    """Generate a first-frame cover from the final compressed video."""
    ensure_video_tools_available()
    cover_dir = upload_root / "covers"
    cover_dir.mkdir(parents=True, exist_ok=True)
    cover_path = cover_dir / f"{video_path.stem}.jpg"

    subprocess.run(
        [
            resolve_video_tool("ffmpeg") or "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-q:v",
            "3",
            str(cover_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return public_upload_url(cover_path, upload_root) if cover_path.exists() else ""


def prepare_playable_mp4_fast(source_path: Path, upload_root: Path) -> MobileVideoResult:
    """Create a quickly playable MP4 without full re-encoding."""
    source_path = Path(source_path)
    upload_root = Path(upload_root)
    ensure_video_tools_available()
    metadata = probe_video(source_path)

    final_path = source_path.with_suffix(".mp4")
    tmp_path = final_path.with_name(f"{final_path.stem}.playable{final_path.suffix}")
    if tmp_path.exists():
        tmp_path.unlink()

    cmd = [
        resolve_video_tool("ffmpeg") or "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        "-max_muxing_queue_size",
        "1024",
        str(tmp_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        stderr_tail = (result.stderr or "")[-500:]
        raise RuntimeError(f"视频快速处理失败：{stderr_tail}")

    tmp_path.replace(final_path)
    if source_path != final_path:
        source_path.unlink(missing_ok=True)

    try:
        cover_url = generate_mobile_cover(final_path, upload_root)
    except Exception:
        cover_url = ""

    return MobileVideoResult(
        file_url=public_upload_url(final_path, upload_root),
        file_size=final_path.stat().st_size,
        duration=metadata.duration,
        resolution=metadata.resolution,
        cover_url=cover_url,
    )


def compress_mobile_mp4_in_place(final_path: Path, upload_root: Path) -> MobileVideoResult:
    """Compress a playable MP4 and atomically replace it at the same path."""
    final_path = Path(final_path)
    upload_root = Path(upload_root)
    ensure_video_tools_available()
    metadata = probe_video(final_path)

    tmp_path = final_path.with_name(f"{final_path.stem}.compressing{final_path.suffix}")
    if tmp_path.exists():
        tmp_path.unlink()

    cmd = [
        resolve_video_tool("ffmpeg") or "ffmpeg",
        "-y",
        "-i",
        str(final_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-vf",
        build_mobile_video_filter(metadata.width, metadata.height),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-ac",
        "2",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-max_muxing_queue_size",
        "1024",
        str(tmp_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if result.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        stderr_tail = (result.stderr or "")[-500:]
        raise RuntimeError(f"视频压缩失败：{stderr_tail}")

    tmp_path.replace(final_path)

    final_metadata = probe_video(final_path)
    try:
        cover_url = generate_mobile_cover(final_path, upload_root)
    except Exception:
        cover_url = ""

    return MobileVideoResult(
        file_url=public_upload_url(final_path, upload_root),
        file_size=final_path.stat().st_size,
        duration=final_metadata.duration,
        resolution=final_metadata.resolution,
        cover_url=cover_url,
    )


def transcode_to_mobile_mp4(source_path: Path, upload_root: Path) -> MobileVideoResult:
    """Create a playable MP4, then compress it for mobile playback."""
    playable = prepare_playable_mp4_fast(source_path, upload_root)
    final_path = Path(upload_root) / playable.file_url.removeprefix("/uploads/")
    return compress_mobile_mp4_in_place(final_path, upload_root)
