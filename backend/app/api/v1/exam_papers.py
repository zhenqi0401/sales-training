"""Exam paper management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func

from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
from app.models.exam_paper import ExamPaper
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.exam import ExamPaperCreate, ExamPaperResponse, ExamPaperUpdate

router = APIRouter(dependencies=[Depends(require_admin())])


@router.get("/", response_model=PaginatedResponse[ExamPaperResponse], summary="试卷列表")
async def list_exam_papers(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
):
    """Paginated exam paper list."""
    query = select(ExamPaper).where(ExamPaper.is_active == True)
    if keyword:
        query = query.where(ExamPaper.title.like(f"%{keyword}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(ExamPaper.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    papers = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[ExamPaperResponse.model_validate(p) for p in papers],
    )


@router.get("/{paper_id}", response_model=ExamPaperResponse, summary="获取试卷详情")
async def get_exam_paper(
    paper_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    paper = await session.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    # Optionally load full question details
    return ExamPaperResponse.model_validate(paper)


@router.post("/", response_model=ExamPaperResponse, status_code=201, summary="创建试卷")
async def create_exam_paper(
    body: ExamPaperCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    paper = ExamPaper(**body.model_dump())
    session.add(paper)
    await session.flush()
    return ExamPaperResponse.model_validate(paper)


@router.put("/{paper_id}", response_model=ExamPaperResponse, summary="更新试卷")
async def update_exam_paper(
    paper_id: int,
    body: ExamPaperUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    paper = await session.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(paper, field, value)

    await session.flush()
    return ExamPaperResponse.model_validate(paper)


@router.delete("/{paper_id}", response_model=MessageResponse, summary="删除试卷")
async def delete_exam_paper(
    paper_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    paper = await session.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    paper.is_active = False
    await session.flush()
    return MessageResponse(message="试卷已删除")
