"""Dashboard / statistics endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select, func

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.learning_progress import LearningProgress
from app.models.exam_record import ExamRecord
from app.models.video import Video
from app.models.user import User
from app.models.store import Store
from app.models.question import Question
from app.schemas.exam import StudyStatsResponse

router = APIRouter()


@router.get("/stats", response_model=StudyStatsResponse, summary="学习统计概览")
async def get_study_stats(session: SessionDep, user: CurrentUserDep):
    total_videos = (
        await session.execute(select(func.count()).select_from(Video).where(Video.status == "published"))
    ).scalar() or 0

    completed_videos = (
        await session.execute(
            select(func.count()).select_from(LearningProgress).where(
                LearningProgress.user_id == user.id, LearningProgress.status == "completed"
            )
        )
    ).scalar() or 0

    in_progress_videos = (
        await session.execute(
            select(func.count()).select_from(LearningProgress).where(
                LearningProgress.user_id == user.id, LearningProgress.status == "in_progress"
            )
        )
    ).scalar() or 0

    total_exams = (
        await session.execute(select(func.count()).select_from(ExamRecord).where(ExamRecord.user_id == user.id))
    ).scalar() or 0

    passed_exams = (
        await session.execute(
            select(func.count()).select_from(ExamRecord).where(
                ExamRecord.user_id == user.id, ExamRecord.passed == True
            )
        )
    ).scalar() or 0

    avg_score = (
        await session.execute(select(func.avg(ExamRecord.score)).where(ExamRecord.user_id == user.id))
    ).scalar() or 0.0

    return StudyStatsResponse(
        total_videos=total_videos,
        completed_videos=completed_videos,
        in_progress_videos=in_progress_videos,
        total_exams=total_exams,
        passed_exams=passed_exams,
        average_score=round(float(avg_score), 1),
    )


@router.get("/admin-overview", summary="管理员数据概览")
async def get_admin_overview(session: SessionDep, user: CurrentUserDep):
    total_users = (
        await session.execute(select(func.count()).select_from(User).where(User.is_active == True))
    ).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_users = (
        await session.execute(
            select(func.count()).select_from(User).where(User.is_active == True, User.last_login >= today_start)
        )
    ).scalar() or 0

    total_videos = (
        await session.execute(select(func.count()).select_from(Video).where(Video.status == "published"))
    ).scalar() or 0

    total_questions = (
        await session.execute(select(func.count()).select_from(Question).where(Question.is_active == True))
    ).scalar() or 0

    total_stores = (
        await session.execute(select(func.count()).select_from(Store).where(Store.is_active == True))
    ).scalar() or 0

    total_submissions = (
        await session.execute(select(func.count()).select_from(ExamRecord))
    ).scalar() or 0

    passed_count = (
        await session.execute(select(func.count()).select_from(ExamRecord).where(ExamRecord.passed == True))
    ).scalar() or 0

    pass_rate = round(passed_count / total_submissions * 100, 1) if total_submissions > 0 else 0

    avg_score = (
        await session.execute(select(func.coalesce(func.avg(ExamRecord.score), 0)))
    ).scalar() or 0.0

    completed_ids_result = await session.execute(
        select(LearningProgress.video_id).where(LearningProgress.status == "completed")
    )
    unique_completed = len(set(completed_ids_result.scalars().all()))
    completion_rate = round(unique_completed / total_videos * 100, 1) if total_videos > 0 else 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_videos": total_videos,
        "total_questions": total_questions,
        "total_stores": total_stores,
        "total_exams": total_submissions,
        "exam_pass_rate": pass_rate,
        "completion_rate": completion_rate,
        "average_score": round(float(avg_score), 1),
    }
