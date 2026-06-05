"""Favorite model — user bookmarks for videos or other content."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video


class Favorite(Base, TimestampMixin):
    """User favourite / bookmark entry."""

    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, comment="用户ID"
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="收藏类型: video, product, script"
    )
    target_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="目标ID"
    )

    # relationships
    user: Mapped["User"] = relationship(back_populates="favorites")
    video: Mapped[Optional["Video"]] = relationship(
        "Video",
        primaryjoin="and_(Favorite.type == 'video', foreign(Favorite.target_id) == Video.id)",
        back_populates="favorites",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Favorite(id={self.id}, user_id={self.user_id}, type={self.type!r}, target_id={self.target_id})>"
