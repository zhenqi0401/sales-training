"""Video management endpoints."""

import asyncio
import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_, select, text

from app.core.config import settings
from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.category import Category
from app.models.product import Product
from app.models.video import Video
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.video import (
    VideoBatchStatusUpdate,
    VideoCreate,
    VideoResponse,
    VideoStatusUpdate,
    VideoUpdate,
)
from app.services.video_processing import (
    compress_mobile_mp4_in_place,
    ensure_video_tools_available,
    prepare_playable_mp4_fast,
)

router = APIRouter()

UPLOAD_DIR = Path(settings.upload_dir)
VIDEO_DIR = UPLOAD_DIR / "videos"
COVER_DIR = UPLOAD_DIR / "covers"
CHUNK_DIR = UPLOAD_DIR / "chunks"
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi"}
ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
VALID_STATUSES = {"draft", "published", "archived"}
_VIDEO_SCHEMA_READY = False


async def _transcode_and_publish(video_id: int, file_url: str) -> None:
    """后台压缩视频，完成后将状态更新为已上架。"""
    from app.core.database import async_session_factory

    final_path = UPLOAD_DIR / file_url.removeprefix("/uploads/")
    result = None
    try:
        result = await asyncio.to_thread(compress_mobile_mp4_in_place, final_path, UPLOAD_DIR)
    except Exception:
        pass

    async with async_session_factory() as session:
        async with session.begin():
            video = await session.get(Video, video_id)
            if video and video.status == "transcoding":
                video.status = "published"
                video.published_at = datetime.now(timezone.utc)
                if result:
                    video.file_size = result.file_size
                    video.resolution = result.resolution
                    if result.cover_url:
                        video.cover_url = result.cover_url


def ensure_upload_dirs() -> None:
    """Create upload folders if they do not exist."""
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)


def ensure_video_compression_ready() -> None:
    try:
        ensure_video_tools_available()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid video status")


async def require_active_category(session: SessionDep, category_id: int | None) -> Category:
    if category_id is None:
        raise HTTPException(status_code=400, detail="请选择所属分类")
    category = await session.get(Category, category_id)
    if not category or not category.is_active:
        raise HTTPException(status_code=400, detail="所属分类不存在或已停用")
    return category


async def ensure_video_schema(session: SessionDep) -> None:
    """Backfill FR-A05 video columns for databases created before migrations."""
    global _VIDEO_SCHEMA_READY
    if _VIDEO_SCHEMA_READY:
        return

    bind = session.get_bind()
    dialect = bind.dialect.name if bind else ""
    if dialect != "mysql":
        _VIDEO_SCHEMA_READY = True
        return

    rows = await session.execute(
        text(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'videos'
              AND COLUMN_NAME IN ('tags', 'product_ids')
            """
        )
    )
    existing = {row[0] for row in rows.fetchall()}

    if "tags" not in existing:
        await session.execute(text("ALTER TABLE videos ADD COLUMN tags JSON NULL COMMENT 'Video tags'"))
    if "product_ids" not in existing:
        await session.execute(text("ALTER TABLE videos ADD COLUMN product_ids JSON NULL COMMENT 'Related product IDs'"))

    _VIDEO_SCHEMA_READY = True


def public_upload_url(path: Path) -> str:
    """Build a URL served by the FastAPI static uploads mount or Nginx."""
    relative = path.relative_to(UPLOAD_DIR).as_posix()
    return f"/uploads/{relative}"


def normalize_video_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Accept both frontend camelCase aliases and backend snake_case fields."""
    aliases = {
        "url": "file_url",
        "coverUrl": "cover_url",
        "categoryId": "category_id",
        "fileSize": "file_size",
        "sortOrder": "sort_order",
        "required": "is_required",
        "isRequired": "is_required",
        "estDuration": "est_duration",
        "productIds": "product_ids",
    }
    normalized = dict(data)
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized.pop(source)
        else:
            normalized.pop(source, None)
    return normalized


async def build_video_response(
    video: Video,
    category: Category | None = None,
    products: dict[int, Product] | None = None,
) -> VideoResponse:
    product_ids = video.product_ids or []
    products = products or {}
    return VideoResponse(
        id=video.id,
        title=video.title,
        description=video.description or "",
        category_id=video.category_id,
        category_name=category.name if category else None,
        file_url=video.file_url,
        cover_url=video.cover_url or "",
        tags=video.tags or [],
        product_ids=product_ids,
        product_names=[products[id_].name for id_ in product_ids if id_ in products],
        duration=video.duration or 0,
        resolution=video.resolution or "",
        file_size=video.file_size or 0,
        status=video.status,
        sort_order=video.sort_order,
        is_required=video.is_required,
        est_duration=video.est_duration or 0,
        published_at=video.published_at,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


async def load_lookup_data(session: SessionDep, videos: list[Video]) -> tuple[dict[int, Category], dict[int, Product]]:
    category_ids = [video.category_id for video in videos if video.category_id is not None]
    product_ids = sorted({id_ for video in videos for id_ in (video.product_ids or [])})
    categories: dict[int, Category] = {}
    products: dict[int, Product] = {}

    if category_ids:
        categories = {
            category.id: category
            for category in (
                await session.execute(select(Category).where(Category.id.in_(category_ids)))
            ).scalars().all()
        }
    if product_ids:
        products = {
            product.id: product
            for product in (
                await session.execute(select(Product).where(Product.id.in_(product_ids)))
            ).scalars().all()
        }
    return categories, products


@router.get("/", response_model=PaginatedResponse[VideoResponse], summary="Video list")
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
    await ensure_video_schema(session)
    query = select(Video)
    if category_id is not None:
        query = query.where(Video.category_id == category_id)
    if status:
        query = query.where(Video.status == status)
    if keyword:
        query = query.where(or_(Video.title.like(f"%{keyword}%"), Video.description.like(f"%{keyword}%")))
    if is_required is not None:
        query = query.where(Video.is_required == is_required)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Video.id.desc()).offset((page - 1) * page_size).limit(page_size)
    videos = (await session.execute(query)).scalars().all()
    categories, products = await load_lookup_data(session, list(videos))

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[
            await build_video_response(video, categories.get(video.category_id), products)
            for video in videos
        ],
    )


@router.get("/{video_id:int}", response_model=VideoResponse, summary="Get video detail")
async def get_video(video_id: int, session: SessionDep, user: CurrentUserDep):
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    category = await session.get(Category, video.category_id) if video.category_id else None
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.post("/", response_model=VideoResponse, status_code=201, summary="Create video")
async def create_video(body: VideoCreate, session: SessionDep, user: CurrentUserDep, background_tasks: BackgroundTasks):
    await ensure_video_schema(session)
    data = normalize_video_payload(body.model_dump())
    category = await require_active_category(session, data.get("category_id"))
    data["status"] = "transcoding"
    data.pop("published_at", None)
    video = Video(**data)
    session.add(video)
    await session.flush()
    background_tasks.add_task(_transcode_and_publish, video.id, video.file_url)
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.put("/{video_id:int}", response_model=VideoResponse, summary="Update video")
async def update_video(video_id: int, body: VideoUpdate, session: SessionDep, user: CurrentUserDep):
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    data = normalize_video_payload(body.model_dump(exclude_unset=True))
    category: Category | None = None
    if "category_id" in data:
        category = await require_active_category(session, data["category_id"])
    if "status" in data:
        validate_status(data["status"])
        if data["status"] == "published" and video.status != "published":
            data["published_at"] = datetime.now(timezone.utc)
        elif data["status"] != "published":
            data["published_at"] = None
    for field, value in data.items():
        setattr(video, field, value)

    await session.flush()
    if category is None:
        category = await session.get(Category, video.category_id) if video.category_id else None
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.put("/{video_id:int}/status", response_model=VideoResponse, summary="Update video status")
async def update_video_status(
    video_id: int,
    body: VideoStatusUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    validate_status(body.status)
    video.status = body.status
    video.published_at = datetime.now(timezone.utc) if body.status == "published" else None
    await session.flush()
    category = await session.get(Category, video.category_id) if video.category_id else None
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.post("/batch/status", response_model=MessageResponse, summary="Batch update video status")
async def batch_update_video_status(
    body: VideoBatchStatusUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    await ensure_video_schema(session)
    validate_status(body.status)
    if not body.ids:
        raise HTTPException(status_code=400, detail="No videos selected")

    videos = (await session.execute(select(Video).where(Video.id.in_(body.ids)))).scalars().all()
    published_at = datetime.now(timezone.utc) if body.status == "published" else None
    for video in videos:
        video.status = body.status
        video.published_at = published_at
    await session.flush()
    return MessageResponse(message=f"Updated {len(videos)} video(s)")


@router.delete("/{video_id:int}", response_model=MessageResponse, summary="Delete video")
async def delete_video(video_id: int, session: SessionDep, user: CurrentUserDep):
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    await session.delete(video)
    await session.flush()
    return MessageResponse(message="Video deleted")


@router.post("/upload/cover", summary="Upload generated video cover")
async def upload_generated_cover(file: UploadFile = File(...), user: CurrentUserDep = None):
    ensure_upload_dirs()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_COVER_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only jpg, png and webp covers are supported")

    content = await file.read()
    out_path = COVER_DIR / f"{uuid.uuid4().hex}{ext}"
    out_path.write_bytes(content)
    return {"cover_url": public_upload_url(out_path)}


@router.post("/upload/init", summary="Initialise chunked upload")
async def init_chunked_upload(
    filename: str = Form(...),
    file_size: int = Form(...),
    user: CurrentUserDep = None,
):
    ensure_upload_dirs()
    ensure_video_compression_ready()
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only mp4, mov and avi videos are supported")
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 2GB limit")

    upload_id = uuid.uuid4().hex
    chunk_path = CHUNK_DIR / upload_id
    chunk_path.mkdir(parents=True, exist_ok=True)
    (chunk_path / "meta.json").write_text(
        json.dumps({"filename": filename, "file_size": file_size}),
        encoding="utf-8",
    )
    return {"upload_id": upload_id}


@router.post("/upload/chunk", summary="Upload chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file: UploadFile = File(...),
    user: CurrentUserDep = None,
):
    chunk_path = CHUNK_DIR / upload_id
    if not chunk_path.exists():
        raise HTTPException(status_code=404, detail="Upload session not found")
    if chunk_index < 0 or chunk_index >= total_chunks:
        raise HTTPException(status_code=400, detail="Invalid chunk index")

    content = await file.read()
    (chunk_path / f"{chunk_index:05d}").write_bytes(content)
    return {"upload_id": upload_id, "chunk": chunk_index, "size": len(content)}


@router.post("/upload/merge", summary="Merge chunks and compress for mobile")
async def merge_chunks(
    upload_id: str = Form(...),
    user: CurrentUserDep = None,
):
    ensure_upload_dirs()
    chunk_path = CHUNK_DIR / upload_id
    if not chunk_path.exists():
        raise HTTPException(status_code=404, detail="Upload session not found")

    meta_file = chunk_path / "meta.json"
    if not meta_file.exists():
        raise HTTPException(status_code=400, detail="Missing upload metadata")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    original_filename = meta["filename"]
    expected_size = int(meta.get("file_size") or 0)
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only mp4, mov and avi videos are supported")

    chunk_files = sorted(c for c in chunk_path.glob("*") if c.name != "meta.json")
    if not chunk_files:
        raise HTTPException(status_code=400, detail="No chunks uploaded")

    out_path = VIDEO_DIR / f"{uuid.uuid4().hex}{ext}"
    digest = hashlib.sha256()
    with out_path.open("wb") as dst:
        for chunk_file in chunk_files:
            content = chunk_file.read_bytes()
            digest.update(content)
            dst.write(content)

    total_size = out_path.stat().st_size
    if total_size > MAX_FILE_SIZE or (expected_size and total_size != expected_size):
        out_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Merged file size is invalid")

    shutil.rmtree(chunk_path, ignore_errors=True)
    try:
        playable = prepare_playable_mp4_fast(out_path, UPLOAD_DIR)
    except Exception as exc:
        out_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=str(exc) or "视频快速处理失败，请重新上传或更换格式",
        ) from exc

    return {
        "filename": Path(playable.file_url).name,
        "upload_id": upload_id,
        "file_url": playable.file_url,
        "file_size": playable.file_size,
        "duration": playable.duration,
        "resolution": playable.resolution,
        "cover_url": playable.cover_url,
        "sha256": digest.hexdigest(),
        "compressed": False,
        "compression_pending": True,
    }
