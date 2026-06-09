"""Question management endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import String, cast, func, select

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.question import Question
from app.models.product import Product
from app.models.video import Video
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.question import (
    AIQuestionDraft,
    AIQuestionGenerate,
    AIQuestionReviewSave,
    QuestionBatchDelete,
    QuestionBatchImport,
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
    tag: str | None = None,
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
    if tag:
        query = query.where(cast(Question.tags, String).like(f'%"{tag}"%'))
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


@router.post("/batch-delete", response_model=MessageResponse, summary="批量删除题目")
async def batch_delete_questions(
    body: QuestionBatchDelete,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Soft-delete multiple active questions."""
    unique_ids = list(dict.fromkeys(body.ids))
    result = await session.execute(
        select(Question).where(
            Question.id.in_(unique_ids),
            Question.is_active == True,
        )
    )
    questions = result.scalars().all()
    if not questions:
        raise HTTPException(status_code=404, detail="未找到可删除的题目")

    for question in questions:
        question.is_active = False

    await session.flush()
    return MessageResponse(message=f"成功删除 {len(questions)} 道题目")


@router.post("/import", response_model=MessageResponse, summary="批量导入题目")
async def import_questions(
    body: QuestionBatchImport,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Import questions parsed from the Excel template."""
    created_count = 0
    for item in body.questions:
        data = item.model_dump()
        data["source"] = "import"
        session.add(Question(**data))
        created_count += 1

    await session.flush()
    return MessageResponse(message=f"成功导入 {created_count} 道题目")


@router.post("/ai-generate", response_model=list[AIQuestionDraft], summary="AI生成题目草稿")
async def ai_generate_questions(
    body: AIQuestionGenerate,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Generate AI question drafts for administrator review.

    Drafts are intentionally not persisted. Use /ai-review-save after the
    administrator edits/deletes/supplements and approves them.
    """
    from app.services.ai_service import generate_questions

    video = await session.get(Video, body.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="关联视频不存在")

    product_category_id = body.product_category_id or video.category_id
    product_query = select(Product).where(Product.is_active == True)
    product_ids = video.product_ids or []
    if product_ids:
        product_query = product_query.where(Product.id.in_(product_ids))
    elif product_category_id is not None:
        product_query = product_query.where(Product.category_id == product_category_id)
    else:
        product_query = product_query.limit(10)
    products = (await session.execute(product_query)).scalars().all()
    product_knowledge = [
        {
            "id": product.id,
            "name": product.name,
            "category_id": product.category_id,
            "intro": product.intro or "",
            "specs": product.specs or {},
            "faq": product.faq or [],
            "compare_data": product.compare_data or {},
        }
        for product in products
    ]

    questions = await generate_questions(
        video_title=video.title,
        video_file_url=video.file_url,
        count=body.count,
        difficulty_level=body.difficulty_level,
        question_type_ratios=body.question_type_ratios,
        category_id=body.category_id,
        video_id=body.video_id,
        product_category_id=product_category_id,
        knowledge_points=body.knowledge_points,
        topic=body.topic,
        transcript=body.transcript,
        product_knowledge=product_knowledge,
    )

    return [AIQuestionDraft.model_validate(q) for q in questions]


@router.post("/ai-review-save", response_model=list[QuestionResponse], summary="保存AI审核题目")
async def save_reviewed_ai_questions(
    body: AIQuestionReviewSave,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Persist administrator-approved AI question drafts."""
    db_questions = []
    for item in body.questions:
        data = item.model_dump()
        data["source"] = "ai"
        question = Question(**data)
        session.add(question)
        db_questions.append(question)
    await session.flush()
    return [QuestionResponse.model_validate(question) for question in db_questions]


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
