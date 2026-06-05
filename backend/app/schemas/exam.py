"""Exam-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExamPaperCreate(BaseModel):
    """Create a new exam paper."""

    title: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = ""
    duration: int = Field(default=60, ge=1, description="考试时长（分钟）")
    pass_score: int = Field(default=60, ge=0)
    total_score: int = Field(default=100, ge=1)
    question_ids: list[int] = Field(default=[], description="题目ID列表")
    difficulty_level: int = Field(default=1, ge=1, le=5)


class ExamPaperUpdate(BaseModel):
    """Update an existing exam paper."""

    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    pass_score: Optional[int] = None
    total_score: Optional[int] = None
    question_ids: Optional[list[int]] = None
    difficulty_level: Optional[int] = None


class ExamPaperResponse(BaseModel):
    """Exam paper read model."""

    id: int
    title: str
    description: Optional[str] = ""
    duration: int
    pass_score: int
    total_score: int
    question_ids: Optional[list] = None
    difficulty_level: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ExamSubmit(BaseModel):
    """Submit an exam."""

    paper_id: int
    answers: list["AnswerItem"]


class AnswerItem(BaseModel):
    """Single answer item within an exam submission."""

    question_id: int
    user_answer: str


class ExamResult(BaseModel):
    """Exam result response."""

    id: int
    paper_id: int
    score: int
    total_score: int
    passed: bool
    started_at: datetime
    submitted_at: Optional[datetime] = None
    answers: list["AnswerResultItem"]


class AnswerResultItem(BaseModel):
    """Answer result item with correct answer."""

    question_id: int
    user_answer: str
    is_correct: bool
    correct_answer: str
    analysis: Optional[str] = ""


class ExamRecordResponse(BaseModel):
    """Exam record read model."""

    id: int
    user_id: int
    paper_id: int
    score: int
    passed: bool
    started_at: datetime
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StudyStatsResponse(BaseModel):
    """Student study statistics."""

    total_videos: int = 0
    completed_videos: int = 0
    in_progress_videos: int = 0
    total_exams: int = 0
    passed_exams: int = 0
    average_score: float = 0.0
