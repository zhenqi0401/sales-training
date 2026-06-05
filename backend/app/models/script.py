"""Script model — sales scripts / talking points."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Script(Base, TimestampMixin):
    """Sales script / talking points / product knowledge card."""

    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="话术标题"
    )
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="general", comment="话术分类: general, product, objection, closing"
    )
    theory: Mapped[Optional[str]] = mapped_column(
        Text, default="", comment="理论基础说明"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="话术内容"
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id"), nullable=True, comment="关联产品ID"
    )
    tags: Mapped[Optional[list]] = mapped_column(
        JSON, default=None, comment="标签列表"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序序号")

    def __repr__(self) -> str:
        return f"<Script(id={self.id}, title={self.title!r}, category={self.category!r})>"
