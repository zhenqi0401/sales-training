"""Question model."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.video import Video
    from app.models.exam_answer import ExamAnswer


class Question(Base, TimestampMixin):
    """Quiz / exam question."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="题目内容"
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="single", comment="题型: single, multiple, true_false, fill, short_answer"
    )
    options: Mapped[Optional[dict]] = mapped_column(
        JSON, default=None, comment="选项 JSON (single/multiple: {A: text, B: text...})"
    )
    answer: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="标准答案"
    )
    analysis: Mapped[Optional[str]] = mapped_column(
        Text, default="", comment="答案解析"
    )
    difficulty: Mapped[int] = mapped_column(
        Integer, default=1, comment="难度: 1-5"
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, comment="分类ID"
    )
    video_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("videos.id"), nullable=True, comment="关联视频ID"
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(64), default="", comment="题目来源: manual, ai, import"
    )
    tags: Mapped[Optional[list]] = mapped_column(
        JSON, default=None, comment="标签列表"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")

    # relationships
    category: Mapped[Optional["Category"]] = relationship(back_populates="questions")
    video: Mapped[Optional["Video"]] = relationship(back_populates="questions")
    exam_answers: Mapped[list["ExamAnswer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, type={self.type!r})>"
