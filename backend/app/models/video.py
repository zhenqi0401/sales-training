"""Video model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.learning_progress import LearningProgress
    from app.models.favorite import Favorite
    from app.models.question import Question


class Video(Base, TimestampMixin):
    """Training video."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="视频标题"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, default="", comment="视频描述"
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, comment="分类ID"
    )
    file_url: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="视频文件URL/路径"
    )
    cover_url: Mapped[Optional[str]] = mapped_column(
        String(512), default="", comment="封面图URL"
    )
    duration: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, comment="视频时长（秒）"
    )
    resolution: Mapped[Optional[str]] = mapped_column(
        String(32), default="", comment="分辨率 e.g. 1920x1080"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, comment="文件大小（字节）"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="draft", comment="状态: draft, published, archived"
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序序号")
    is_required: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为必修视频"
    )
    est_duration: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, comment="预计学习时长（分钟）"
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布时间"
    )

    # relationships
    category: Mapped[Optional["Category"]] = relationship(back_populates="videos")
    learning_progresses: Mapped[list["LearningProgress"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        "Favorite",
        primaryjoin="and_(Video.id == foreign(Favorite.target_id), Favorite.type == 'video')",
        back_populates="video",
        cascade="all, delete-orphan",
        viewonly=True,
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, title={self.title!r})>"
