"""Dashboard / statistics endpoints."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import func, select

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.category import Category
from app.models.exam_answer import ExamAnswer
from app.models.exam_paper import ExamPaper
from app.models.exam_record import ExamRecord
from app.models.learning_progress import LearningProgress
from app.models.question import Question
from app.models.store import Store
from app.models.user import User
from app.models.video import Video
from app.schemas.exam import StudyStatsResponse

router = APIRouter()


def percent(numerator: float, denominator: float) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def minutes(seconds: int | float | None) -> int:
    return round((seconds or 0) / 60)


def is_after(dt: datetime | None, start: datetime) -> bool:
    if not dt:
        return False
    left = dt
    right = start
    if left.tzinfo is not None:
        left = left.astimezone(timezone.utc).replace(tzinfo=None)
    if right.tzinfo is not None:
        right = right.astimezone(timezone.utc).replace(tzinfo=None)
    return left >= right


def level_from_paper(paper: ExamPaper | None) -> str:
    if not paper:
        return "L1"
    title = paper.title or ""
    if "L1" in title or "初级" in title:
        return "L1"
    if "L2" in title or "中级" in title:
        return "L2"
    if "L3" in title or "高级" in title:
        return "L3"
    difficulty = paper.difficulty_level or 1
    if difficulty <= 2:
        return "L1"
    if difficulty <= 4:
        return "L2"
    return "L3"


async def published_videos(session: SessionDep) -> list[Video]:
    return (
        await session.execute(
            select(Video).where(Video.status == "published").order_by(Video.sort_order, Video.id)
        )
    ).scalars().all()


async def active_students(session: SessionDep) -> list[User]:
    return (
        await session.execute(
            select(User).where(User.is_active == True, User.role == "student").order_by(User.id)
        )
    ).scalars().all()


async def student_progress_rows(session: SessionDep) -> list[tuple[LearningProgress, User, Video]]:
    return (
        await session.execute(
            select(LearningProgress, User, Video)
            .join(User, User.id == LearningProgress.user_id)
            .join(Video, Video.id == LearningProgress.video_id)
            .where(User.is_active == True, User.role == "student", Video.status == "published")
        )
    ).all()


async def exam_rows(session: SessionDep) -> list[tuple[ExamRecord, User, ExamPaper]]:
    return (
        await session.execute(
            select(ExamRecord, User, ExamPaper)
            .join(User, User.id == ExamRecord.user_id)
            .join(ExamPaper, ExamPaper.id == ExamRecord.paper_id)
            .where(User.is_active == True, User.role == "student")
            .order_by(ExamRecord.submitted_at)
        )
    ).all()


async def wrong_answer_rows(session: SessionDep) -> list[tuple[ExamAnswer, Question]]:
    return (
        await session.execute(
            select(ExamAnswer, Question)
            .join(ExamRecord, ExamRecord.id == ExamAnswer.exam_record_id)
            .join(User, User.id == ExamRecord.user_id)
            .join(Question, Question.id == ExamAnswer.question_id)
            .where(User.is_active == True, User.role == "student", ExamAnswer.is_correct == False)
        )
    ).all()


async def category_name_map(session: SessionDep) -> dict[int, str]:
    categories = (await session.execute(select(Category))).scalars().all()
    return {category.id: category.name for category in categories}


async def store_name_map(session: SessionDep) -> dict[int, str]:
    stores = (await session.execute(select(Store).where(Store.is_active == True))).scalars().all()
    return {store.id: store.name for store in stores}


async def build_dashboard_payload(session: SessionDep) -> dict[str, Any]:
    students = await active_students(session)
    videos = await published_videos(session)
    progress_rows = await student_progress_rows(session)
    records = await exam_rows(session)
    wrong_rows = await wrong_answer_rows(session)
    category_names = await category_name_map(session)
    store_names = await store_name_map(session)

    student_count = len(students)
    video_count = len(videos)
    expected_progress_count = student_count * video_count

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_user_ids = {
        user.id
        for user in students
        if is_after(user.last_login, today_start)
    }
    active_user_ids.update(progress.user_id for progress, _user, _video in progress_rows if is_after(progress.updated_at, today_start))
    active_user_ids.update(record.user_id for record, _user, _paper in records if is_after(record.submitted_at, today_start))

    progress_by_student: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"watchSeconds": 0, "completed": 0, "started": 0, "progressTotal": 0.0}
    )
    progress_by_video: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"watchSeconds": 0, "watchers": set(), "completed": 0, "progressTotal": 0.0}
    )

    for progress, _user, _video in progress_rows:
        completed = progress.status == "completed" or (progress.progress_percent or 0) >= 100
        progress_by_student[progress.user_id]["watchSeconds"] += progress.watch_duration or 0
        progress_by_student[progress.user_id]["progressTotal"] += min(progress.progress_percent or 0, 100)
        progress_by_student[progress.user_id]["started"] += 1
        if completed:
            progress_by_student[progress.user_id]["completed"] += 1

        progress_by_video[progress.video_id]["watchSeconds"] += progress.watch_duration or 0
        progress_by_video[progress.video_id]["watchers"].add(progress.user_id)
        progress_by_video[progress.video_id]["progressTotal"] += min(progress.progress_percent or 0, 100)
        if completed:
            progress_by_video[progress.video_id]["completed"] += 1

    completed_total = sum(data["completed"] for data in progress_by_student.values())
    watch_seconds_total = sum(data["watchSeconds"] for data in progress_by_student.values())
    avg_learning_minutes = minutes(watch_seconds_total / student_count) if student_count else 0

    exam_by_level = {
        "L1": {"count": 0, "passed": 0, "scoreTotal": 0},
        "L2": {"count": 0, "passed": 0, "scoreTotal": 0},
        "L3": {"count": 0, "passed": 0, "scoreTotal": 0},
    }
    exam_by_paper: dict[int, dict[str, Any]] = {}
    exam_by_student: dict[int, dict[str, Any]] = defaultdict(lambda: {"count": 0, "passed": 0, "scoreTotal": 0, "bestScore": 0})
    trend_by_date: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "passed": 0, "scoreTotal": 0})

    for record, _user, paper in records:
        level = level_from_paper(paper)
        if level in exam_by_level:
            exam_by_level[level]["count"] += 1
            exam_by_level[level]["scoreTotal"] += record.score or 0
            if record.passed:
                exam_by_level[level]["passed"] += 1

        paper_stats = exam_by_paper.setdefault(
            paper.id,
            {
                "paperId": paper.id,
                "paperTitle": paper.title,
                "level": level,
                "count": 0,
                "passed": 0,
                "scoreTotal": 0,
            },
        )
        paper_stats["count"] += 1
        paper_stats["scoreTotal"] += record.score or 0
        if record.passed:
            paper_stats["passed"] += 1

        student_stats = exam_by_student[record.user_id]
        student_stats["count"] += 1
        student_stats["scoreTotal"] += record.score or 0
        student_stats["bestScore"] = max(student_stats["bestScore"], record.score or 0)
        if record.passed:
            student_stats["passed"] += 1

        if record.submitted_at:
            date_key = record.submitted_at.date().isoformat()
            trend_by_date[date_key]["count"] += 1
            trend_by_date[date_key]["scoreTotal"] += record.score or 0
            if record.passed:
                trend_by_date[date_key]["passed"] += 1

    wrong_counter: Counter[int] = Counter()
    weak_counter: Counter[str] = Counter()
    question_map: dict[int, Question] = {}
    for _answer, question in wrong_rows:
        wrong_counter[question.id] += 1
        question_map[question.id] = question
        category = category_names.get(question.category_id or 0) or (question.tags or ["未分类"])[0]
        weak_counter[str(category)] += 1

    student_items = []
    for user in students:
        learn = progress_by_student[user.id]
        exam = exam_by_student[user.id]
        completed = learn["completed"]
        progress_rate = percent(completed, video_count)
        average_progress = percent(learn["progressTotal"], video_count * 100) if video_count else 0
        student_items.append(
            {
                "userId": user.id,
                "name": user.real_name or user.username,
                "phone": user.phone,
                "storeId": user.store_id,
                "storeName": store_names.get(user.store_id or 0, "未分配门店"),
                "watchMinutes": minutes(learn["watchSeconds"]),
                "completedVideos": completed,
                "totalVideos": video_count,
                "completionRate": progress_rate,
                "averageProgress": average_progress,
                "examCount": exam["count"],
                "examPassed": exam["passed"],
                "examPassRate": percent(exam["passed"], exam["count"]),
                "averageScore": round(exam["scoreTotal"] / exam["count"], 1) if exam["count"] else 0,
                "bestScore": exam["bestScore"],
            }
        )

    video_stats = []
    for video in videos:
        data = progress_by_video[video.id]
        watchers = len(data["watchers"])
        video_stats.append(
            {
                "videoId": video.id,
                "title": video.title,
                "categoryName": category_names.get(video.category_id or 0, "未分类"),
                "durationMinutes": minutes(video.duration),
                "watchers": watchers,
                "completionRate": percent(data["completed"], watchers),
                "averageWatchMinutes": minutes(data["watchSeconds"] / watchers) if watchers else 0,
                "totalWatchMinutes": minutes(data["watchSeconds"]),
                "rankScore": minutes(data["watchSeconds"]) + data["completed"] * 10,
            }
        )

    store_stats = []
    by_store: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for item in student_items:
        by_store[item["storeId"]].append(item)
    for store_id, items in by_store.items():
        exam_count = sum(item["examCount"] for item in items)
        exam_passed = sum(item["examPassed"] for item in items)
        store_stats.append(
            {
                "storeId": store_id,
                "storeName": store_names.get(store_id or 0, "未分配门店"),
                "studentCount": len(items),
                "completionRate": round(sum(item["completionRate"] for item in items) / len(items), 1) if items else 0,
                "averageWatchMinutes": round(sum(item["watchMinutes"] for item in items) / len(items)) if items else 0,
                "examPassRate": percent(exam_passed, exam_count),
                "averageScore": round(sum(item["averageScore"] for item in items) / len(items), 1) if items else 0,
            }
        )

    exam_level_stats = [
        {
            "level": level,
            "count": data["count"],
            "averageScore": round(data["scoreTotal"] / data["count"], 1) if data["count"] else 0,
            "passRate": percent(data["passed"], data["count"]),
        }
        for level, data in exam_by_level.items()
    ]

    paper_stats = [
        {
            **data,
            "averageScore": round(data["scoreTotal"] / data["count"], 1) if data["count"] else 0,
            "passRate": percent(data["passed"], data["count"]),
        }
        for data in exam_by_paper.values()
    ]

    trend = []
    for offset in range(29, -1, -1):
        day = (datetime.now(timezone.utc).date() - timedelta(days=offset)).isoformat()
        data = trend_by_date[day]
        trend.append(
            {
                "date": day,
                "count": data["count"],
                "averageScore": round(data["scoreTotal"] / data["count"], 1) if data["count"] else 0,
                "passRate": percent(data["passed"], data["count"]),
            }
        )

    high_frequency_wrong = [
        {
            "questionId": question_id,
            "content": question_map[question_id].content,
            "categoryName": category_names.get(question_map[question_id].category_id or 0, "未分类"),
            "wrongCount": count,
        }
        for question_id, count in wrong_counter.most_common(10)
    ]

    weak_knowledge = [{"name": name, "wrongCount": count} for name, count in weak_counter.most_common(10)]

    overview = {
        "totalUsers": student_count,
        "activeUsers": len(active_user_ids),
        "totalVideos": video_count,
        "totalQuestions": (await session.execute(select(func.count()).select_from(Question).where(Question.is_active == True))).scalar() or 0,
        "totalStores": len(store_names),
        "totalExams": len(records),
        "completionRate": percent(completed_total, expected_progress_count),
        "totalWatchMinutes": minutes(watch_seconds_total),
        "averageLearningMinutes": avg_learning_minutes,
        "examPassRate": percent(sum(1 for record, _u, _p in records if record.passed), len(records)),
        "averageScore": round(sum(record.score or 0 for record, _u, _p in records) / len(records), 1) if records else 0,
        "examPassRateByLevel": {item["level"]: item["passRate"] for item in exam_level_stats},
    }

    # Legacy snake_case fields are kept for older dashboard cards.
    return {
        "total_users": overview["totalUsers"],
        "active_users": overview["activeUsers"],
        "total_videos": overview["totalVideos"],
        "total_questions": overview["totalQuestions"],
        "total_stores": overview["totalStores"],
        "total_exams": overview["totalExams"],
        "exam_pass_rate": overview["examPassRate"],
        "completion_rate": overview["completionRate"],
        "average_score": overview["averageScore"],
        "overview": overview,
        "videoStats": {
            "items": sorted(video_stats, key=lambda item: item["totalWatchMinutes"], reverse=True),
            "ranking": sorted(video_stats, key=lambda item: item["rankScore"], reverse=True)[:10],
        },
        "studentStats": {
            "progressList": sorted(student_items, key=lambda item: item["watchMinutes"], reverse=True),
            "learningRanking": sorted(student_items, key=lambda item: item["watchMinutes"], reverse=True)[:10],
            "examRanking": sorted(student_items, key=lambda item: (item["bestScore"], item["averageScore"]), reverse=True)[:10],
        },
        "storeStats": sorted(store_stats, key=lambda item: item["completionRate"], reverse=True),
        "examStats": {
            "levels": exam_level_stats,
            "papers": sorted(paper_stats, key=lambda item: item["count"], reverse=True),
            "highFrequencyWrong": high_frequency_wrong,
            "weakKnowledge": weak_knowledge,
            "trend": trend,
        },
    }


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
    return await build_dashboard_payload(session)


@router.get("/student-progress-export", summary="导出学员学习进度")
async def export_student_progress(session: SessionDep, user: CurrentUserDep):
    payload = await build_dashboard_payload(session)
    rows = payload["studentStats"]["progressList"]

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "学员ID",
        "姓名",
        "手机号",
        "门店",
        "学习时长(分钟)",
        "已完成视频",
        "总视频",
        "完课率",
        "考试次数",
        "考试通过率",
        "平均分",
        "最高分",
    ])
    for row in rows:
        writer.writerow([
            row["userId"],
            row["name"],
            row["phone"],
            row["storeName"],
            row["watchMinutes"],
            row["completedVideos"],
            row["totalVideos"],
            f'{row["completionRate"]}%',
            row["examCount"],
            f'{row["examPassRate"]}%',
            row["averageScore"],
            row["bestScore"],
        ])

    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": 'attachment; filename="student-progress.csv"'},
    )
