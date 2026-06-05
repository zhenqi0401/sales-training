"""Question service layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question


class QuestionService:
    """Business logic for question management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_questions_by_ids(self, question_ids: list[int]) -> list[Question]:
        """Fetch questions by their IDs."""
        if not question_ids:
            return []
        result = await self.session.execute(
            select(Question)
            .where(Question.id.in_(question_ids), Question.is_active == True)
        )
        return result.scalars().all()

    async def get_questions_by_category(self, category_id: int) -> list[Question]:
        """Fetch questions for a given category."""
        result = await self.session.execute(
            select(Question)
            .where(Question.category_id == category_id, Question.is_active == True)
            .order_by(Question.difficulty)
        )
        return result.scalars().all()
