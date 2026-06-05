"""Exam service layer."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_paper import ExamPaper
from app.models.exam_record import ExamRecord
from app.models.exam_answer import ExamAnswer
from app.models.question import Question


class ExamService:
    """Business logic for exam operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def score_exam(
        self,
        user_id: int,
        paper_id: int,
        answers: list[dict],
    ) -> dict:
        """Score an exam submission and return results."""
        paper = await self.session.get(ExamPaper, paper_id)
        if not paper or not paper.question_ids:
            raise ValueError("Paper not found or has no questions")

        # Load questions
        stmt = select(Question).where(Question.id.in_(paper.question_ids))
        result = await self.session.execute(stmt)
        questions = {q.id: q for q in result.scalars().all()}

        now = datetime.now(timezone.utc)
        record = ExamRecord(
            user_id=user_id,
            paper_id=paper_id,
            score=0,
            passed=False,
            started_at=now,
            submitted_at=now,
        )
        self.session.add(record)
        await self.session.flush()

        score_per_q = paper.total_score / len(paper.question_ids) if paper.question_ids else 0
        correct_count = 0
        details = []

        for ans in answers:
            q = questions.get(ans["question_id"])
            if not q:
                continue
            is_correct = q.answer.strip().lower() == ans["user_answer"].strip().lower()
            if is_correct:
                correct_count += 1

            self.session.add(
                ExamAnswer(
                    exam_record_id=record.id,
                    question_id=ans["question_id"],
                    user_answer=ans["user_answer"],
                    is_correct=is_correct,
                )
            )
            details.append({
                "question_id": ans["question_id"],
                "is_correct": is_correct,
                "correct_answer": q.answer,
                "analysis": q.analysis,
            })

        record.score = round(correct_count * score_per_q)
        record.passed = record.score >= paper.pass_score
        await self.session.flush()

        return {
            "record_id": record.id,
            "score": record.score,
            "total_score": paper.total_score,
            "passed": record.passed,
            "details": details,
        }
