"""Question management endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.question import Question
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.question import (
    AIQuestionGenerate,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[QuestionResponse], summary="题目列表")
async def list_questions(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    category_id: int | None = None,
    difficulty: str | None = None,
    type: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
):
    """Paginated question list with filters."""
    query = select(Question)

    if category_id is not None:
        query = query.where(Question.category_id == category_id)
    if difficulty:
        if difficulty == "easy":
            query = query.where(Question.difficulty <= 2)
        elif difficulty == "medium":
            query = query.where(Question.difficulty == 3)
        elif difficulty == "hard":
            query = query.where(Question.difficulty >= 4)
        elif difficulty.isdigit():
            query = query.where(Question.difficulty == int(difficulty))
    if type:
        query = query.where(Question.type == type)
    if keyword:
        query = query.where(Question.content.like(f"%{keyword}%"))
    if status == "disabled":
        query = query.where(Question.is_active == False)
    else:
        query = query.where(Question.is_active == True)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Question.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    questions = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[QuestionResponse.model_validate(q) for q in questions],
    )


@router.get("/{question_id}", response_model=QuestionResponse, summary="获取题目详情")
async def get_question(
    question_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    question = await session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return QuestionResponse.model_validate(question)


@router.post("/", response_model=QuestionResponse, status_code=201, summary="创建题目")
async def create_question(
    body: QuestionCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    question = Question(**body.model_dump())
    session.add(question)
    await session.flush()
    return QuestionResponse.model_validate(question)


@router.put("/{question_id}", response_model=QuestionResponse, summary="更新题目")
async def update_question(
    question_id: int,
    body: QuestionUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    question = await session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    await session.flush()
    return QuestionResponse.model_validate(question)


@router.delete("/{question_id}", response_model=MessageResponse, summary="删除题目")
async def delete_question(
    question_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    question = await session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    question.is_active = False
    await session.flush()
    return MessageResponse(message="题目已删除")


@router.post("/ai-generate", response_model=list[QuestionResponse], summary="AI生成题目")
async def ai_generate_questions(
    body: AIQuestionGenerate,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Generate questions using AI (stub implementation)."""
    from app.services.ai_service import generate_questions

    questions = await generate_questions(
        topic=body.topic,
        count=body.count,
        difficulty=body.difficulty,
        question_types=body.question_types,
        category_id=body.category_id,
    )

    # Save generated questions to DB
    db_questions = []
    for q_data in questions:
        q = Question(**q_data)
        session.add(q)
        db_questions.append(q)

    await session.flush()
    return [QuestionResponse.model_validate(q) for q in db_questions]
