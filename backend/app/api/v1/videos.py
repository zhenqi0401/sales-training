"""Video management endpoints."""

import asyncio
import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_, select, text

from app.core.config import settings
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
from app.models.category import Category
from app.models.product import Product
from app.models.question import Question
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
    MobileVideoResult,
    compress_mobile_mp4_in_place,
    ensure_video_tools_available,
    prepare_playable_mp4_fast,
    probe_video,
)

router = APIRouter()

UPLOAD_DIR = Path(settings.upload_dir)
VIDEO_DIR = UPLOAD_DIR / "videos"
COVER_DIR = UPLOAD_DIR / "covers"
CHUNK_DIR = UPLOAD_DIR / "chunks"
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi"}
ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
VALID_STATUSES = {"draft", "published", "archived", "generating", "transcoding"}
_VIDEO_SCHEMA_READY = False


async def _write_pipeline_log(video_id: int, step: str, status: str, message: str = "", error: str = "") -> None:
    """Write a pipeline step entry to the video's pipeline_log JSON field."""
    from app.core.database import async_session_factory
    import logging
    logger = logging.getLogger(__name__)
    try:
        async with async_session_factory() as session:
            async with session.begin():
                video = await session.get(Video, video_id)
                if not video:
                    return
                log = dict(video.pipeline_log or {})
                log[step] = {
                    "status": status,  # running, success, failed
                    "message": message,
                    "error": error,
                }
                video.pipeline_log = log
    except Exception:
        logger.exception("写入 pipeline_log 失败 video_id=%s", video_id)


async def _transcode_generate_publish(video_id: int, file_url: str, category_id: int | None, video_title: str) -> None:
    """后台压缩视频 → ASR 转录 → AI生成题目 → 上架。
    若已转码完成（resolution 有值）或视频文件 ≤ 100MB 则跳过压缩。
    任何步骤失败时回退为草稿状态，方便管理员重试。
    """
    from app.core.database import async_session_factory
    import logging
    logger = logging.getLogger(__name__)

    logger.info("🔧 后台任务启动 video_id=%s title=%s", video_id, video_title)

    TRANSCODE_SKIP_MAX_BYTES = 1 * 1024 * 1024 * 1024  # 1GB

    # 0. 重试时清理旧的 AI 生成题目，避免重复入库
    async with async_session_factory() as session:
        async with session.begin():
            from sqlalchemy import delete as sql_delete
            await session.execute(
                sql_delete(Question).where(Question.video_id == video_id, Question.source == "ai")
            )
            logger.info("后台任务: 已清理旧AI题目 video_id=%s", video_id)

    await _write_pipeline_log(video_id, "init", "running", "管线启动，清理旧数据")

    final_path = UPLOAD_DIR / file_url.removeprefix("/uploads/")
    if not final_path.exists():
        logger.error("视频文件不存在 video_id=%s path=%s", video_id, final_path)
    else:
        logger.info("视频文件存在 video_id=%s size=%s", video_id, final_path.stat().st_size)

    result = None
    skip_compress = False

    # 1. 检查是否需要转码
    async with async_session_factory() as session:
        video = await session.get(Video, video_id)
        if not video:
            logger.warning("后台任务: 视频不存在 video_id=%s，退出", video_id)
            return
        if video.status != "transcoding":
            logger.warning("后台任务: 视频状态不是transcoding video_id=%s status=%s，退出", video_id, video.status)
            return
        logger.info("后台任务: 当前状态=%s file_size=%s resolution=%s", video.status, video.file_size, video.resolution)
        if video.file_size and video.file_size <= TRANSCODE_SKIP_MAX_BYTES:
            skip_compress = True
            logger.info("后台任务: 小视频(≤1GB)，跳过压缩 video_id=%s size=%s", video_id, video.file_size)
            try:
                meta = await asyncio.to_thread(probe_video, final_path)
                result = MobileVideoResult(
                    file_url=file_url,
                    file_size=video.file_size or final_path.stat().st_size,
                    duration=meta.duration,
                    resolution=meta.resolution,
                    cover_url=video.cover_url or "",
                )
            except Exception:
                logger.warning("读取视频元数据失败 video_id=%s，仍跳过压缩", video_id)
        else:
            logger.info("后台任务: 需要压缩 video_id=%s size=%s", video_id, video.file_size)

    if not skip_compress:
        await _write_pipeline_log(video_id, "transcode", "running", "开始视频压缩")
        logger.info("后台任务: 开始压缩 video_id=%s", video_id)
        try:
            result = await asyncio.to_thread(compress_mobile_mp4_in_place, final_path, UPLOAD_DIR)
            logger.info("后台任务: 压缩完成 video_id=%s new_size=%s", video_id, result.file_size)
            await _write_pipeline_log(video_id, "transcode", "success", f"压缩完成，新大小 {result.file_size} bytes")
        except Exception as exc:
            logger.exception("视频转码失败 video_id=%s", video_id)
            await _write_pipeline_log(video_id, "transcode", "failed", "视频压缩失败", str(exc))
            # 转码失败 → 回退草稿，允许管理员重试
            async with async_session_factory() as session:
                async with session.begin():
                    video = await session.get(Video, video_id)
                    if video and video.status == "transcoding":
                        video.status = "draft"
                        logger.info("后台任务: 转码失败，回退草稿 video_id=%s", video_id)
            return

    if skip_compress:
        await _write_pipeline_log(video_id, "transcode", "skipped", "跳过压缩（已转码或小视频）")

    # 2. 更新转码结果并标记为 generating
    async with async_session_factory() as session:
        async with session.begin():
            video = await session.get(Video, video_id)
            if not video or video.status != "transcoding":
                logger.warning("后台任务: 步骤2状态检查失败 video_id=%s status=%s", video_id, video.status if video else 'None')
                return
            if result:
                video.file_size = result.file_size
                video.resolution = result.resolution
                if result.cover_url:
                    video.cover_url = result.cover_url
            video.status = "generating"
            logger.info("后台任务: 状态→generating video_id=%s", video_id)

    # 3. ASR 转录 + AI 生成题目
    generated_questions: list[dict[str, Any]] = []
    try:
        from app.services.ai_service import transcribe_video_audio, generate_questions_from_transcript
        logger.info("后台任务: 开始ASR转录 video_id=%s", video_id)
        await _write_pipeline_log(video_id, "asr", "running", "开始语音转文字")
        transcript = await transcribe_video_audio(final_path)
        logger.info("后台任务: ASR完成 video_id=%s chars=%s", video_id, len(transcript))
        await _write_pipeline_log(video_id, "asr", "success", f"转写完成，{len(transcript)} 字符")
        logger.info("后台任务: 开始AI生成题目 (文本模式) video_id=%s", video_id)
        await _write_pipeline_log(video_id, "ai_generate", "running", "开始 AI 生成题目")
        generated_questions = await generate_questions_from_transcript(
            transcript=transcript,
            video_title=video_title,
            count=5,
            difficulty_level="L2",
            question_type_ratios={"single": 100, "multiple": 0, "true_false": 0},
            category_id=category_id,
            video_id=video_id,
        )
        logger.info("后台任务: AI生成完成 video_id=%s count=%s", video_id, len(generated_questions))
        await _write_pipeline_log(video_id, "ai_generate", "success", f"生成 {len(generated_questions)} 道题目")
    except Exception as exc:
        logger.exception("AI 生成题目失败 video_id=%s", video_id)
        await _write_pipeline_log(video_id, "ai_generate", "failed", "ASR 或 AI 生成失败", str(exc))

    # 4. 持久化题目并上架
    async with async_session_factory() as session:
        async with session.begin():
            video = await session.get(Video, video_id)
            if not video or video.status != "generating":
                logger.warning("后台任务: 步骤4状态检查失败 video_id=%s status=%s", video_id, video.status if video else 'None')
                # 状态已被外部修改（如管理员回退为 draft），不再写入
                return

            if generated_questions:
                try:
                    for item in generated_questions:
                        item["source"] = "ai"
                        question = Question(**item)
                        session.add(question)
                    video.status = "published"
                    video.published_at = datetime.now(timezone.utc)
                    logger.info("后台任务: ✅完成 video_id=%s status=published questions=%s", video_id, len(generated_questions))
                    await _write_pipeline_log(video_id, "done", "success", f"管线完成，入库 {len(generated_questions)} 道题目")
                except Exception:
                    logger.exception("保存AI题目失败 video_id=%s", video_id)
                    video.status = "draft"
                    await _write_pipeline_log(video_id, "done", "failed", "保存题目失败")
            else:
                logger.warning("后台任务: AI生成题目为空，回退草稿 video_id=%s", video_id)
                video.status = "draft"
                await _write_pipeline_log(video_id, "done", "failed", "AI 未生成任何题目")


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
              AND COLUMN_NAME IN ('tags', 'product_ids', 'pipeline_log')
            """
        )
    )
    existing = {row[0] for row in rows.fetchall()}

    if "tags" not in existing:
        await session.execute(text("ALTER TABLE videos ADD COLUMN tags JSON NULL COMMENT 'Video tags'"))
    if "product_ids" not in existing:
        await session.execute(text("ALTER TABLE videos ADD COLUMN product_ids JSON NULL COMMENT 'Related product IDs'"))
    if "pipeline_log" not in existing:
        await session.execute(text("ALTER TABLE videos ADD COLUMN pipeline_log JSON NULL COMMENT 'Pipeline execution log'"))

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
        pipeline_log=video.pipeline_log,
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


@router.post("/", response_model=VideoResponse, status_code=201, summary="Create video",
             dependencies=[Depends(require_admin())])
async def create_video(body: VideoCreate, session: SessionDep, user: CurrentUserDep):
    await ensure_video_schema(session)
    data = normalize_video_payload(body.model_dump())
    category = await require_active_category(session, data.get("category_id"))
    # 上传后固定为草稿状态，不自动转码
    data["status"] = "draft"
    data.pop("published_at", None)
    video = Video(**data)
    session.add(video)
    await session.flush()
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.put("/{video_id:int}", response_model=VideoResponse, summary="Update video",
            dependencies=[Depends(require_admin())])
async def update_video(video_id: int, body: VideoUpdate, session: SessionDep, user: CurrentUserDep, background_tasks: BackgroundTasks):
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    data = normalize_video_payload(body.model_dump(exclude_unset=True))
    category: Category | None = None
    if "category_id" in data:
        category = await require_active_category(session, data["category_id"])
    trigger_transcode = False
    if "status" in data:
        validate_status(data["status"])
        if data["status"] == "published" and video.status == "draft":
            data["status"] = "transcoding"
            data["published_at"] = datetime.now(timezone.utc)
            trigger_transcode = True
        elif data["status"] == "published" and video.status == "archived":
            data["published_at"] = datetime.now(timezone.utc)
        elif data["status"] != "published":
            data["published_at"] = None
    for field, value in data.items():
        setattr(video, field, value)

    await session.flush()
    if trigger_transcode:
        background_tasks.add_task(_transcode_generate_publish, video.id, video.file_url, video.category_id, video.title)
    if category is None:
        category = await session.get(Category, video.category_id) if video.category_id else None
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.put("/{video_id:int}/status", response_model=VideoResponse, summary="Update video status",
            dependencies=[Depends(require_admin())])
async def update_video_status(
    video_id: int,
    body: VideoStatusUpdate,
    session: SessionDep,
    user: CurrentUserDep,
    background_tasks: BackgroundTasks,
):
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    validate_status(body.status)
    # 上架时触发后台转码（仅草稿需要，已下架的直接上架）
    if body.status == "published" and video.status == "draft":
        video.status = "transcoding"
        video.published_at = datetime.now(timezone.utc)
        await session.flush()
        background_tasks.add_task(_transcode_generate_publish, video.id, video.file_url, video.category_id, video.title)
    elif body.status == "published" and video.status == "archived":
        video.status = "published"
        video.published_at = datetime.now(timezone.utc)
        await session.flush()
    elif body.status == "draft" and video.status in ("transcoding", "generating"):
        # 允许将卡住的管线回退为草稿
        video.status = "draft"
        video.published_at = None
        await session.flush()
    else:
        video.status = body.status
        video.published_at = datetime.now(timezone.utc) if body.status == "published" else None
        await session.flush()
    category = await session.get(Category, video.category_id) if video.category_id else None
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.post("/{video_id:int}/retry", response_model=VideoResponse, summary="Retry pipeline for stuck video",
             dependencies=[Depends(require_admin())])
async def retry_video_pipeline(
    video_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    background_tasks: BackgroundTasks,
):
    """重新触发转码 → ASR → AI 出题管线。
    适用于卡在 transcoding 或 generating 状态的视频。
    """
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status not in ("transcoding", "generating", "draft"):
        raise HTTPException(status_code=400, detail="只有草稿、转码中或生成中状态的视频可以重新处理")

    # 重置为 transcoding 并触发后台管线
    video.status = "transcoding"
    video.published_at = datetime.now(timezone.utc)
    await session.flush()
    background_tasks.add_task(_transcode_generate_publish, video.id, video.file_url, video.category_id, video.title)

    category = await session.get(Category, video.category_id) if video.category_id else None
    _, products = await load_lookup_data(session, [video])
    return await build_video_response(video, category, products)


@router.get("/{video_id:int}/pipeline-log", summary="Get pipeline execution log",
            dependencies=[Depends(require_admin())])
async def get_pipeline_log(
    video_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """返回最近一次管线执行的日志摘要，前端可据此显示进度。"""
    await ensure_video_schema(session)
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return {
        "video_id": video.id,
        "status": video.status,
        "log": video.pipeline_log or {},
    }


@router.post("/batch/status", response_model=MessageResponse, summary="Batch update video status",
             dependencies=[Depends(require_admin())])
async def batch_update_video_status(
    body: VideoBatchStatusUpdate,
    session: SessionDep,
    user: CurrentUserDep,
    background_tasks: BackgroundTasks,
):
    await ensure_video_schema(session)
    validate_status(body.status)
    if not body.ids:
        raise HTTPException(status_code=400, detail="No videos selected")

    videos = (await session.execute(select(Video).where(Video.id.in_(body.ids)))).scalars().all()
    # 上架时触发后台转码（仅草稿需要，已下架的直接上架）
    if body.status == "published":
        published_at = datetime.now(timezone.utc)
        for video in videos:
            if video.status == "draft":
                video.status = "transcoding"
                video.published_at = published_at
                background_tasks.add_task(_transcode_generate_publish, video.id, video.file_url, video.category_id, video.title)
            elif video.status == "archived":
                video.status = "published"
                video.published_at = published_at
    else:
        published_at = datetime.now(timezone.utc) if body.status == "published" else None
        for video in videos:
            video.status = body.status
            video.published_at = published_at
    await session.flush()
    return MessageResponse(message=f"Updated {len(videos)} video(s)")


@router.delete("/{video_id:int}", response_model=MessageResponse, summary="Delete video",
               dependencies=[Depends(require_admin())])
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
