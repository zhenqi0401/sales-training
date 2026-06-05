"""ExamAnswer model — individual answer within an exam record."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.exam_record import ExamRecord
    from app.models.question import Question


class ExamAnswer(Base, TimestampMixin):
    """Answer to a single question within an exam attempt."""

    __tablename__ = "exam_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_record_id: Mapped[int] = mapped_column(
        ForeignKey("exam_records.id"), nullable=False, comment="考试记录ID"
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"), nullable=False, comment="题目ID"
    )
    user_answer: Mapped[str] = mapped_column(
        Text, nullable=False, comment="用户答案"
    )
    is_correct: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否正确"
    )

    # relationships
    exam_record: Mapped["ExamRecord"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="exam_answers")

    def __repr__(self) -> str:
        return f"<ExamAnswer(id={self.id}, question_id={self.question_id}, correct={self.is_correct})>"
