"""Authentication endpoints: login, refresh, me."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    body: LoginRequest,
    session: SessionDep,
):
    """Authenticate user by username/phone and password, return JWT token."""
    from sqlalchemy import select

    # Support login by username or phone
    stmt = select(User).where(
        (User.username == body.username) | (User.phone == body.username)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # Update last_login
    from datetime import datetime, timezone
    user.last_login = datetime.now(timezone.utc)
    await session.flush()

    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(
    user: CurrentUserDep,
):
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(user)


@router.post("/change-password", summary="修改密码")
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUserDep,
    session: SessionDep,
):
    """Change the current user's password."""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码不正确",
        )

    user.password_hash = hash_password(body.new_password)
    await session.flush()
    return {"message": "密码修改成功"}
