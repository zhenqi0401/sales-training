"""ExamPaper model."""

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExamPaper(Base, TimestampMixin):
    """Exam paper template."""

    __tablename__ = "exam_papers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="试卷标题"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, default="", comment="试卷描述"
    )
    duration: Mapped[int] = mapped_column(
        Integer, default=60, comment="考试时长（分钟）"
    )
    pass_score: Mapped[int] = mapped_column(
        Integer, default=60, comment="及格分数"
    )
    total_score: Mapped[int] = mapped_column(
        Integer, default=100, comment="总分"
    )
    question_ids: Mapped[Optional[list]] = mapped_column(
        JSON, default=None, comment="题目ID列表 [1, 2, 3...]"
    )
    difficulty_level: Mapped[int] = mapped_column(
        Integer, default=1, comment="难度等级 1-5"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")

    # relationships
    exam_records: Mapped[list["ExamRecord"]] = relationship(  # noqa: F821
        back_populates="paper", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ExamPaper(id={self.id}, title={self.title!r})>"
