"""Store management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func

from app.core.dependencies import CurrentUserDep, SessionDep, require_role
from app.models.store import Store
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.category import CategoryCreate, CategoryUpdate

# Re-use CategoryResponse and CategoryCreate which have the same shape
# Let's define simple inline schemas for store
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StoreCreate(BaseModel):
    name: str
    code: str
    parent_id: Optional[int] = None
    address: Optional[str] = ""
    contact_name: Optional[str] = ""
    contact_phone: Optional[str] = ""
    sort_order: int = 0


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[int] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class StoreResponse(BaseModel):
    id: int
    name: str
    code: str
    parent_id: Optional[int] = None
    address: Optional[str] = ""
    contact_name: Optional[str] = ""
    contact_phone: Optional[str] = ""
    is_active: bool
    sort_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


router = APIRouter(dependencies=[Depends(require_role("super_admin", "training_admin"))])


@router.get("/", response_model=PaginatedResponse[StoreResponse], summary="门店列表")
async def list_stores(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
):
    """Paginated store list."""
    query = select(Store)
    if keyword:
        query = query.where(
            (Store.name.like(f"%{keyword}%")) | (Store.code.like(f"%{keyword}%"))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Store.sort_order, Store.id).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    stores = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[StoreResponse.model_validate(s) for s in stores],
    )


@router.get("/tree", response_model=list[StoreResponse], summary="门店树形结构")
async def get_store_tree(
    session: SessionDep,
    user: CurrentUserDep,
):
    """Return flat list of stores sorted by hierarchy (parent, sort_order)."""
    result = await session.execute(
        select(Store).order_by(Store.parent_id.asc().nullsfirst(), Store.sort_order)
    )
    stores = result.scalars().all()
    return [StoreResponse.model_validate(s) for s in stores]


@router.get("/{store_id}", response_model=StoreResponse, summary="获取门店详情")
async def get_store(
    store_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    store = await session.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    return StoreResponse.model_validate(store)


@router.post("/", response_model=StoreResponse, status_code=201, summary="创建门店")
async def create_store(
    body: StoreCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    existing = (
        await session.execute(select(Store).where(Store.code == body.code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="门店编码已存在")

    store = Store(**body.model_dump())
    session.add(store)
    await session.flush()
    return StoreResponse.model_validate(store)


@router.put("/{store_id}", response_model=StoreResponse, summary="更新门店")
async def update_store(
    store_id: int,
    body: StoreUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    store = await session.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(store, field, value)

    await session.flush()
    return StoreResponse.model_validate(store)


@router.delete("/{store_id}", response_model=MessageResponse, summary="删除门店")
async def delete_store(
    store_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    store = await session.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    store.is_active = False
    await session.flush()
    return MessageResponse(message="门店已禁用")
