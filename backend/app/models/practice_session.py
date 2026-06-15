"""Practice session & message models for AI agent conversation practice."""

from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PracticeSession(Base, TimestampMixin):
    """A single AI conversation practice session."""

    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True, comment="学员ID"
    )
    module_code: Mapped[str] = mapped_column(
        String(64), nullable=False, default="general", comment="演练场景编码: reception/question/product/objection/closing/fitting/aftercare/general"
    )
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, default="话术演练", comment="会话标题"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", comment="状态: active/completed/abandoned"
    )
    total_turns: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="总对话轮数"
    )
    average_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="平均评分"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="会话总结"
    )

    def __repr__(self) -> str:
        return f"<PracticeSession(id={self.id}, user_id={self.user_id}, module={self.module_code!r}, status={self.status!r})>"


class PracticeMessage(Base, TimestampMixin):
    """A single message within a practice session (user, assistant, or tool)."""

    __tablename__ = "practice_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话ID",
    )
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="角色: user/assistant/tool"
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="消息文本内容"
    )
    tool_calls: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="工具调用记录 (MCP)"
    )
    tool_results: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="工具返回结果"
    )
    evaluation: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="AI 对用户回复的评估 {score, feedback, highlights, improvements}"
    )
    turn_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="对话轮次序号"
    )

    def __repr__(self) -> str:
        return f"<PracticeMessage(id={self.id}, session_id={self.session_id}, role={self.role!r}, turn={self.turn_number})>"


class LongTermMemory(Base, TimestampMixin):
    """Long-term memory for users — key insights and patterns from practice sessions."""

    __tablename__ = "long_term_memories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True, comment="学员ID"
    )
    memory_key: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="记忆唯一键 (用于去重合并)"
    )
    memory_value: Mapped[str] = mapped_column(
        Text, nullable=False, comment="记忆内容"
    )
    importance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, comment="重要性 1-10"
    )
    source_session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="SET NULL"),
        nullable=True,
        comment="来源会话ID",
    )
    memory_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="insight",
        comment="记忆类型: insight/weakness/strength/preference/pattern"
    )
    recall_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="被召回次数"
    )

    def __repr__(self) -> str:
        return f"<LongTermMemory(id={self.id}, user_id={self.user_id}, key={self.memory_key!r}, importance={self.importance})>"
