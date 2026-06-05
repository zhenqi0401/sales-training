"""Question Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    """Create a new question."""

    content: str = Field(..., min_length=1)
    type: str = "single"
    options: Optional[dict] = None
    answer: str = Field(..., min_length=1)
    analysis: Optional[str] = ""
    difficulty: int = 1
    category_id: Optional[int] = None
    video_id: Optional[int] = None
    source: Optional[str] = "manual"
    tags: Optional[list] = None


class QuestionUpdate(BaseModel):
    """Update an existing question."""

    content: Optional[str] = None
    type: Optional[str] = None
    options: Optional[dict] = None
    answer: Optional[str] = None
    analysis: Optional[str] = None
    difficulty: Optional[int] = None
    category_id: Optional[int] = None
    video_id: Optional[int] = None
    tags: Optional[list] = None


class QuestionResponse(BaseModel):
    """Question read model."""

    id: int
    content: str
    type: str
    options: Optional[dict] = None
    answer: str
    analysis: Optional[str] = ""
    difficulty: int
    category_id: Optional[int] = None
    video_id: Optional[int] = None
    source: Optional[str] = ""
    tags: Optional[list] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AIQuestionGenerate(BaseModel):
    """Payload for AI question generation."""

    topic: str = Field(..., min_length=1, description="话题或知识点")
    count: int = Field(default=5, ge=1, le=20, description="生成题目数量")
    difficulty: int = Field(default=2, ge=1, le=5, description="难度 1-5")
    question_types: list[str] = Field(
        default=["single", "multiple", "true_false"],
        description="题型列表",
    )
    category_id: Optional[int] = None
