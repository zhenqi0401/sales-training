"""Question Pydantic schemas."""

from datetime import datetime
from typing import Literal, Optional

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


class QuestionBatchDelete(BaseModel):
    """Batch delete questions by IDs."""

    ids: list[int] = Field(..., min_length=1)


class QuestionBatchImport(BaseModel):
    """Batch import questions from parsed Excel rows."""

    questions: list[QuestionCreate] = Field(..., min_length=1)


class AIQuestionReviewSave(BaseModel):
    """Persist AI generated questions after administrator review."""

    questions: list[QuestionCreate] = Field(..., min_length=1)


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

    video_id: int = Field(..., description="关联视频ID")
    topic: Optional[str] = Field(default="", description="补充主题或知识点")
    count: int = Field(default=5, ge=1, le=50, description="生成题目数量")
    difficulty_level: Literal["L1", "L2", "L3"] = Field(default="L2", description="难度 L1/L2/L3")
    question_type_ratios: dict[str, int] = Field(
        default_factory=lambda: {"single": 60, "multiple": 30, "true_false": 10},
        description="题型比例，key 为 single/multiple/true_false，value 为百分比或权重",
    )
    category_id: Optional[int] = None
    product_category_id: Optional[int] = None
    knowledge_points: list[str] = Field(default_factory=list)
    transcript: Optional[str] = Field(default="", description="可选：人工提供的字幕/转写文本")


class AIQuestionDraft(BaseModel):
    """AI generated question draft for administrator review."""

    content: str
    type: str
    options: Optional[dict] = None
    answer: str
    analysis: Optional[str] = ""
    difficulty: int
    category_id: Optional[int] = None
    video_id: Optional[int] = None
    source: str = "ai"
    tags: list[str] = Field(default_factory=list)
