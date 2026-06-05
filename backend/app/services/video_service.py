"""Video service layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video import Video


class VideoService:
    """Business logic for video management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_published_videos(self, category_id: int | None = None):
        """Return all published videos, optionally filtered by category."""
        query = select(Video).where(Video.status == "published")
        if category_id is not None:
            query = query.where(Video.category_id == category_id)
        query = query.order_by(Video.sort_order, Video.id.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_required_videos(self):
        """Return all mandatory training videos."""
        result = await self.session.execute(
            select(Video)
            .where(Video.is_required == True, Video.status == "published")
            .order_by(Video.sort_order)
        )
        return result.scalars().all()
