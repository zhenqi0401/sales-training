"""Common Pydantic response models."""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[T]


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    detail: Optional[str] = None
