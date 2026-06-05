"""LearningProgress model — tracks user video watching progress."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video


class LearningProgress(Base, TimestampMixin):
    """Per-user per-video learning progress record."""

    __tablename__ = "learning_progresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, comment="用户ID"
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id"), nullable=False, comment="视频ID"
    )
    progress_percent: Mapped[float] = mapped_column(
        Float, default=0.0, comment="学习进度百分比 0-100"
    )
    watch_duration: Mapped[int] = mapped_column(
        Integer, default=0, comment="已观看时长（秒）"
    )
    last_position: Mapped[int] = mapped_column(
        Integer, default=0, comment="上次播放位置（秒）"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="not_started", comment="状态: not_started, in_progress, completed"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    # relationships
    user: Mapped["User"] = relationship(back_populates="learning_progresses")
    video: Mapped["Video"] = relationship(back_populates="learning_progresses")

    def __repr__(self) -> str:
        return f"<LearningProgress(user_id={self.user_id}, video_id={self.video_id}, progress={self.progress_percent})>"
