"""Category model — hierarchical (parent_id) for product / video categories."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.video import Video
    from app.models.product import Product
    from app.models.question import Question


class Category(Base, TimestampMixin):
    """Category for products, videos, and questions."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="分类名称"
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="分类编码"
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(256), default="", comment="图标URL或class"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, default="", comment="分类描述"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="排序序号"
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, comment="上级分类ID"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")

    # self-referential relationship for hierarchy
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="children", remote_side="Category.id"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )
    videos: Mapped[list["Video"]] = relationship(back_populates="category")
    products: Mapped[list["Product"]] = relationship(back_populates="category")
    questions: Mapped[list["Question"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name!r}, code={self.code!r})>"
