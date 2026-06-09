"""User model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.learning_progress import LearningProgress
    from app.models.exam_record import ExamRecord
    from app.models.favorite import Favorite
    from app.models.store import Store


class User(Base, TimestampMixin):
    """Platform user — can be super_admin, training_admin, instructor or student."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="用户名"
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False, comment="手机号"
    )
    password_hash: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="密码哈希"
    )
    real_name: Mapped[Optional[str]] = mapped_column(
        String(64), default="", comment="真实姓名"
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="student",
        comment="角色: super_admin, training_admin, instructor, student",
    )
    store_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("stores.id"), nullable=True, comment="所属门店ID"
    )
    avatar: Mapped[Optional[str]] = mapped_column(
        String(512), default="", comment="头像URL"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    must_change_password: Mapped[bool] = mapped_column(
        default=True, comment="首次登录是否必须修改密码"
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后登录时间"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        Text, default="", comment="备注"
    )

    # relationships
    store: Mapped[Optional["Store"]] = relationship(back_populates="users")
    learning_progresses: Mapped[list["LearningProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    exam_records: Mapped[list["ExamRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r}, role={self.role!r})>"
