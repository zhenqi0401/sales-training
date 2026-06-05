"""Exam submission & records endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.exam_answer import ExamAnswer
from app.models.exam_paper import ExamPaper
from app.models.exam_record import ExamRecord
from app.models.question import Question
from app.schemas.common import PaginatedResponse
from app.schemas.exam import (
    AnswerResultItem,
    ExamRecordResponse,
    ExamResult,
    ExamSubmit,
)

router = APIRouter()


@router.post("/submit", response_model=ExamResult, summary="提交考试")
async def submit_exam(
    body: ExamSubmit,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Submit an exam and get instant scoring results."""
    # Verify paper exists and is active
    paper = await session.get(ExamPaper, body.paper_id)
    if not paper or not paper.is_active:
        raise HTTPException(status_code=404, detail="试卷不存在或已停用")

    if not paper.question_ids:
        raise HTTPException(status_code=400, detail="试卷没有题目")

    # Load all questions for the paper
    question_ids = paper.question_ids
    stmt = select(Question).where(
        Question.id.in_(question_ids),
        Question.is_active == True,
    )
    result = await session.execute(stmt)
    questions = {q.id: q for q in result.scalars().all()}

    # Create exam record
    now = datetime.now(timezone.utc)
    record = ExamRecord(
        user_id=user.id,
        paper_id=body.paper_id,
        score=0,
        passed=False,
        started_at=now,
        submitted_at=now,
    )
    session.add(record)
    await session.flush()

    # Score each answer
    total_score = paper.total_score
    score_per_question = total_score / len(question_ids) if question_ids else 0
    correct_count = 0
    answer_results = []

    for answer_item in body.answers:
        question = questions.get(answer_item.question_id)
        if not question:
            continue

        is_correct = question.answer.strip().lower() == answer_item.user_answer.strip().lower()

        exam_answer = ExamAnswer(
            exam_record_id=record.id,
            question_id=answer_item.question_id,
            user_answer=answer_item.user_answer,
            is_correct=is_correct,
        )
        session.add(exam_answer)

        if is_correct:
            correct_count += 1

        answer_results.append(
            AnswerResultItem(
                question_id=answer_item.question_id,
                user_answer=answer_item.user_answer,
                is_correct=is_correct,
                correct_answer=question.answer,
                analysis=question.analysis or "",
            )
        )

    # Calculate score
    record.score = round(correct_count * score_per_question)
    record.passed = record.score >= paper.pass_score
    await session.flush()

    return ExamResult(
        id=record.id,
        paper_id=record.paper_id,
        score=record.score,
        total_score=total_score,
        passed=record.passed,
        started_at=record.started_at,
        submitted_at=record.submitted_at,
        answers=answer_results,
    )


@router.get("/records", response_model=PaginatedResponse[ExamRecordResponse], summary="考试记录")
async def list_exam_records(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    paper_id: int | None = None,
    passed: bool | None = None,
):
    """List exam records for the current user."""
    query = select(ExamRecord).where(ExamRecord.user_id == user.id)

    if paper_id is not None:
        query = query.where(ExamRecord.paper_id == paper_id)
    if passed is not None:
        query = query.where(ExamRecord.passed == passed)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(ExamRecord.submitted_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    records = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[ExamRecordResponse.model_validate(r) for r in records],
    )


@router.get("/records/{record_id}", response_model=ExamResult, summary="考试详情")
async def get_exam_record(
    record_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Get detailed exam record with answers."""
    record = await session.get(ExamRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="记录不存在")

    # Load answers
    stmt = select(ExamAnswer).where(ExamAnswer.exam_record_id == record_id)
    result = await session.execute(stmt)
    answers = result.scalars().all()

    # Load paper for total score
    paper = await session.get(ExamPaper, record.paper_id)

    answer_results = []
    for ans in answers:
        question = await session.get(Question, ans.question_id)
        answer_results.append(
            AnswerResultItem(
                question_id=ans.question_id,
                user_answer=ans.user_answer,
                is_correct=ans.is_correct,
                correct_answer=question.answer if question else "",
                analysis=question.analysis if question else "",
            )
        )

    return ExamResult(
        id=record.id,
        paper_id=record.paper_id,
        score=record.score,
        total_score=paper.total_score if paper else 0,
        passed=record.passed,
        started_at=record.started_at,
        submitted_at=record.submitted_at,
        answers=answer_results,
    )
