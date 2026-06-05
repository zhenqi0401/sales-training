"""Script (sales talk) management endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.script import Script
from app.schemas.common import MessageResponse, PaginatedResponse


class ScriptCreate(BaseModel):
    title: str
    category: str = "general"
    theory: Optional[str] = ""
    content: str
    product_id: Optional[int] = None
    tags: Optional[list] = None
    sort_order: int = 0


class ScriptUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    theory: Optional[str] = None
    content: Optional[str] = None
    product_id: Optional[int] = None
    tags: Optional[list] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ScriptResponse(BaseModel):
    id: int
    title: str
    category: str
    theory: Optional[str] = ""
    content: str
    product_id: Optional[int] = None
    tags: Optional[list] = None
    is_active: bool
    sort_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScriptCategoryResponse(BaseModel):
    value: str
    label: str
    count: int


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ScriptResponse], summary="话术列表")
async def list_scripts(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    product_id: int | None = None,
):
    """Paginated script list."""
    query = select(Script)

    if category:
        query = query.where(Script.category == category)
    if status == "draft":
        query = query.where(Script.is_active == False)
    else:
        query = query.where(Script.is_active == True)
    if keyword:
        query = query.where(
            or_(
                Script.title.like(f"%{keyword}%"),
                Script.content.like(f"%{keyword}%"),
            )
        )
    if product_id is not None:
        query = query.where(Script.product_id == product_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Script.sort_order, Script.id).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    scripts = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[ScriptResponse.model_validate(s) for s in scripts],
    )


@router.get("/categories", response_model=list[ScriptCategoryResponse], summary="话术分类选项")
async def list_script_categories(
    session: SessionDep,
    user: CurrentUserDep,
):
    """Return script categories that currently have active content."""
    result = await session.execute(
        select(Script.category, func.count(Script.id))
        .where(Script.is_active == True)
        .group_by(Script.category)
        .order_by(Script.category)
    )

    labels = {
        "opening": "开场白",
        "product": "产品介绍",
        "objection": "异议处理",
        "closing": "促单成交",
        "service": "售后服务",
        "general": "通用话术",
        "prototype_card": "原型卡片",
        "prototype_script": "原型话术",
    }
    return [
        ScriptCategoryResponse(value=category, label=labels.get(category, category), count=count)
        for category, count in result.all()
        if category
    ]


@router.get("/{script_id}", response_model=ScriptResponse, summary="获取话术详情")
async def get_script(
    script_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    script = await session.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="话术不存在")
    return ScriptResponse.model_validate(script)


@router.post("/", response_model=ScriptResponse, status_code=201, summary="创建话术")
async def create_script(
    body: ScriptCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    script = Script(**body.model_dump())
    session.add(script)
    await session.flush()
    return ScriptResponse.model_validate(script)


@router.put("/{script_id}", response_model=ScriptResponse, summary="更新话术")
async def update_script(
    script_id: int,
    body: ScriptUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    script = await session.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="话术不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(script, field, value)

    await session.flush()
    return ScriptResponse.model_validate(script)


@router.delete("/{script_id}", response_model=MessageResponse, summary="删除话术")
async def delete_script(
    script_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    script = await session.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="话术不存在")

    script.is_active = False
    await session.flush()
    return MessageResponse(message="话术已删除")
