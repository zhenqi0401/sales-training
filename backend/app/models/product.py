"""Product model — product knowledge base."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category


class Product(Base, TimestampMixin):
    """Product knowledge entry."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="产品名称"
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, comment="分类ID"
    )
    intro: Mapped[Optional[str]] = mapped_column(
        Text, default="", comment="产品简介"
    )
    specs: Mapped[Optional[dict]] = mapped_column(
        JSON, default=None, comment="规格参数 JSON"
    )
    faq: Mapped[Optional[list]] = mapped_column(
        JSON, default=None, comment="常见问题 JSON [{q, a}]"
    )
    compare_data: Mapped[Optional[dict]] = mapped_column(
        JSON, default=None, comment="对比数据 JSON"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(default=0, comment="排序序号")

    # relationships
    category: Mapped[Optional["Category"]] = relationship(back_populates="products")

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name={self.name!r})>"
