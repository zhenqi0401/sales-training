"""Product knowledge management endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.core.dependencies import CurrentUserDep, SessionDep
from app.models.category import Category
from app.models.product import Product
from app.schemas.common import MessageResponse, PaginatedResponse


class ProductCreate(BaseModel):
    name: str
    category_id: Optional[int] = None
    category: Optional[str] = None
    category_code: Optional[str] = None
    intro: Optional[str] = ""
    specs: Optional[dict] = None
    faq: Optional[list] = None
    compare_data: Optional[dict] = None
    sort_order: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    category: Optional[str] = None
    category_code: Optional[str] = None
    intro: Optional[str] = None
    specs: Optional[dict] = None
    faq: Optional[list] = None
    compare_data: Optional[dict] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    category_id: Optional[int] = None
    intro: Optional[str] = ""
    specs: Optional[dict] = None
    faq: Optional[list] = None
    compare_data: Optional[dict] = None
    is_active: bool
    sort_order: int
    category_code: Optional[str] = None
    category_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


router = APIRouter()


class ProductCategoryResponse(BaseModel):
    id: int
    code: str
    name: str
    count: int


def to_product_response(product: Product, category: Category | None = None) -> ProductResponse:
    """Build a product response with category display fields."""
    return ProductResponse(
        id=product.id,
        name=product.name,
        category_id=product.category_id,
        intro=product.intro,
        specs=product.specs,
        faq=product.faq,
        compare_data=product.compare_data,
        is_active=product.is_active,
        sort_order=product.sort_order,
        category_code=category.code if category else None,
        category_name=category.name if category else None,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def product_payload(body: ProductCreate | ProductUpdate, session: SessionDep) -> dict:
    """Convert product form payload into model fields."""
    data = body.model_dump(exclude_unset=True)
    category_value = data.pop("category", None) or data.pop("category_code", None)
    if data.get("category_id") is None and category_value:
        category = (
            await session.execute(
                select(Category).where(or_(Category.code == category_value, Category.name == category_value))
            )
        ).scalar_one_or_none()
        if category:
            data["category_id"] = category.id
    return data


@router.get("/", response_model=PaginatedResponse[ProductResponse], summary="产品列表")
async def list_products(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    category_id: int | None = None,
    category: str | None = None,
    brand: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
):
    """Paginated product list."""
    query = select(Product)

    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    elif category:
        category_ids = (
            await session.execute(
                select(Category.id).where(or_(Category.code == category, Category.name == category))
            )
        ).scalars().all()
        if category_ids:
            query = query.where(Product.category_id.in_(category_ids))
        else:
            query = query.where(False)
    if brand:
        query = query.where(func.json_unquote(func.json_extract(Product.specs, "$.brand")) == brand)
    if status == "draft":
        query = query.where(Product.is_active == False)
    else:
        query = query.where(Product.is_active == True)
    if keyword:
        query = query.where(
            or_(
                Product.name.like(f"%{keyword}%"),
                Product.intro.like(f"%{keyword}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Product.sort_order, Product.id).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    products = result.scalars().all()
    category_ids = [p.category_id for p in products if p.category_id is not None]
    categories = {}
    if category_ids:
        categories = {
            c.id: c
            for c in (
                await session.execute(select(Category).where(Category.id.in_(category_ids)))
            ).scalars().all()
        }

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[to_product_response(p, categories.get(p.category_id)) for p in products],
    )


@router.get("/categories", response_model=list[ProductCategoryResponse], summary="产品分类选项")
async def list_product_categories(
    session: SessionDep,
    user: CurrentUserDep,
):
    """Return product categories that currently have active content."""
    result = await session.execute(
        select(Category.id, Category.code, Category.name, func.count(Product.id))
        .join(Product, Product.category_id == Category.id)
        .where(Product.is_active == True)
        .group_by(Category.id, Category.code, Category.name)
        .order_by(Category.sort_order, Category.id)
    )
    return [
        ProductCategoryResponse(id=id_, code=code, name=name, count=count)
        for id_, code, name, count in result.all()
    ]


@router.get("/{product_id}", response_model=ProductResponse, summary="获取产品详情")
async def get_product(
    product_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    category = await session.get(Category, product.category_id) if product.category_id else None
    return to_product_response(product, category)


@router.post("/", response_model=ProductResponse, status_code=201, summary="创建产品")
async def create_product(
    body: ProductCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    product = Product(**await product_payload(body, session))
    session.add(product)
    await session.flush()
    category = await session.get(Category, product.category_id) if product.category_id else None
    return to_product_response(product, category)


@router.put("/{product_id}", response_model=ProductResponse, summary="更新产品")
async def update_product(
    product_id: int,
    body: ProductUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    update_data = await product_payload(body, session)
    for field, value in update_data.items():
        setattr(product, field, value)

    await session.flush()
    category = await session.get(Category, product.category_id) if product.category_id else None
    return to_product_response(product, category)


@router.delete("/{product_id}", response_model=MessageResponse, summary="删除产品")
async def delete_product(
    product_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    product.is_active = False
    await session.flush()
    return MessageResponse(message="产品已删除")
