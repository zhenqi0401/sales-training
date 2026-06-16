"""Category Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Create a new category."""

    name: str = Field(..., min_length=1, max_length=64)
    code: Optional[str] = None
    icon: Optional[str] = ""
    description: Optional[str] = ""
    sort_order: int = 0
    parent_id: Optional[int] = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    """Update an existing category."""

    name: Optional[str] = None
    code: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Category read model."""

    id: int
    name: str
    code: str
    icon: Optional[str] = ""
    description: Optional[str] = ""
    sort_order: int
    parent_id: Optional[int] = None
    is_active: bool
    video_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: Optional[list["CategoryResponse"]] = None

    model_config = {"from_attributes": True}
