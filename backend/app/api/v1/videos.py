"""Video management endpoints — includes chunked upload for large files."""

import hashlib
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import select, func

from app.core.config import settings
from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.video import Video
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.video import VideoCreate, VideoResponse, VideoUpdate

router = APIRouter()

CHUNK_DIR = Path(settings.upload_dir) / "chunks"
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".wmv", ".flv", ".mkv"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB

# ── video list / CRUD ──────────────────────────────────────────────

@router.get("/", response_model=PaginatedResponse[VideoResponse], summary="视频列表")
async def list_videos(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    category_id: int | None = None,
    status: str | None = None,
    keyword: str | None = None,
    is_required: bool | None = None,
):
    query = select(Video)
    if category_id is not None:
        query = query.where(Video.category_id == category_id)
    if status:
        query = query.where(Video.status == status)
    if keyword:
        query = query.where(Video.title.like(f"%{keyword}%"))
    if is_required is not None:
        query = query.where(Video.is_required == is_required)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Video.sort_order, Video.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    videos = result.scalars().all()

    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[VideoResponse.model_validate(v) for v in videos],
    )

@router.get("/{video_id}", response_model=VideoResponse, summary="获取视频详情")
async def get_video(video_id: int, session: SessionDep, user: CurrentUserDep):
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return VideoResponse.model_validate(video)

@router.post("/", response_model=VideoResponse, status_code=201, summary="创建视频")
async def create_video(body: VideoCreate, session: SessionDep, user: CurrentUserDep):
    video = Video(**body.model_dump())
    session.add(video)
    await session.flush()
    return VideoResponse.model_validate(video)

@router.put("/{video_id}", response_model=VideoResponse, summary="更新视频")
async def update_video(video_id: int, body: VideoUpdate, session: SessionDep, user: CurrentUserDep):
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(video, field, value)
    await session.flush()
    return VideoResponse.model_validate(video)

@router.delete("/{video_id}", response_model=MessageResponse, summary="删除视频")
async def delete_video(video_id: int, session: SessionDep, user: CurrentUserDep):
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    video.status = "archived"
    await session.flush()
    return MessageResponse(message="视频已归档")

# ── chunked upload ─────────────────────────────────────────────────

@router.post("/upload/init", summary="初始化分片上传")
async def init_chunked_upload(
    filename: str = Form(...),
    file_size: int = Form(...),
    user: CurrentUserDep = None,
):
    """Initialise a chunked upload session. Returns a unique upload_id."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过 2GB 限制")

    upload_id = uuid.uuid4().hex
    chunk_path = CHUNK_DIR / upload_id
    chunk_path.mkdir(parents=True, exist_ok=True)

    # Persist metadata so the merge step knows the original name and size
    (chunk_path / "meta.json").write_text(
        json.dumps({"filename": filename, "file_size": file_size}), encoding="utf-8"
    )

    return {"upload_id": upload_id, "chunk_dir": str(chunk_path)}


@router.post("/upload/chunk", summary="上传分片")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file: UploadFile = File(...),
    user: CurrentUserDep = None,
):
    """Receive a single chunk and write it to disk."""
    chunk_path = CHUNK_DIR / upload_id
    if not chunk_path.exists():
        raise HTTPException(status_code=404, detail="上传会话不存在或已过期")

    # Save chunk as 00001, 00002, …
    chunk_file = chunk_path / f"{chunk_index:05d}"
    content = await file.read()
    chunk_file.write_bytes(content)

    return {"upload_id": upload_id, "chunk": chunk_index, "size": len(content)}


@router.post("/upload/merge", summary="合并分片")
async def merge_chunks(
    upload_id: str = Form(...),
    session: SessionDep = None,
    user: CurrentUserDep = None,
):
    """Merge all uploaded chunks into a single video file, clean up the temp dir."""
    chunk_path = CHUNK_DIR / upload_id
    if not chunk_path.exists():
        raise HTTPException(status_code=404, detail="上传会话不存在或已过期")

    meta_file = chunk_path / "meta.json"
    if not meta_file.exists():
        raise HTTPException(status_code=400, detail="缺少上传元数据")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    original_filename = meta["filename"]
    ext = Path(original_filename).suffix.lower()

    out_filename = f"{uuid.uuid4().hex}{ext}"
    out_dir = Path(settings.upload_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_filename

    # Collect chunks in order
    chunk_files = sorted(chunk_path.glob("*"), key=lambda p: p.name)
    chunk_files = [c for c in chunk_files if c.name != "meta.json"]

    with out_path.open("wb") as dst:
        for cf in chunk_files:
            dst.write(cf.read_bytes())

    total_size = out_path.stat().st_size

    # Clean up chunk directory
    import shutil
    shutil.rmtree(chunk_path, ignore_errors=True)

    return {
        "filename": out_filename,
        "file_url": f"/uploads/{out_filename}",
        "file_size": total_size,
    }
