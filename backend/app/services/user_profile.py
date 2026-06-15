"""User profile service — builds a structured profile of the learner for agent context.

The profile aggregates data from multiple sources (users, learning_progress,
exam_records, favorites, scripts, practice_sessions) into a JSON-serialisable
dict that is injected into the agent system prompt as "用户画像".
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.models.category import Category
from app.models.exam_record import ExamRecord
from app.models.favorite import Favorite
from app.models.learning_progress import LearningProgress
from app.models.practice_session import LongTermMemory, PracticeSession
from app.models.script import Script
from app.models.user import User
from app.models.video import Video


async def build_user_profile(user_id: int, session: Any) -> dict[str, Any]:
    """Build a comprehensive user profile dict for agent context injection.

    Args:
        user_id: The learner's user ID.
        session: An async SQLAlchemy session.

    Returns:
        A dict with keys: basic_info, learning_stats, exam_stats,
        favorite_scripts, practice_history, long_term_memories.
    """
    # ── Basic info ──────────────────────────────────────────────────
    user = await session.get(User, user_id)
    basic_info: dict[str, Any] = {
        "user_id": user_id,
        "role": "unknown",
        "real_name": "",
        "store_name": "",
    }
    if user:
        basic_info["role"] = user.role
        basic_info["real_name"] = user.real_name or user.username
        if user.store:
            basic_info["store_name"] = user.store.name

    # ── Learning stats ──────────────────────────────────────────────
    total_videos_result = await session.execute(
        select(func.count()).select_from(Video).where(Video.status == "published")
    )
    total_videos = total_videos_result.scalar() or 0

    completed_result = await session.execute(
        select(func.count())
        .select_from(LearningProgress)
        .where(
            LearningProgress.user_id == user_id,
            LearningProgress.status == "completed",
        )
    )
    completed_videos = completed_result.scalar() or 0

    in_progress_result = await session.execute(
        select(func.count())
        .select_from(LearningProgress)
        .where(
            LearningProgress.user_id == user_id,
            LearningProgress.status == "in_progress",
            LearningProgress.progress_percent > 0,
        )
    )
    in_progress_videos = in_progress_result.scalar() or 0

    total_duration_result = await session.execute(
        select(func.coalesce(func.sum(LearningProgress.watch_duration), 0))
        .where(LearningProgress.user_id == user_id)
    )
    total_watch_seconds = total_duration_result.scalar() or 0

    learning_stats = {
        "total_videos": total_videos,
        "completed_videos": completed_videos,
        "in_progress_videos": in_progress_videos,
        "completion_rate": f"{round(completed_videos / max(total_videos, 1) * 100)}%",
        "total_watch_minutes": round(total_watch_seconds / 60),
    }

    # ── Exam stats ──────────────────────────────────────────────────
    exam_count_result = await session.execute(
        select(func.count())
        .select_from(ExamRecord)
        .where(ExamRecord.user_id == user_id)
    )
    exam_count = exam_count_result.scalar() or 0

    passed_result = await session.execute(
        select(func.count())
        .select_from(ExamRecord)
        .where(
            ExamRecord.user_id == user_id,
            ExamRecord.passed == True,
        )
    )
    passed_count = passed_result.scalar() or 0

    avg_score_result = await session.execute(
        select(func.coalesce(func.avg(ExamRecord.score), 0))
        .where(ExamRecord.user_id == user_id)
    )
    avg_score = round(float(avg_score_result.scalar() or 0), 1)

    exam_stats = {
        "total_exams": exam_count,
        "passed_exams": passed_count,
        "pass_rate": f"{round(passed_count / max(exam_count, 1) * 100)}%",
        "average_score": avg_score,
    }

    # ── Favorite scripts ────────────────────────────────────────────
    fav_result = await session.execute(
        select(Script.title, Script.category)
        .join(Favorite, Favorite.target_id == Script.id)
        .where(Favorite.type == "script")
        .where(Favorite.user_id == user_id, Script.is_active == True)
        .limit(10)
    )
    favorite_scripts = [
        {"title": row.title, "category": row.category}
        for row in fav_result.all()
    ]

    # ── Practice history ────────────────────────────────────────────
    practice_result = await session.execute(
        select(
            PracticeSession.module_code,
            func.count(PracticeSession.id).label("cnt"),
            func.coalesce(func.avg(PracticeSession.average_score), 0).label("avg"),
        )
        .where(
            PracticeSession.user_id == user_id,
            PracticeSession.status.in_(["active", "completed"]),
        )
        .group_by(PracticeSession.module_code)
    )
    practice_by_module = {}
    for row in practice_result.all():
        practice_by_module[row.module_code] = {
            "count": row.cnt,
            "avg_score": round(float(row.avg), 1),
        }

    total_sessions_result = await session.execute(
        select(func.count())
        .select_from(PracticeSession)
        .where(PracticeSession.user_id == user_id)
    )
    total_sessions = total_sessions_result.scalar() or 0

    practice_history = {
        "total_sessions": total_sessions,
        "by_module": practice_by_module,
    }

    # ── Long-term memories ──────────────────────────────────────────
    ltm_result = await session.execute(
        select(LongTermMemory)
        .where(LongTermMemory.user_id == user_id)
        .order_by(LongTermMemory.importance.desc(), LongTermMemory.recall_count.desc())
        .limit(10)
    )
    long_term_memories = [
        {
            "key": m.memory_key,
            "value": m.memory_value,
            "type": m.memory_type,
            "importance": m.importance,
        }
        for m in ltm_result.scalars().all()
    ]

    return {
        "basic_info": basic_info,
        "learning_stats": learning_stats,
        "exam_stats": exam_stats,
        "favorite_scripts": favorite_scripts,
        "practice_history": practice_history,
        "long_term_memories": long_term_memories,
    }


def profile_to_system_prompt(profile: dict[str, Any]) -> str:
    """Convert a user profile dict into a compact system prompt section.

    The returned string is intended to be appended to the agent system prompt.
    """
    basic = profile.get("basic_info", {})
    learning = profile.get("learning_stats", {})
    exam = profile.get("exam_stats", {})
    favs = profile.get("favorite_scripts", [])
    practice = profile.get("practice_history", {})
    memories = profile.get("long_term_memories", [])

    lines = [
        "## 当前学员画像",
        f"- 姓名：{basic.get('real_name', '未知')}",
        f"- 角色：{basic.get('role', '未知')}",
        f"- 门店：{basic.get('store_name', '未知')}",
        "",
        "### 学习进度",
        f"- 已完成 {learning.get('completed_videos', 0)}/{learning.get('total_videos', 0)} 个视频 ({learning.get('completion_rate', '0%')})",
        f"- 累计观看 {learning.get('total_watch_minutes', 0)} 分钟",
        "",
        "### 考试情况",
        f"- 共参加 {exam.get('total_exams', 0)} 次考试，通过 {exam.get('passed_exams', 0)} 次 ({exam.get('pass_rate', '0%')})",
        f"- 平均分 {exam.get('average_score', 0)}",
    ]

    if favs:
        lines.append("")
        lines.append("### 收藏话术")
        for f in favs:
            lines.append(f"- [{f['category']}] {f['title']}")

    by_module = practice.get("by_module", {})
    if by_module:
        lines.append("")
        lines.append("### 演练统计")
        for code, stats in sorted(by_module.items()):
            module_names = {
                "reception": "接待流程", "question": "问诊话术", "product": "产品介绍",
                "objection": "异议处理", "closing": "成交技巧", "fitting": "验光配镜",
                "aftercare": "售后服务", "general": "通用演练",
            }
            name = module_names.get(code, code)
            lines.append(f"- {name}：{stats['count']} 次，均分 {stats['avg_score']}")

    if memories:
        lines.append("")
        lines.append("### 长期记忆（过往演练洞察）")
        for m in memories:
            prefix = {"weakness": "⚠️ 薄弱点", "strength": "✅ 优势", "insight": "💡 洞察", "preference": "👍 偏好", "pattern": "🔄 模式"}.get(m["type"], "📌")
            lines.append(f"- {prefix}：{m['value']}")

    return "\n".join(lines)
