"""User management endpoints (admin)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete

from app.core.dependencies import CurrentUserDep, SessionDep, require_role
from app.core.security import hash_password
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import (
    UserBatchImport,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(dependencies=[Depends(require_role("super_admin", "training_admin"))])


@router.get("/", response_model=PaginatedResponse[UserResponse], summary="用户列表")
async def list_users(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    keyword: str | None = None,
    store_id: int | None = None,
):
    """Paginated user list with optional filters."""
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if keyword:
        query = query.where(
            (User.username.like(f"%{keyword}%"))
            | (User.real_name.like(f"%{keyword}%"))
            | (User.phone.like(f"%{keyword}%"))
        )
    if store_id is not None:
        query = query.where(User.store_id == store_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Fetch page
    query = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    users = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        items=[UserResponse.model_validate(u) for u in users],
    )


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Get a single user by ID."""
    db_user = await session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse.model_validate(db_user)


@router.post("/", response_model=UserResponse, status_code=201, summary="创建用户")
async def create_user(
    body: UserCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Create a new user."""
    # Check duplicate username
    existing = (
        await session.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    existing_phone = (
        await session.execute(select(User).where(User.phone == body.phone))
    ).scalar_one_or_none()
    if existing_phone:
        raise HTTPException(status_code=400, detail="手机号已存在")

    db_user = User(
        username=body.username,
        phone=body.phone,
        password_hash=hash_password(body.password),
        real_name=body.real_name,
        role=body.role,
        store_id=body.store_id,
        is_active=body.is_active,
        remark=body.remark,
    )
    session.add(db_user)
    await session.flush()
    return UserResponse.model_validate(db_user)


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
async def update_user(
    user_id: int,
    body: UserUpdate,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Update an existing user."""
    db_user = await session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    await session.flush()
    return UserResponse.model_validate(db_user)


@router.delete("/{user_id}", response_model=MessageResponse, summary="删除用户")
async def delete_user(
    user_id: int,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Delete a user (soft-deactivate)."""
    db_user = await session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db_user.is_active = False
    await session.flush()
    return MessageResponse(message="用户已禁用")


@router.post("/batch-import", response_model=MessageResponse, summary="批量导入用户")
async def batch_import_users(
    body: UserBatchImport,
    session: SessionDep,
    user: CurrentUserDep,
):
    """Batch import users from a list."""
    created_count = 0
    for user_data in body.users:
        # Skip duplicates
        existing = (
            await session.execute(
                select(User).where(
                    (User.username == user_data.username) | (User.phone == user_data.phone)
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue

        db_user = User(
            username=user_data.username,
            phone=user_data.phone,
            password_hash=hash_password(user_data.password),
            real_name=user_data.real_name,
            role=user_data.role,
            store_id=user_data.store_id,
            is_active=user_data.is_active,
            remark=user_data.remark,
        )
        session.add(db_user)
        created_count += 1

    await session.flush()
    return MessageResponse(message=f"成功导入 {created_count} 个用户")
