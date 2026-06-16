"""Category management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pypinyin import lazy_pinyin
from sqlalchemy import func, select

from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
from app.models.category import Category
from app.models.video import Video
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter()


def to_category_response(
    category: Category,
    children: list[CategoryResponse] | None = None,
    video_count: int = 0,
) -> CategoryResponse:
    """Build a category response without triggering lazy relationship loading."""
    return CategoryResponse(
        id=category.id,
        name=category.name,
        code=category.code,
        icon=category.icon,
        description=category.description,
        sort_order=category.sort_order,
        parent_id=category.parent_id,
        is_active=category.is_active,
        video_count=video_count,
        created_at=category.created_at,
        updated_at=category.updated_at,
        children=children,
    )


async def get_category_video_counts(
    session: SessionDep,
    category_ids: list[int],
) -> dict[int, int]:
    if not category_ids:
        return {}
    rows = await session.execute(
        select(Video.category_id, func.count(Video.id))
        .where(Video.category_id.in_(category_ids))
        .group_by(Video.category_id)
    )
    return {int(category_id): int(count) for category_id, count in rows.all() if category_id is not None}


@router.get("/", response_model=PaginatedResponse[CategoryResponse], summary="分类列表")
async def list_categories(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 100,
    parent_id: int | None = None,
    all_levels: bool = True,
):
    """Paginated category list."""
    query = select(Category).where(Category.is_active == True)
    if parent_id is not None:
        query = query.where(Category.parent_id == parent_id)
    elif not all_levels:
        query = query.where(Category.parent_id.is_(None))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(
        Category.parent_id.isnot(None),
        Category.parent_id,
        Category.sort_order,
        Category.id,
    ).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    categories = result.scalars().all()
    video_counts = await get_category_video_counts(session, [category.id for category in categories])

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[to_category_response(c, video_count=video_counts.get(c.id, 0)) for c in categories],
    )


@router.get("/tree", response_model=list[CategoryResponse], summary="分类树形结构")
async def get_category_tree(
    session: SessionDep,
    user: CurrentUserDep,
):
    """Return all active categories in a nested tree structure."""
    result = await session.execute(
        select(Category)
        .where(Category.is_active == True)
        .order_by(
            Category.parent_id.isnot(None),
            Category.parent_id,
            Category.sort_order,
            Category.id,
        )
    )
    all_cats = result.scalars().all()
    video_counts = await get_category_video_counts(session, [category.id for category in all_cats])

    cat_map: dict[int, CategoryResponse] = {}
    for category in all_cats:
        cat_map[category.id] = to_category_response(category, [], video_counts.get(category.id, 0))

    roots: list[CategoryResponse] = []
    for category in cat_map.values():
        if category.parent_id and category.parent_id in cat_map:
            cat_map[category.parent_id].children.append(category)
        else:
            roots.append(category)

    return roots


@router.get("/{category_id}", response_model=CategoryResponse, summary="获取分类详情")
async def get_category(
    category_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    category = await session.get(Category, category_id)
    if not category or not category.is_active:
        raise HTTPException(status_code=404, detail="分类不存在")
    video_counts = await get_category_video_counts(session, [category.id])
    return to_category_response(category, video_count=video_counts.get(category.id, 0))


@router.post("/", response_model=CategoryResponse, status_code=201, summary="创建分类",
             dependencies=[Depends(require_admin())])
async def create_category(
    body: CategoryCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    # Auto-generate code from name using pinyin if not provided
    code = body.code
    if not code:
        code = "_".join(lazy_pinyin(body.name.strip()))
        if not code:
            code = "unknown"
        # Ensure uniqueness
        base_code = code
        suffix = 2
        while (await session.execute(select(Category).where(Category.code == code))).scalar_one_or_none():
            code = f"{base_code}_{suffix}"
            suffix += 1
    elif (await session.execute(select(Category).where(Category.code == code))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分类编码已存在")

    data = body.model_dump()
    data["code"] = code
    category = Category(**data)
    session.add(category)
    await session.flush()
    return to_category_response(category)


@router.put("/{category_id}", response_model=CategoryResponse, summary="更新分类",
            dependencies=[Depends(require_admin())])
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await session.flush()
    video_counts = await get_category_video_counts(session, [category.id])
    return to_category_response(category, video_count=video_counts.get(category.id, 0))


@router.delete("/{category_id}", response_model=MessageResponse, summary="删除分类",
               dependencies=[Depends(require_admin())])
async def delete_category(
    category_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    children = (
        await session.execute(select(Category).where(Category.parent_id == category_id))
    ).scalars().all()
    if children:
        raise HTTPException(status_code=400, detail="该分类下有子分类，无法删除")

    video_count = (
        await session.execute(select(func.count()).select_from(Video).where(Video.category_id == category_id))
    ).scalar() or 0
    if video_count:
        raise HTTPException(status_code=400, detail="该产品分类下已有视频，无法删除")

    category.is_active = False
    await session.flush()
    return MessageResponse(message="分类已停用")
