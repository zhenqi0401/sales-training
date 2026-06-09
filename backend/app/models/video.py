"""Video model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.favorite import Favorite
    from app.models.learning_progress import LearningProgress
    from app.models.question import Question


class Video(Base, TimestampMixin):
    """Training video."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, comment="Video title")
    description: Mapped[Optional[str]] = mapped_column(Text, default="", comment="Video description")
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, comment="Category ID"
    )
    file_url: Mapped[str] = mapped_column(String(512), nullable=False, comment="Video file URL/path")
    cover_url: Mapped[Optional[str]] = mapped_column(String(512), default="", comment="Cover image URL")
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list, comment="Video tags")
    product_ids: Mapped[Optional[list[int]]] = mapped_column(JSON, default=list, comment="Related product IDs")
    duration: Mapped[Optional[int]] = mapped_column(Integer, default=0, comment="Duration in seconds")
    resolution: Mapped[Optional[str]] = mapped_column(String(32), default="", comment="Resolution, e.g. 1920x1080")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, default=0, comment="File size in bytes")
    status: Mapped[str] = mapped_column(String(32), default="draft", comment="draft, published, archived")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="Sort order")
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, comment="Mandatory training video")
    est_duration: Mapped[Optional[int]] = mapped_column(Integer, default=0, comment="Estimated study minutes")
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Published time"
    )

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
