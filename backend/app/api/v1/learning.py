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
from app.services import oss_storage


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
        "url": oss_storage.to_playable_url(video.file_url or ""),
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


async def _get_descendant_ids(session: SessionDep, category_id: int) -> list[int]:
    """递归获取某分类及其所有子分类的 ID 列表。"""
    ids = [category_id]
    children = (
        await session.execute(
            select(Category.id).where(Category.parent_id == category_id, Category.is_active == True)
        )
    ).scalars().all()
    for child_id in children:
        ids.extend(await _get_descendant_ids(session, child_id))
    return ids


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
        cat_ids = await _get_descendant_ids(session, category.id)
        video_ids = (
            await session.execute(
                select(Video.id).where(Video.category_id.in_(cat_ids), Video.status == "published")
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
    # Load the category itself
    category = await session.get(Category, category_id)
    if not category or not category.is_active:
        raise HTTPException(status_code=404, detail="分类不存在")

    # Load direct children
    children = (
        await session.execute(
            select(Category)
            .where(Category.parent_id == category_id, Category.is_active == True)
            .order_by(Category.sort_order, Category.id)
        )
    ).scalars().all()

    children_data: list[dict] = []
    videos: list[Video] = []

    if children:
        # Folder mode: return children with video counts
        for child in children:
            child_ids = await _get_descendant_ids(session, child.id)
            video_count = (
                await session.execute(
                    select(func.count()).select_from(Video).where(
                        Video.category_id.in_(child_ids), Video.status == "published"
                    )
                )
            ).scalar() or 0
            children_data.append({
                "id": child.id,
                "name": child.name,
                "code": child.code or "",
                "icon": child.icon or "",
                "description": child.description or "",
                "videoCount": video_count,
                "sort": child.sort_order,
            })
    else:
        # Leaf mode: return videos
        cat_ids = await _get_descendant_ids(session, category_id)
        videos = (
            await session.execute(
                select(Video)
                .where(Video.category_id.in_(cat_ids), Video.status == "published")
                .order_by(Video.sort_order, Video.id.desc())
            )
        ).scalars().all()

    progress_map = await user_video_progress_map(session, user.id, [v.id for v in videos])
    return envelope({
        "category": {
            "id": category.id,
            "name": category.name,
            "code": category.code or "",
            "icon": category.icon or "",
            "description": category.description or "",
        },
        "children": children_data,
        "videos": [video_payload(v, progress_map.get(v.id)) for v in videos],
    })


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


# ── Video practice questions endpoints ────────────────────────────────────


class VideoAnswerCheck(BaseModel):
    question_id: int = Field(alias="questionId")
    selected: str | list[str]

    model_config = {"populate_by_name": True}


class VideoCheckRequest(BaseModel):
    answers: list[VideoAnswerCheck]


@router.get("/videos/{video_id:int}/questions", response_model=ApiResponse, summary="获取视频配套练习题")
async def get_video_questions(
    video_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Get all active practice questions bound to a video (answers hidden)."""
    from app.models.question import Question

    result = await session.execute(
        select(Question).where(
            Question.video_id == video_id,
            Question.is_active == True,
        ).order_by(Question.id)
    )
    questions = result.scalars().all()

    items = []
    for q in questions:
        items.append({
            "id": q.id,
            "content": q.content,
            "type": q.type,
            "options": q.options,
            "analysis": "",  # hidden until check
            "videoId": q.video_id,
            "categoryId": q.category_id,
        })

    # Get video title
    video = await session.get(Video, video_id)
    return envelope({
        "videoTitle": video.title if video else "",
        "questions": items,
    })


@router.post("/videos/{video_id:int}/check", response_model=ApiResponse, summary="提交视频练习题答案")
async def check_video_answers(
    video_id: int,
    body: VideoCheckRequest,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Submit answers and get correct/wrong feedback with analysis."""
    from app.models.question import Question

    question_ids = [a.question_id for a in body.answers]
    if not question_ids:
        raise HTTPException(status_code=400, detail="缺少答案")

    result = await session.execute(
        select(Question).where(Question.id.in_(question_ids))
    )
    question_map: dict[int, Question] = {q.id: q for q in result.scalars().all()}

    # Validate all questions belong to this video
    for q in question_map.values():
        if q.video_id != video_id:
            raise HTTPException(status_code=400, detail=f"题目 {q.id} 不属于该视频")

    results = []
    correct_count = 0
    for ans in body.answers:
        q = question_map.get(ans.question_id)
        if not q:
            continue

        correct_answer = q.answer.strip()
        if isinstance(ans.selected, list):
            user_answer = ",".join(sorted(ans.selected))
        else:
            user_answer = str(ans.selected).strip()

        is_correct = user_answer == correct_answer
        if is_correct:
            correct_count += 1

        results.append({
            "questionId": q.id,
            "correct": is_correct,
            "correctAnswer": correct_answer,
            "analysis": q.analysis or "",
        })

    return envelope({
        "total": len(results),
        "correct": correct_count,
        "results": results,
    })
