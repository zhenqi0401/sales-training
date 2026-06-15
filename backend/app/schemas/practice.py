"""Pydantic schemas for practice session & chat API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ─────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Request to create a new practice session."""
    module_code: str = Field(
        default="general",
        description="演练场景编码: reception/question/product/objection/closing/fitting/aftercare/general",
    )
    title: str = Field(default="话术演练", description="会话标题")


class ChatRequest(BaseModel):
    """Request to send a message in a practice session."""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息内容")


# ── Response schemas ────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    """Practice session summary."""
    id: int
    user_id: int
    module_code: str
    title: str
    status: str
    total_turns: int
    average_score: Optional[float] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """A single practice message."""
    id: int
    session_id: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[Any] = None
    tool_results: Optional[Any] = None
    evaluation: Optional[Any] = None
    turn_number: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    """Full session detail with messages."""
    session: SessionResponse
    messages: list[MessageResponse]


class SessionListResponse(BaseModel):
    """Paginated session list."""
    total: int
    page: int
    page_size: int
    items: list[SessionResponse]


class CreateSessionResponse(BaseModel):
    """Response after creating a session."""
    session_id: int
    module_code: str
    title: str
    message: str = "会话创建成功"


class ChatDoneData(BaseModel):
    """Data payload for the SSE 'done' event."""
    session_id: int
    turn: int
    average_score: Optional[float] = None
