"""Store model — supports hierarchy via parent_id."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Store(Base, TimestampMixin):
    """Store / organisational unit."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="门店名称"
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="门店编码"
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("stores.id"), nullable=True, comment="上级门店ID"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(512), default="", comment="地址"
    )
    contact_name: Mapped[Optional[str]] = mapped_column(
        String(64), default="", comment="联系人"
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(20), default="", comment="联系电话"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(default=0, comment="排序")

    # self-referential relationship for hierarchy
    parent: Mapped[Optional["Store"]] = relationship(
        "Store", back_populates="children", remote_side="Store.id"
    )
    children: Mapped[list["Store"]] = relationship(
        "Store", back_populates="parent", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(back_populates="store")

    def __repr__(self) -> str:
        return f"<Store(id={self.id}, name={self.name!r}, code={self.code!r})>"
