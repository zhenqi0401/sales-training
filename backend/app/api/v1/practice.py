"""Practice session & AI agent chat API endpoints."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.dependencies import CurrentUserDep, SessionDep, require_training_user
from app.models.practice_session import (
    LongTermMemory,
    PracticeMessage,
    PracticeSession,
)
from app.schemas.common import MessageResponse
from app.schemas.practice import (
    ChatDoneData,
    ChatRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    MessageResponse as MessageResp,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
)
from app.services.practice_agent import run_practice_agent
from app.services.practice_memory import extract_insights_from_session

router = APIRouter(dependencies=[Depends(require_training_user())])


def practice_envelope(data=None, message: str = "success", code: int = 200):
    """Unified API response wrapper matching training-web expectations."""
    return {"code": code, "message": message, "data": data}


# ── Sessions CRUD ───────────────────────────────────────────────────────────


@router.post("/sessions", summary="创建演练会话")
async def create_session(
    body: CreateSessionRequest,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Create a new practice session for the current user."""
    ps = PracticeSession(
        user_id=user.id,
        module_code=body.module_code,
        title=body.title,
        status="active",
    )
    session.add(ps)
    await session.flush()

    return practice_envelope(
        CreateSessionResponse(
            session_id=ps.id,
            module_code=ps.module_code,
            title=ps.title,
        ).model_dump()
    )


@router.get("/sessions", summary="演练会话列表")
async def list_sessions(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    module_code: Optional[str] = None,
    status: Optional[str] = None,
):
    """List practice sessions for the current user, with optional filters."""
    query = select(PracticeSession).where(PracticeSession.user_id == user.id)

    if module_code:
        query = query.where(PracticeSession.module_code == module_code)
    if status:
        query = query.where(PracticeSession.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = (
        query.order_by(PracticeSession.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(query)
    items = result.scalars().all()

    return practice_envelope(
        SessionListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[SessionResponse.model_validate(s) for s in items],
        ).model_dump()
    )


@router.get("/sessions/{session_id}", summary="会话详情（含消息）")
async def get_session_detail(
    session_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Get a practice session with all messages."""
    ps = await session.get(PracticeSession, session_id)
    if not ps:
        raise HTTPException(status_code=404, detail="会话不存在")
    if ps.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    msg_result = await session.execute(
        select(PracticeMessage)
        .where(PracticeMessage.session_id == session_id)
        .order_by(PracticeMessage.turn_number, PracticeMessage.id)
    )
    messages = msg_result.scalars().all()

    return practice_envelope(
        SessionDetailResponse(
            session=SessionResponse.model_validate(ps),
            messages=[MessageResp.model_validate(m) for m in messages],
        ).model_dump()
    )


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Delete (abandon) a practice session."""
    ps = await session.get(PracticeSession, session_id)
    if not ps:
        raise HTTPException(status_code=404, detail="会话不存在")
    if ps.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作此会话")

    ps.status = "abandoned"
    await session.flush()
    return practice_envelope(message="会话已删除")


# ── Chat (SSE streaming) ────────────────────────────────────────────────────


@router.post("/sessions/{session_id}/chat", summary="发送消息（SSE 流式）")
async def chat_with_agent(
    session_id: int,
    body: ChatRequest,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
):
    """Send a message to the practice agent and stream the response via SSE.

    Returns a ``text/event-stream`` response with the following event types:
      - ``text`` — partial LLM text token
      - ``tool_call`` — agent invoked a tool
      - ``tool_result`` — tool execution result
      - ``evaluation`` — AI evaluation of the user response
      - ``error`` — an error occurred
      - ``done`` — turn complete
    """
    # Validate session ownership
    ps = await session.get(PracticeSession, session_id)
    if not ps:
        raise HTTPException(status_code=404, detail="会话不存在")
    if ps.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作此会话")
    if ps.status != "active":
        raise HTTPException(status_code=400, detail="会话已结束，无法继续对话")

    async def event_generator():
        try:
            async for sse_event in run_practice_agent(
                session=session,
                session_id=session_id,
                user_id=user.id,
                user_message=body.message,
                module_code=ps.module_code,
            ):
                # Check for client disconnection
                if await request.is_disconnected():
                    break
                yield sse_event

            # Commit all DB changes
            await session.commit()

            # If this looks like a good stopping point, extract insights
            if ps.total_turns and ps.total_turns >= 3:
                try:
                    await extract_insights_from_session(session, session_id, user.id)
                    await session.commit()
                except Exception:
                    pass  # Best-effort insight extraction

        except Exception as exc:
            error_data = {"message": f"Agent 错误: {str(exc)}"}
            yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


# ── Session completion ──────────────────────────────────────────────────────


@router.post("/sessions/{session_id}/complete", summary="结束演练会话")
async def complete_session(
    session_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Mark a practice session as completed and extract long-term memories."""
    ps = await session.get(PracticeSession, session_id)
    if not ps:
        raise HTTPException(status_code=404, detail="会话不存在")
    if ps.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作此会话")

    ps.status = "completed"

    # Extract insights from the session
    try:
        insights = await extract_insights_from_session(session, session_id, user.id)
    except Exception:
        insights = []

    # Generate simple summary
    msg_result = await session.execute(
        select(func.count())
        .select_from(PracticeMessage)
        .where(PracticeMessage.session_id == session_id, PracticeMessage.evaluation.isnot(None))
    )
    eval_count = msg_result.scalar() or 0

    if eval_count > 0:
        from sqlalchemy import select as sa_select
        eval_result = await session.execute(
            sa_select(PracticeMessage.evaluation)
            .where(
                PracticeMessage.session_id == session_id,
                PracticeMessage.evaluation.isnot(None),
            )
        )
        evals = [e[0] for e in eval_result.all() if e[0]]
        scores = [e.get("score", 0) for e in evals if isinstance(e, dict)]
        if scores:
            avg = round(sum(scores) / len(scores), 1)
            ps.average_score = avg
            ps.summary = f"共 {ps.total_turns} 轮对话，平均评分 {avg}/5，提取了 {len(insights)} 条长期记忆"

    await session.flush()
    await session.commit()

    return practice_envelope(
        SessionResponse.model_validate(ps).model_dump(),
        message="会话已完成",
    )
