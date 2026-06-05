"""ExamRecord model — records a user's exam attempt."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.exam_paper import ExamPaper
    from app.models.exam_answer import ExamAnswer


class ExamRecord(Base, TimestampMixin):
    """Exam attempt record."""

    __tablename__ = "exam_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, comment="用户ID"
    )
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("exam_papers.id"), nullable=False, comment="试卷ID"
    )
    score: Mapped[int] = mapped_column(
        Integer, default=0, comment="得分"
    )
    passed: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否及格"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="开始时间"
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="提交时间"
    )

    # relationships
    user: Mapped["User"] = relationship(back_populates="exam_records")
    paper: Mapped["ExamPaper"] = relationship(back_populates="exam_records")
    answers: Mapped[list["ExamAnswer"]] = relationship(
        back_populates="exam_record", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ExamRecord(id={self.id}, user_id={self.user_id}, paper_id={self.paper_id}, score={self.score})>"
