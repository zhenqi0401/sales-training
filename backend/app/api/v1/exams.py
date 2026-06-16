"""Training exam flow endpoints."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import random
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, func, select

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.category import Category
from app.models.exam_answer import ExamAnswer
from app.models.exam_paper import ExamPaper
from app.models.exam_record import ExamRecord
from app.models.question import Question
from app.schemas.exam import ExamSubmit
from app.schemas.user import ApiResponse

router = APIRouter()


LEVEL_RULES: dict[str, dict[str, Any]] = {
    "L1": {
        "title": "初级考核",
        "description": "基础产品知识 + 接待流程",
        "duration": 60,
        "passScore": 16,
        "totalScore": 20,
        "questionCount": 20,
        "passRate": 0.80,
    },
    "L2": {
        "title": "中级考核",
        "description": "专业知识 + 销售技巧",
        "duration": 60,
        "passScore": 22,
        "totalScore": 25,
        "questionCount": 25,
        "passRate": 0.85,
    },
    "L3": {
        "title": "高级考核",
        "description": "综合能力 + 实战场景",
        "duration": 60,
        "passScore": 27,
        "totalScore": 30,
        "questionCount": 30,
        "passRate": 0.90,
    },
    "SPRINT": {
        "title": "冲刺模式",
        "description": "随机抽题，限时挑战",
        "duration": 10,
        "passScore": 60,
        "totalScore": 100,
        "questionCount": 10,
    },
    "WRONG": {
        "title": "错题重练",
        "description": "从错题本抽题重新练习",
        "duration": 20,
        "passScore": 60,
        "totalScore": 100,
        "questionCount": 20,
    },
}


def envelope(data: object | None = None, message: str = "success") -> ApiResponse:
    return ApiResponse(message=message, data=data)


def normalize_level(level: str | None) -> str:
    value = (level or "L1").upper()
    return value if value in LEVEL_RULES else "L1"


def frontend_question_type(question_type: str) -> str:
    if question_type in {"multi", "multiple"}:
        return "multi"
    if question_type in {"judge", "true_false", "boolean"}:
        return "judge"
    return "single"


def option_payload(options: dict | None, question_type: str) -> list[dict[str, str]]:
    if options:
        return [
            {"label": str(key), "value": str(key), "content": str(value)}
            for key, value in options.items()
        ]
    if frontend_question_type(question_type) == "judge":
        return [
            {"label": "A", "value": "true", "content": "正确"},
            {"label": "B", "value": "false", "content": "错误"},
        ]
    return []


def normalize_answer(value: str | list[str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [str(item).strip().upper() for item in value if str(item).strip()]
        return ",".join(sorted(parts))

    text = str(value).strip()
    if not text:
        return ""
    if "," in text or "，" in text or "|" in text:
        parts = [part.strip().upper() for part in re.split(r"[,，|]", text) if part.strip()]
        return ",".join(sorted(parts))
    if re.fullmatch(r"[A-Za-z]{2,}", text):
        return ",".join(sorted(text.upper()))
    return text.lower() if text.lower() in {"true", "false"} else text.upper()


def is_answer_correct(question: Question, user_answer: str) -> bool:
    return normalize_answer(question.answer) == normalize_answer(user_answer)


async def category_name(session: SessionDep, question: Question) -> str:
    if question.category_id:
        category = await session.get(Category, question.category_id)
        if category:
            return category.name
    if question.tags:
        return str(question.tags[0])
    return "未分类"


async def question_payload(
    session: SessionDep,
    question: Question,
    score: int = 0,
    include_answer: bool = False,
    exam_level: str | None = None,
) -> dict[str, Any]:
    category = await category_name(session, question)
    return {
        "id": question.id,
        "examLevel": exam_level or difficulty_to_level(question.difficulty),
        "type": frontend_question_type(question.type),
        "content": question.content,
        "options": option_payload(question.options, question.type),
        "answer": question.answer if include_answer else "",
        "score": score,
        "analysis": question.analysis or "",
        "knowledgePoint": category,
        "categoryId": question.category_id,
        "categoryName": category,
        "tags": question.tags or [],
    }


def difficulty_to_level(difficulty: int | None) -> str:
    value = difficulty or 1
    if value <= 2:
        return "L1"
    if value <= 4:
        return "L2"
    return "L3"


def paper_level(paper: ExamPaper | None) -> str:
    if not paper:
        return "L1"
    for level, rules in LEVEL_RULES.items():
        if paper.title == rules["title"]:
            return level
    return difficulty_to_level(paper.difficulty_level)


async def active_questions(session: SessionDep) -> list[Question]:
    return (
        await session.execute(
            select(Question)
            .where(Question.is_active == True)
            .order_by(Question.difficulty, Question.id)
        )
    ).scalars().all()


async def find_paper_for_level(session: SessionDep, level: str) -> ExamPaper | None:
    if level in {"SPRINT", "WRONG"}:
        return None

    expected_title = LEVEL_RULES[level]["title"]
    papers = (
        await session.execute(
            select(ExamPaper)
            .where(ExamPaper.is_active == True)
            .order_by(ExamPaper.id)
        )
    ).scalars().all()
    if not papers:
        return None
    title_matches = [paper for paper in papers if paper.title == expected_title]
    if title_matches:
        return title_matches[0]
    return papers[0]


async def ensure_paper_for_level(session: SessionDep, level: str) -> ExamPaper:
    paper = await find_paper_for_level(session, level)
    if paper:
        return paper

    rules = LEVEL_RULES[level]
    candidates = await active_questions(session)
    if not candidates:
        raise HTTPException(status_code=400, detail="暂无可用题目")

    random.shuffle(candidates)
    question_ids = [question.id for question in candidates[: rules["questionCount"]]]
    paper = ExamPaper(
        title=rules["title"],
        description=rules["description"],
        duration=rules["duration"],
        pass_score=rules["passScore"],
        total_score=rules["totalScore"],
        question_ids=question_ids,
        is_active=True,
    )
    session.add(paper)
    await session.flush()
    return paper


async def questions_for_level(session: SessionDep, user_id: int, level: str) -> tuple[ExamPaper | None, list[Question]]:
    level = normalize_level(level)
    if level == "SPRINT":
        questions = await active_questions(session)
        random.shuffle(questions)
        return None, questions[: LEVEL_RULES[level]["questionCount"]]

    if level == "WRONG":
        wrong_ids = (
            await session.execute(
                select(ExamAnswer.question_id)
                .join(ExamRecord, ExamRecord.id == ExamAnswer.exam_record_id)
                .where(ExamRecord.user_id == user_id, ExamAnswer.is_correct == False)
                .order_by(desc(ExamAnswer.created_at))
            )
        ).scalars().all()
        unique_ids = list(dict.fromkeys(wrong_ids))
        if not unique_ids:
            return None, []
        questions = (
            await session.execute(
                select(Question).where(Question.id.in_(unique_ids), Question.is_active == True)
            )
        ).scalars().all()
        by_id = {question.id: question for question in questions}
        return None, [by_id[qid] for qid in unique_ids if qid in by_id][: LEVEL_RULES[level]["questionCount"]]

    paper = await ensure_paper_for_level(session, level)
    rules = LEVEL_RULES[level]
    # Randomly select questions from the entire bank for each attempt
    candidates = await active_questions(session)
    if not candidates:
        raise HTTPException(status_code=400, detail="暂无可用题目")
    random.shuffle(candidates)
    selected = candidates[: rules["questionCount"]]
    # Update paper with the fresh selection for record-keeping
    paper.question_ids = [question.id for question in selected]
    await session.flush()
    return paper, selected


async def exam_record_payload(session: SessionDep, record: ExamRecord, include_answers: bool = False) -> dict[str, Any]:
    paper = await session.get(ExamPaper, record.paper_id)
    answers = (
        await session.execute(
            select(ExamAnswer).where(ExamAnswer.exam_record_id == record.id).order_by(ExamAnswer.id)
        )
    ).scalars().all()
    questions_by_id = {}
    if answers:
        questions = (
            await session.execute(
                select(Question).where(Question.id.in_([answer.question_id for answer in answers]))
            )
        ).scalars().all()
        questions_by_id = {question.id: question for question in questions}

    total_count = len(paper.question_ids or []) if paper and paper.question_ids else len(answers)
    correct_count = sum(1 for answer in answers if answer.is_correct)
    duration = 0
    if record.started_at and record.submitted_at:
        try:
            duration = max(0, round((record.submitted_at - record.started_at).total_seconds()))
        except TypeError:
            duration = 0

    payload: dict[str, Any] = {
        "id": record.id,
        "userId": record.user_id,
        "paperId": record.paper_id,
        "paperTitle": paper.title if paper else "",
        "examLevel": paper_level(paper),
        "score": record.score,
        "totalScore": paper.total_score if paper else 100,
        "passScore": paper.pass_score if paper else 60,
        "passRate": round((paper.pass_score / paper.total_score), 2) if paper and paper.total_score else 0.6,
        "passed": record.passed,
        "duration": duration,
        "correctCount": correct_count,
        "totalCount": total_count,
        "submittedAt": record.submitted_at.isoformat() if record.submitted_at else "",
        "startedAt": record.started_at.isoformat() if record.started_at else "",
        "answers": [],
        "categoryScores": [],
        "weakPoints": [],
    }

    category_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0, "score": 0})
    answer_items = []
    score_per_question = (paper.total_score / total_count) if paper and total_count else 0
    for answer in answers:
        question = questions_by_id.get(answer.question_id)
        if not question:
            continue
        category = await category_name(session, question)
        category_stats[category]["total"] += 1
        if answer.is_correct:
            category_stats[category]["correct"] += 1
            category_stats[category]["score"] += round(score_per_question)
        if include_answers:
            answer_items.append(
                {
                    "questionId": answer.question_id,
                    "question": await question_payload(session, question, round(score_per_question), include_answer=True, exam_level=paper_level(paper)),
                    "selected": answer.user_answer,
                    "userAnswer": answer.user_answer,
                    "correct": answer.is_correct,
                    "isCorrect": answer.is_correct,
                    "correctAnswer": question.answer,
                    "score": round(score_per_question) if answer.is_correct else 0,
                    "analysis": question.analysis or "",
                    "knowledgePoint": category,
                }
            )

    payload["answers"] = answer_items
    payload["categoryScores"] = [
        {
            "category": category,
            "score": stats["score"],
            "totalScore": round(stats["total"] * score_per_question),
            "correctCount": stats["correct"],
            "totalCount": stats["total"],
        }
        for category, stats in category_stats.items()
    ]
    payload["weakPoints"] = [
        item["category"]
        for item in payload["categoryScores"]
        if item["totalCount"] and item["correctCount"] / item["totalCount"] < 0.7
    ]
    return payload


@router.get("/config/{level}", response_model=ApiResponse, summary="考试规则")
async def get_exam_config(level: str, session: SessionDep, user: CurrentUserDep):
    level = normalize_level(level)
    rules = LEVEL_RULES[level].copy()
    paper = await find_paper_for_level(session, level)
    if paper:
        rules["paperId"] = paper.id
        if paper.description:
            rules["description"] = paper.description
    rules["level"] = level
    if "passRate" not in rules or not rules.get("passRate"):
        rules["passRate"] = LEVEL_RULES.get(level, {}).get("passRate", 0.6)
    return envelope(rules)


@router.get("/questions/{level}", response_model=ApiResponse, summary="考试题目")
async def get_exam_questions(level: str, session: SessionDep, user: CurrentUserDep):
    paper, questions = await questions_for_level(session, user.id, normalize_level(level))
    total_score = paper.total_score if paper else LEVEL_RULES[normalize_level(level)]["totalScore"]
    score = round(total_score / len(questions)) if questions else 0
    exam_level = normalize_level(level)
    return envelope([await question_payload(session, question, score, exam_level=exam_level) for question in questions])


@router.get("/sprint", response_model=ApiResponse, summary="冲刺模式题目")
async def get_sprint_questions(session: SessionDep, user: CurrentUserDep):
    _, questions = await questions_for_level(session, user.id, "SPRINT")
    score = round(LEVEL_RULES["SPRINT"]["totalScore"] / len(questions)) if questions else 0
    return envelope([await question_payload(session, question, score, exam_level="SPRINT") for question in questions])


@router.post("/submit", response_model=ApiResponse, summary="提交考试")
async def submit_exam(body: ExamSubmit, session: SessionDep, user: CurrentUserDep):
    """Submit an exam and get instant scoring results."""
    level = normalize_level(body.level)
    paper = await session.get(ExamPaper, body.paper_id) if body.paper_id else None
    if not paper:
        if level in {"SPRINT", "WRONG"}:
            question_ids = [item.question_id for item in body.answers]
            if not question_ids:
                raise HTTPException(status_code=400, detail="提交答案不能为空")
            rules = LEVEL_RULES[level]
            paper = ExamPaper(
                title=rules["title"],
                description=rules["description"],
                duration=rules["duration"],
                pass_score=rules["passScore"],
                total_score=rules["totalScore"],
                question_ids=question_ids,
                is_active=True,
            )
            session.add(paper)
            await session.flush()
        else:
            paper = await ensure_paper_for_level(session, level)
    if not paper or not paper.is_active:
        raise HTTPException(status_code=404, detail="试卷不存在或已停用")

    question_ids = paper.question_ids or [item.question_id for item in body.answers]
    if level not in {"SPRINT", "WRONG"}:
        # For L1/L2/L3, prefer the user's actual answered questions
        # because paper.question_ids may have been refreshed by another concurrent request
        body_qids = [item.question_id for item in body.answers]
        if body_qids:
            question_ids = body_qids
            paper.question_ids = body_qids
            await session.flush()
    if not question_ids:
        raise HTTPException(status_code=400, detail="试卷没有题目")

    questions = (
        await session.execute(
            select(Question).where(Question.id.in_(question_ids), Question.is_active == True)
        )
    ).scalars().all()
    by_id = {question.id: question for question in questions}
    ordered_questions = [by_id[qid] for qid in question_ids if qid in by_id]
    if not ordered_questions:
        raise HTTPException(status_code=400, detail="试卷没有可用题目")

    submitted_map = {item.question_id: item.answer_value for item in body.answers}
    now = datetime.now(timezone.utc)
    started_at = now - timedelta(seconds=max(body.duration or 0, 0))
    record = ExamRecord(
        user_id=user.id,
        paper_id=paper.id,
        score=0,
        passed=False,
        started_at=started_at,
        submitted_at=now,
    )
    session.add(record)
    await session.flush()

    score_per_question = paper.total_score / len(ordered_questions)
    correct_count = 0
    for question in ordered_questions:
        user_answer = submitted_map.get(question.id, "")
        correct = is_answer_correct(question, user_answer)
        if correct:
            correct_count += 1
        session.add(
            ExamAnswer(
                exam_record_id=record.id,
                question_id=question.id,
                user_answer=user_answer,
                is_correct=correct,
            )
        )

    record.score = round(correct_count * score_per_question)
    record.passed = record.score >= paper.pass_score
    await session.flush()

    return envelope(await exam_record_payload(session, record, include_answers=True), message="提交成功")


@router.get("/records", response_model=ApiResponse, summary="考试记录")
async def list_exam_records(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    pageSize: int | None = None,
    paper_id: int | None = None,
    paperId: int | None = None,
    passed: bool | None = None,
):
    page_size = pageSize or page_size
    paper_id = paperId if paperId is not None else paper_id
    query = select(ExamRecord).where(ExamRecord.user_id == user.id)
    if paper_id is not None:
        query = query.where(ExamRecord.paper_id == paper_id)
    if passed is not None:
        query = query.where(ExamRecord.passed == passed)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    records = (
        await session.execute(
            query.order_by(desc(ExamRecord.submitted_at)).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()

    return envelope(
        {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "items": [await exam_record_payload(session, record) for record in records],
        }
    )


@router.get("/records/{record_id}", response_model=ApiResponse, summary="考试详情")
async def get_exam_record(record_id: int, session: SessionDep, user: CurrentUserDep):
    record = await session.get(ExamRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="记录不存在")
    return envelope(await exam_record_payload(session, record, include_answers=True))


@router.get("/wrong-answers", response_model=ApiResponse, summary="错题本")
async def list_wrong_answers(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    pageSize: int | None = None,
    category_id: int | None = None,
    categoryId: int | None = None,
    keyword: str | None = None,
):
    page_size = pageSize or page_size
    category_id = categoryId if categoryId is not None else category_id
    rows = (
        await session.execute(
            select(ExamAnswer, Question)
            .join(ExamRecord, ExamRecord.id == ExamAnswer.exam_record_id)
            .join(Question, Question.id == ExamAnswer.question_id)
            .where(ExamRecord.user_id == user.id, ExamAnswer.is_correct == False)
            .order_by(desc(ExamAnswer.created_at))
        )
    ).all()

    grouped: dict[int, dict[str, Any]] = {}
    counts: Counter[int] = Counter()
    for answer, question in rows:
        if category_id is not None and question.category_id != category_id:
            continue
        if keyword and keyword not in question.content and keyword not in (question.analysis or ""):
            continue
        counts[question.id] += 1
        if question.id not in grouped:
            grouped[question.id] = {"answer": answer, "question": question}

    all_items = list(grouped.values())
    total = len(all_items)
    paged = all_items[(page - 1) * page_size : page * page_size]
    items = []
    for item in paged:
        answer = item["answer"]
        question = item["question"]
        items.append(
            {
                "id": question.id,
                "question": await question_payload(session, question, include_answer=True),
                "userAnswer": answer.user_answer,
                "examId": answer.exam_record_id,
                "wrongCount": counts[question.id],
                "lastWrongAt": answer.created_at.isoformat() if answer.created_at else "",
            }
        )

    return envelope(
        {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "items": items,
        }
    )


@router.get("/wrong-answers/stats", response_model=ApiResponse, summary="错题统计")
async def wrong_answer_stats(session: SessionDep, user: CurrentUserDep):
    rows = (
        await session.execute(
            select(ExamAnswer, Question)
            .join(ExamRecord, ExamRecord.id == ExamAnswer.exam_record_id)
            .join(Question, Question.id == ExamAnswer.question_id)
            .where(ExamRecord.user_id == user.id, ExamAnswer.is_correct == False)
        )
    ).all()
    by_category: Counter[str] = Counter()
    by_tag: Counter[str] = Counter()
    for _answer, question in rows:
        by_category[await category_name(session, question)] += 1
        for tag in question.tags or []:
            by_tag[str(tag)] += 1
    return envelope(
        {
            "totalWrong": len(rows),
            "weakCategories": [{"name": name, "count": count} for name, count in by_category.most_common()],
            "weakKnowledgePoints": [{"name": name, "count": count} for name, count in by_tag.most_common(10)],
        }
    )


@router.get("/trend", response_model=ApiResponse, summary="成绩趋势")
async def exam_trend(session: SessionDep, user: CurrentUserDep):
    records = (
        await session.execute(
            select(ExamRecord)
            .where(ExamRecord.user_id == user.id)
            .order_by(ExamRecord.submitted_at)
            .limit(30)
        )
    ).scalars().all()
    return envelope(
        [
            {
                "recordId": record.id,
                "score": record.score,
                "passed": record.passed,
                "submittedAt": record.submitted_at.isoformat() if record.submitted_at else "",
            }
            for record in records
        ]
    )
