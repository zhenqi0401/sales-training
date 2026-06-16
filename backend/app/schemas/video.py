"""Video Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VideoCreate(BaseModel):
    """Create a new video."""

    title: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = ""
    category_id: int
    file_url: str = Field(..., max_length=512)
    cover_url: Optional[str] = ""
    tags: list[str] = Field(default_factory=list)
    product_ids: list[int] = Field(default_factory=list)
    duration: Optional[int] = 0
    resolution: Optional[str] = ""
    file_size: Optional[int] = 0
    status: str = "draft"
    sort_order: int = 0
    is_required: bool = False
    est_duration: Optional[int] = 0


class VideoUpdate(BaseModel):
    """Update an existing video."""

    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    file_url: Optional[str] = None
    cover_url: Optional[str] = None
    tags: Optional[list[str]] = None
    product_ids: Optional[list[int]] = None
    duration: Optional[int] = None
    resolution: Optional[str] = None
    file_size: Optional[int] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    is_required: Optional[bool] = None
    est_duration: Optional[int] = None


class VideoResponse(BaseModel):
    """Video read model."""

    id: int
    title: str
    description: Optional[str] = ""
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    file_url: str
    cover_url: Optional[str] = ""
    tags: list[str] = Field(default_factory=list)
    product_ids: list[int] = Field(default_factory=list)
    product_names: list[str] = Field(default_factory=list)
    duration: Optional[int] = 0
    resolution: Optional[str] = ""
    file_size: Optional[int] = 0
    status: str
    sort_order: int
    is_required: bool
    est_duration: Optional[int] = 0
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pipeline_log: Optional[dict] = None

    model_config = {"from_attributes": True}


class VideoList(BaseModel):
    """Video list query response."""

    total: int
    items: list[VideoResponse]


class VideoStatusUpdate(BaseModel):
    """Update a single video's shelf status."""

    status: str


class VideoBatchStatusUpdate(BaseModel):
    """Batch shelf status update."""

    ids: list[int]
    status: str
