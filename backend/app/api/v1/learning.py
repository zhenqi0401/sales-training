"""Learning progress and training-home endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func, select

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.category import Category
from app.models.learning_progress import LearningProgress
from app.models.store import Store
from app.models.user import User
from app.models.video import Video
from app.schemas.common import PaginatedResponse
from app.schemas.user import ApiResponse


class ProgressUpdate(BaseModel):
    """Update learning progress payload."""

    video_id: int | None = Field(default=None, alias="videoId")
    progress_percent: float | None = Field(default=None, alias="progress")
    watch_duration: int | None = Field(default=None, alias="watchDuration")
    last_position: int | None = Field(default=None, alias="lastPosition")
    completed: bool | None = None
    status: str | None = None

    model_config = {"populate_by_name": True}


class ProgressResponse(BaseModel):
    """Learning progress read model."""
    id: int
    user_id: int
    video_id: int
    progress_percent: float
    watch_duration: int
    last_position: int
    status: str
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    video_title: Optional[str] = None

    model_config = {"from_attributes": True}


router = APIRouter()


def envelope(data: object | None = None, message: str = "success") -> ApiResponse:
    """Return the response shape consumed by training-web."""
    return ApiResponse(message=message, data=data)


def format_minutes(seconds: int | None) -> int:
    """Convert stored watch seconds into whole display minutes."""
    if not seconds:
        return 0
    return max(1, round(seconds / 60))


def progress_status(progress: LearningProgress | None) -> tuple[int, bool, int]:
    """Return frontend progress percent, completion flag and watched seconds."""
    if not progress:
        return 0, False, 0
    percent = int(round(progress.progress_percent or 0))
    completed = progress.status == "completed" or percent >= 100
    return min(100, max(0, percent)), completed, progress.watch_duration or 0


def video_payload(video: Video, progress: LearningProgress | None = None) -> dict:
    """Map backend video fields to the training-web course card shape."""
    percent, completed, watch_duration = progress_status(progress)
    return {
        "id": video.id,
        "categoryId": video.category_id,
        "title": video.title,
        "cover": video.cover_url or "",
        "url": video.file_url or "",
        "duration": video.duration or (video.est_duration or 0) * 60,
        "watchDuration": watch_duration,
        "completed": completed,
        "progress": percent,
        "description": video.description or "",
        "resolution": video.resolution or "",
        "讲师": "培训讲师",
        "createdAt": video.created_at.isoformat() if video.created_at else "",
        "required": bool(video.is_required),
        "estDuration": video.est_duration or 0,
    }


async def user_video_progress_map(session: SessionDep, user_id: int, video_ids: list[int]) -> dict[int, LearningProgress]:
    if not video_ids:
        return {}
    records = (
        await session.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == user_id,
                LearningProgress.video_id.in_(video_ids),
            )
        )
    ).scalars().all()
    return {record.video_id: record for record in records}


def period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "day":
        return today
    if period == "month":
        return today.replace(day=1)
    return today - timedelta(days=today.weekday())


async def count_streak_days(session: SessionDep, user_id: int) -> int:
    records = (
        await session.execute(
            select(LearningProgress.completed_at)
            .where(
                LearningProgress.user_id == user_id,
                LearningProgress.status == "completed",
                LearningProgress.completed_at.is_not(None),
            )
            .order_by(desc(LearningProgress.completed_at))
        )
    ).scalars().all()

    completed_dates = {
        item.astimezone(timezone.utc).date() if item.tzinfo else item.date()
        for item in records
        if item
    }
    cursor = datetime.now(timezone.utc).date()
    streak = 0
    while cursor in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("/categories", response_model=ApiResponse, summary="培训端课程分类")
async def list_training_categories(session: SessionDep, user: CurrentUserDep):
    categories = (
        await session.execute(
            select(Category)
            .where(Category.is_active == True, Category.parent_id.is_(None))
            .order_by(Category.sort_order, Category.id)
        )
    ).scalars().all()

    items: list[dict] = []
    for category in categories:
        video_ids = (
            await session.execute(
                select(Video.id).where(Video.category_id == category.id, Video.status == "published")
            )
        ).scalars().all()
        completed_count = 0
        if video_ids:
            completed_count = (
                await session.execute(
                    select(func.count())
                    .select_from(LearningProgress)
                    .where(
                        LearningProgress.user_id == user.id,
                        LearningProgress.video_id.in_(video_ids),
                        LearningProgress.status == "completed",
                    )
                )
            ).scalar() or 0
        items.append(
            {
                "id": category.id,
                "code": category.code,
                "name": category.name,
                "icon": category.icon or "",
                "description": category.description or "",
                "videoCount": len(video_ids),
                "completedCount": completed_count,
                "sort": category.sort_order,
            }
        )
    return envelope(items)


@router.get("/categories/{category_id:int}/videos", response_model=ApiResponse, summary="培训端分类课程")
async def list_training_category_videos(category_id: int, session: SessionDep, user: CurrentUserDep):
    videos = (
        await session.execute(
            select(Video)
            .where(Video.category_id == category_id, Video.status == "published")
            .order_by(Video.sort_order, Video.id.desc())
        )
    ).scalars().all()
    progress_map = await user_video_progress_map(session, user.id, [video.id for video in videos])
    return envelope([video_payload(video, progress_map.get(video.id)) for video in videos])


@router.get("/videos/{video_id:int}", response_model=ApiResponse, summary="培训端课程详情")
async def get_training_video(video_id: int, session: SessionDep, user: CurrentUserDep):
    video = await session.get(Video, video_id)
    if not video or video.status != "published":
        raise HTTPException(status_code=404, detail="课程不存在")
    progress_map = await user_video_progress_map(session, user.id, [video.id])
    return envelope(video_payload(video, progress_map.get(video.id)))


@router.get("/stats", response_model=ApiResponse, summary="培训首页学习统计")
async def get_training_stats(session: SessionDep, user: CurrentUserDep):
    total_videos = (
        await session.execute(select(func.count()).select_from(Video).where(Video.status == "published"))
    ).scalar() or 0

    completed_videos = (
        await session.execute(
            select(func.count()).select_from(LearningProgress).where(
                LearningProgress.user_id == user.id,
                LearningProgress.status == "completed",
            )
        )
    ).scalar() or 0

    in_progress_videos = (
        await session.execute(
            select(func.count()).select_from(LearningProgress).where(
                LearningProgress.user_id == user.id,
                LearningProgress.status == "in_progress",
            )
        )
    ).scalar() or 0

    total_duration_seconds = (
        await session.execute(
            select(func.coalesce(func.sum(LearningProgress.watch_duration), 0)).where(
                LearningProgress.user_id == user.id
            )
        )
    ).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_duration_seconds = (
        await session.execute(
            select(func.coalesce(func.sum(LearningProgress.watch_duration), 0)).where(
                LearningProgress.user_id == user.id,
                LearningProgress.updated_at >= today_start,
            )
        )
    ).scalar() or 0

    return envelope(
        {
            "totalVideos": total_videos,
            "completedVideos": completed_videos,
            "inProgressVideos": in_progress_videos,
            "pendingVideos": max(total_videos - completed_videos - in_progress_videos, 0),
            "totalDuration": format_minutes(total_duration_seconds),
            "todayDuration": format_minutes(today_duration_seconds),
            "streakDays": await count_streak_days(session, user.id),
        }
    )


@router.get("/daily-tasks", response_model=ApiResponse, summary="今日必修学习任务")
async def get_daily_tasks(session: SessionDep, user: CurrentUserDep):
    completed_ids = set(
        (
            await session.execute(
                select(LearningProgress.video_id).where(
                    LearningProgress.user_id == user.id,
                    LearningProgress.status == "completed",
                )
            )
        ).scalars().all()
    )

    videos = (
        await session.execute(
            select(Video)
            .where(Video.status == "published", Video.is_required == True)
            .order_by(Video.sort_order, Video.id.desc())
            .limit(6)
        )
    ).scalars().all()

    deadline = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    tasks = [
        {
            "id": video.id,
            "title": video.title,
            "description": f"必修课程 · 预计 {video.est_duration or max(1, round((video.duration or 0) / 60))} 分钟",
            "type": "video",
            "targetId": video.id,
            "completed": video.id in completed_ids,
            "reward": max(5, (video.est_duration or 5) * 2),
            "deadline": deadline,
        }
        for video in videos
    ]
    return envelope(tasks)


@router.post("/daily-tasks/{task_id:int}/complete", response_model=ApiResponse, summary="完成今日任务")
async def complete_daily_task(task_id: int, session: SessionDep, user: CurrentUserDep):
    video = await session.get(Video, task_id)
    if not video:
        raise HTTPException(status_code=404, detail="任务不存在")
    now = datetime.now(timezone.utc)
    record = (
        await session.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == user.id,
                LearningProgress.video_id == task_id,
            )
        )
    ).scalar_one_or_none()
    if record:
        record.progress_percent = 100
        record.status = "completed"
        record.watch_duration = max(record.watch_duration or 0, video.duration or 0)
        record.completed_at = record.completed_at or now
    else:
        session.add(
            LearningProgress(
                user_id=user.id,
                video_id=task_id,
                progress_percent=100,
                watch_duration=video.duration or 0,
                last_position=video.duration or 0,
                status="completed",
                completed_at=now,
            )
        )
    await session.flush()
    return envelope(message="任务已完成")


@router.get("/recent", response_model=ApiResponse, summary="最近学习课程")
async def get_recent_courses(session: SessionDep, user: CurrentUserDep):
    rows = (
        await session.execute(
            select(LearningProgress, Video)
            .join(Video, Video.id == LearningProgress.video_id)
            .where(
                LearningProgress.user_id == user.id,
                Video.status == "published",
                LearningProgress.status != "not_started",
            )
            .order_by(desc(LearningProgress.updated_at))
            .limit(5)
        )
    ).all()
    return envelope([video_payload(video, progress) for progress, video in rows])


@router.get("/leaderboard", response_model=ApiResponse, summary="学习排行榜")
async def get_leaderboard(period: str = "week", session: SessionDep = None, user: CurrentUserDep = None):
    if period not in {"day", "week", "month"}:
        period = "week"

    start_at = period_start(period)
    rows = (
        await session.execute(
            select(
                User.id,
                User.real_name,
                User.username,
                User.avatar,
                Store.name.label("store_name"),
                func.coalesce(func.sum(LearningProgress.watch_duration), 0).label("watch_seconds"),
                func.coalesce(
                    func.sum(case((LearningProgress.status == "completed", 1), else_=0)),
                    0,
                ).label("completed"),
            )
            .join(LearningProgress, LearningProgress.user_id == User.id)
            .outerjoin(Store, Store.id == User.store_id)
            .where(
                User.is_active == True,
                LearningProgress.updated_at >= start_at,
            )
            .group_by(User.id, User.real_name, User.username, User.avatar, Store.name)
            .order_by(desc("watch_seconds"))
            .limit(10)
        )
    ).all()

    entries = []
    for idx, row in enumerate(rows, start=1):
        score = int(round((row.watch_seconds or 0) / 60)) + int(row.completed or 0) * 10
        entries.append(
            {
                "userId": row.id,
                "name": row.real_name or row.username,
                "avatar": row.avatar or "",
                "storeName": row.store_name or "未分配门店",
                "score": score,
                "rank": idx,
            }
        )
    return envelope(entries)


@router.get("/announcements", response_model=ApiResponse, summary="公告通知")
async def get_announcements():
    today = datetime.now(timezone.utc).date().isoformat()
    return envelope(
        [
            {
                "id": 1,
                "title": "今日必修课程已更新",
                "content": "请优先完成首页展示的必修课程，学习进度会自动计入排行榜。",
                "type": "task",
                "publishedAt": today,
                "read": False,
            },
            {
                "id": 2,
                "title": "学习排行榜按周期统计",
                "content": "支持查看日榜、周榜和月榜，分数由学习时长和课程完成情况组成。",
                "type": "ranking",
                "publishedAt": today,
                "read": False,
            },
        ]
    )


@router.get("/progress", response_model=ApiResponse, summary="学习进度列表")
async def list_progress(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
):
    """List learning progress for the current user."""
    query = select(LearningProgress).where(LearningProgress.user_id == user.id)

    if status:
        query = query.where(LearningProgress.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(LearningProgress.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    records = result.scalars().all()

    # Enrich with video titles
    items = []
    for r in records:
        video = await session.get(Video, r.video_id)
        pr = ProgressResponse.model_validate(r)
        pr.video_title = video.title if video else None
        items.append(pr)

    return envelope(
        {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "items": [item.model_dump() for item in items],
        }
    )


@router.get("/progress/{video_id}", response_model=ApiResponse, summary="获取单个视频进度")
async def get_video_progress(
    video_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Get learning progress for a specific video."""
    stmt = select(LearningProgress).where(
        LearningProgress.user_id == user.id,
        LearningProgress.video_id == video_id,
    )
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        return envelope(None)

    video = await session.get(Video, video_id)
    pr = ProgressResponse.model_validate(record)
    pr.video_title = video.title if video else None
    return envelope(pr.model_dump())


@router.post("/progress", response_model=ApiResponse, summary="更新学习进度")
async def update_progress(
    body: ProgressUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Create or update learning progress for a video."""
    # Verify video exists
    video_id = body.video_id
    if video_id is None:
        raise HTTPException(status_code=400, detail="缺少视频ID")

    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # Find existing record
    stmt = select(LearningProgress).where(
        LearningProgress.user_id == user.id,
        LearningProgress.video_id == video_id,
    )
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    progress_percent = body.progress_percent if body.progress_percent is not None else 0.0
    watch_duration = body.watch_duration if body.watch_duration is not None else 0
    last_position = body.last_position if body.last_position is not None else watch_duration
    status_value = body.status or ("completed" if body.completed or progress_percent >= 90 else "in_progress")

    if record:
        # Update
        record.progress_percent = progress_percent
        record.watch_duration = watch_duration
        record.last_position = last_position
        record.status = status_value
        if status_value == "completed" and record.completed_at is None:
            record.completed_at = now
    else:
        # Create
        record = LearningProgress(
            user_id=user.id,
            video_id=video_id,
            progress_percent=progress_percent,
            watch_duration=watch_duration,
            last_position=last_position,
            status=status_value,
            completed_at=now if status_value == "completed" else None,
        )
        session.add(record)

    await session.flush()

    pr = ProgressResponse.model_validate(record)
    pr.video_title = video.title
    return envelope(pr.model_dump())


@router.get("/calendar", response_model=ApiResponse, summary="学习日历热力图数据")
async def get_learning_calendar(
    session: SessionDep,
    user: CurrentUserDep,
    days: int = 84,
):
    """Return daily learning statistics for the last N days for calendar heatmap."""
    # Clamp days to a reasonable range
    days = max(7, min(days, 365))

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Aggregate daily watch duration and completed video count
    rows = (
        await session.execute(
            select(
                func.date(LearningProgress.updated_at).label("date"),
                func.coalesce(func.sum(LearningProgress.watch_duration), 0).label("duration"),
                func.coalesce(
                    func.sum(
                        case((LearningProgress.status == "completed", LearningProgress.watch_duration), else_=0)
                    ),
                    0,
                ).label("watch_seconds"),
            )
            .where(
                LearningProgress.user_id == user.id,
                LearningProgress.updated_at >= start_date,
            )
            .group_by(func.date(LearningProgress.updated_at))
            .order_by("date")
        )
    ).all()

    # Build a dict keyed by date string
    daily_map: dict[str, dict] = {}
    for row in rows:
        date_str = str(row.date)
        daily_map[date_str] = {
            "date": date_str,
            "duration": int(row.duration or 0),
            "completed": int(row.duration or 0) > 0 and True or False,
        }

    # Count completed per day — a video is "completed" when its progress was updated and status became completed
    completed_rows = (
        await session.execute(
            select(
                func.date(LearningProgress.completed_at).label("date"),
                func.count(LearningProgress.id).label("count"),
            )
            .where(
                LearningProgress.user_id == user.id,
                LearningProgress.status == "completed",
                LearningProgress.completed_at >= start_date,
            )
            .group_by(func.date(LearningProgress.completed_at))
            .order_by("date")
        )
    ).all()

    for row in completed_rows:
        date_str = str(row.date)
        if date_str in daily_map:
            daily_map[date_str]["completed"] = row.count
        else:
            daily_map[date_str] = {
                "date": date_str,
                "duration": 0,
                "completed": row.count,
            }

    # Fill missing dates within range
    result: list[dict] = []
    cursor = start_date
    while cursor <= end_date:
        date_str = cursor.strftime("%Y-%m-%d")
        if date_str in daily_map:
            result.append(daily_map[date_str])
        else:
            result.append({"date": date_str, "duration": 0, "completed": 0})
        cursor += timedelta(days=1)

    return envelope(result)



# ── Script endpoints for training-web ─────────────────────────────────────


@router.get("/scripts", response_model=ApiResponse, summary="培训端话术列表")
async def list_training_scripts(
    session: SessionDep,
    user: CurrentUserDep,
    category: str | None = None,
    favorites: bool = False,
    page: int = 1,
    page_size: int = 50,
):
    """Return sales scripts grouped by category for the training-web course module."""
    from app.models.script import Script
    from app.models.favorite import Favorite

    favorite_script_ids: list[int] = []
    if favorites:
        favorite_script_ids = (
            await session.execute(
                select(Favorite.target_id).where(
                    Favorite.user_id == user.id,
                    Favorite.type == "script",
                )
            )
        ).scalars().all()
        if not favorite_script_ids:
            return envelope({"items": [], "total": 0, "categories": []})

    query = select(Script).where(Script.is_active == True)

    if favorites:
        query = query.where(Script.id.in_(favorite_script_ids))

    if category:
        query = query.where(Script.category == category)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Script.sort_order, Script.id).offset((page - 1) * page_size).limit(page_size)
    scripts = (await session.execute(query)).scalars().all()

    # Get user's favorite script IDs
    script_ids = [s.id for s in scripts]
    fav_ids: set[int] = set()
    if script_ids:
        favs = (
            await session.execute(
                select(Favorite.target_id).where(
                    Favorite.user_id == user.id,
                    Favorite.type == "script",
                    Favorite.target_id.in_(script_ids),
                )
            )
        ).scalars().all()
        fav_ids = set(favs)

    items = []
    for s in scripts:
        items.append({
            "id": s.id,
            "title": s.title,
            "category": s.category,
            "theory": s.theory or "",
            "content": s.content,
            "scene": (s.tags or []) if isinstance(s.tags, list) else [],
            "tags": s.tags or [],
            "isFavorite": s.id in fav_ids,
            "sortOrder": s.sort_order,
            "createdAt": s.created_at.isoformat() if s.created_at else "",
        })

    # Build category summary
    cat_result = await session.execute(
        select(Script.category, func.count(Script.id))
        .where(Script.is_active == True)
        .where(Script.id.in_(favorite_script_ids) if favorites else True)
        .group_by(Script.category)
        .order_by(Script.category)
    )
    # Master-theory categories from prototype
    cat_labels = {
        "drucker": "德鲁克 · 管理之父",
        "girard": "乔·吉拉德 · 销售冠军",
        "hopkins": "霍普金斯 · 销售教父",
        "gitomer": "吉特默 · 销售圣经",
        "trout": "特劳特 · 定位理论",
        "burnett": "李奥·贝纳 · 品牌大师",
        "masters": "大师通识",
        # Concern-based categories
        "price": "价格敏感",
        "delay": "拖延犹豫",
        "awareness": "认知不足",
        "brand": "品牌偏好",
        "info_bias": "信息偏差",
        "trust": "信任/效果疑虑",
        "competitor": "竞品对比",
        "execution": "执行难度",
        "safety": "安全担忧",
        "knowledge": "常识科普",
        "online": "网络热议",
        "fang_kong": "防控镜片异议",
        "jiao_su": "角塑异议",
        # Legacy fallbacks
        "opening": "开场白",
        "product": "产品介绍",
        "objection": "异议处理",
        "closing": "促单成交",
        "service": "售后服务",
        "general": "通用话术",
        "prototype_card": "大师通识",
        "prototype_script": "通用话术",
    }
    categories = [
        {"code": row[0], "name": cat_labels.get(row[0], row[0]), "count": row[1]}
        for row in cat_result.all() if row[0]
    ]

    return envelope({"items": items, "total": total, "categories": categories})


@router.get("/scripts/{script_id:int}", response_model=ApiResponse, summary="培训端话术详情")
async def get_training_script(
    script_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Return a single script with theory, scene, and favourite status for training-web."""
    from app.models.script import Script
    from app.models.favorite import Favorite

    script = await session.get(Script, script_id)
    if not script or not script.is_active:
        raise HTTPException(status_code=404, detail="话术不存在")

    fav = (
        await session.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.type == "script",
                Favorite.target_id == script_id,
            )
        )
    ).scalar_one_or_none()

    return envelope({
        "id": script.id,
        "title": script.title,
        "category": script.category,
        "theory": script.theory or "",
        "content": script.content,
        "scene": (script.tags or []) if isinstance(script.tags, list) else [],
        "tags": script.tags or [],
        "isFavorite": fav is not None,
        "sortOrder": script.sort_order,
        "createdAt": script.created_at.isoformat() if script.created_at else "",
    })
