"""Learning progress endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.learning_progress import LearningProgress
from app.models.video import Video
from app.schemas.common import PaginatedResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProgressUpdate(BaseModel):
    """Update learning progress payload."""
    video_id: int
    progress_percent: float = 0.0
    watch_duration: int = 0
    last_position: int = 0
    status: str = "in_progress"


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


@router.get("/progress", response_model=PaginatedResponse[ProgressResponse], summary="学习进度列表")
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

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=items,
    )


@router.get("/progress/{video_id}", response_model=ProgressResponse | None, summary="获取单个视频进度")
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
        return None

    video = await session.get(Video, video_id)
    pr = ProgressResponse.model_validate(record)
    pr.video_title = video.title if video else None
    return pr


@router.post("/progress", response_model=ProgressResponse, summary="更新学习进度")
async def update_progress(
    body: ProgressUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Create or update learning progress for a video."""
    # Verify video exists
    video = await session.get(Video, body.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # Find existing record
    stmt = select(LearningProgress).where(
        LearningProgress.user_id == user.id,
        LearningProgress.video_id == body.video_id,
    )
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if record:
        # Update
        record.progress_percent = body.progress_percent
        record.watch_duration = body.watch_duration
        record.last_position = body.last_position
        record.status = body.status
        if body.status == "completed" and record.completed_at is None:
            record.completed_at = now
    else:
        # Create
        record = LearningProgress(
            user_id=user.id,
            video_id=body.video_id,
            progress_percent=body.progress_percent,
            watch_duration=body.watch_duration,
            last_position=body.last_position,
            status=body.status,
            completed_at=now if body.status == "completed" else None,
        )
        session.add(record)

    await session.flush()

    pr = ProgressResponse.model_validate(record)
    pr.video_title = video.title
    return pr
