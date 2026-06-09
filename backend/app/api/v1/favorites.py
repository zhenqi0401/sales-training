"""Favorites management endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, and_, delete
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.favorite import Favorite
from app.schemas.common import PaginatedResponse
from app.schemas.user import ApiResponse


class FavoriteCreate(BaseModel):
    type: str
    target_id: int


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    type: str
    target_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[FavoriteResponse], summary="收藏列表")
async def list_favorites(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    type: str | None = None,
):
    """List favorites for the current user."""
    query = select(Favorite).where(Favorite.user_id == user.id)

    if type:
        query = query.where(Favorite.type == type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Favorite.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    favorites = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[FavoriteResponse.model_validate(f) for f in favorites],
    )


@router.post("/", response_model=ApiResponse, status_code=201, summary="添加收藏")
async def add_favorite(
    body: FavoriteCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Add a favorite. Idempotent — if already favourited, returns the existing record."""
    # Check if already favourited
    stmt = select(Favorite).where(
        Favorite.user_id == user.id,
        Favorite.type == body.type,
        Favorite.target_id == body.target_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return ApiResponse(message="已收藏", data=FavoriteResponse.model_validate(existing).model_dump())

    fav = Favorite(
        user_id=user.id,
        type=body.type,
        target_id=body.target_id,
    )
    session.add(fav)
    await session.flush()
    return ApiResponse(message="已收藏", data=FavoriteResponse.model_validate(fav).model_dump())


@router.delete("/", response_model=ApiResponse, summary="取消收藏")
async def remove_favorite(
    session: SessionDep,
    user: CurrentUserDep,
    type: str,
    target_id: int,
):
    """Remove a favorite."""
    stmt = select(Favorite).where(
        Favorite.user_id == user.id,
        Favorite.type == type,
        Favorite.target_id == target_id,
    )
    fav = (await session.execute(stmt)).scalar_one_or_none()
    if not fav:
        return ApiResponse(message="已取消收藏")

    await session.delete(fav)
    await session.flush()
    return ApiResponse(message="已取消收藏")
