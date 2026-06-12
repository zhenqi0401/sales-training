"""Sales audio file model."""
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalesAudioFile(Base, TimestampMixin):
    __tablename__ = "sales_audio_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(256), default="")
    duration: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    transcript: Mapped[Optional[str]] = mapped_column(Text, default="")
    summary: Mapped[Optional[str]] = mapped_column(Text, default="")
    methodology_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
