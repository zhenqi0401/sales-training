"""Authentication endpoints: login, refresh, me."""

from datetime import datetime, timedelta, timezone
import logging
import random
import re

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    ApiResponse,
    ChangePasswordRequest,
    InitPasswordRequest,
    LoginRequest,
    LoginTokenPayload,
    PhoneLoginRequest,
    RefreshTokenRequest,
    SmsCodeRequest,
    TokenResponse,
    TrainingTokenPayload,
    TrainingUserResponse,
    UserResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

SMS_CODE_TTL_SECONDS = 300
SMS_CODE_RESEND_SECONDS = 60
DEV_SMS_CODE = "123456"
_sms_codes: dict[str, dict[str, datetime | str]] = {}


def _get_user_must_change_password(user: User) -> bool:
    return bool(getattr(user, "must_change_password", False))


def _set_user_must_change_password(user: User, value: bool) -> None:
    if hasattr(user, "must_change_password"):
        setattr(user, "must_change_password", value)


def _to_training_user(user: User) -> TrainingUserResponse:
    join_date = user.created_at.date().isoformat() if user.created_at else ""
    return TrainingUserResponse(
        id=user.id,
        name=user.real_name or user.username,
        phone=user.phone,
        avatar=user.avatar or "",
        storeName="",
        joinDate=join_date,
        level=1,
        point=0,
        mustChangePassword=_get_user_must_change_password(user),
        role=user.role,
    )


def _create_training_token_response(user: User) -> ApiResponse:
    token = create_access_token(data={"sub": str(user.id), "role": user.role, "tokenType": "access"})
    refresh_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "tokenType": "refresh"},
        expires_delta=timedelta(days=30),
    )
    payload = TrainingTokenPayload(
        token=token,
        refreshToken=refresh_token,
        user=_to_training_user(user),
    )
    return ApiResponse(message="登录成功", data=payload.model_dump())


async def _get_user_from_refresh_token(refresh_token: str, session: SessionDep) -> User:
    payload = decode_access_token(refresh_token)
    if payload is None or payload.get("tokenType") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def _cleanup_sms_codes(now: datetime) -> None:
    expired_phones = [
        phone for phone, item in _sms_codes.items()
        if item["expires_at"] <= now
    ]
    for phone in expired_phones:
        _sms_codes.pop(phone, None)


async def _send_sms_code(phone: str, code: str) -> None:
    """Placeholder SMS sender. Replace this with an SMS provider integration."""
    logger.info("Training login SMS code for %s is %s", phone, code)


@router.post("/login", response_model=ApiResponse, summary="User login")
async def login(
    body: LoginRequest,
    session: SessionDep,
):
    """Authenticate user by username/phone and password, return JWT token."""
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
            detail="账号已被禁用",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    user.last_login = datetime.now(timezone.utc)
    await session.flush()

    # 培训端用户（sales/student）返回含 refreshToken + mustChangePassword 的格式
    if user.role in ("sales", "student"):
        return _create_training_token_response(user)

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    payload = LoginTokenPayload(
        token=token,
        user=UserResponse.model_validate(user),
    )
    return ApiResponse(message="登录成功", data=payload.model_dump())


@router.post("/send-code", response_model=ApiResponse, summary="Send SMS code")
async def send_code(
    body: SmsCodeRequest,
    session: SessionDep,
):
    """Send an SMS verification code for student phone login."""
    phone = body.phone.strip()
    if not re.fullmatch(r"1[3-9]\d{9}", phone):
        raise HTTPException(status_code=400, detail="请输入正确的手机号")

    user = (
        await session.execute(select(User).where(User.phone == phone))
    ).scalar_one_or_none()
    if user is None or user.role not in ("sales", "student"):
        raise HTTPException(status_code=404, detail="培训账号不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    now = datetime.now(timezone.utc)
    _cleanup_sms_codes(now)
    existing = _sms_codes.get(phone)
    if existing and existing["sent_at"] + timedelta(seconds=SMS_CODE_RESEND_SECONDS) > now:
        raise HTTPException(status_code=429, detail="验证码发送过于频繁，请稍后再试")

    code = DEV_SMS_CODE if DEV_SMS_CODE else f"{random.randint(0, 999999):06d}"
    _sms_codes[phone] = {
        "code": code,
        "sent_at": now,
        "expires_at": now + timedelta(seconds=SMS_CODE_TTL_SECONDS),
    }
    await _send_sms_code(phone, code)
    return ApiResponse(message="验证码已发送")


@router.post("/phone-login", response_model=ApiResponse, summary="Phone code login")
async def phone_login(
    body: PhoneLoginRequest,
    session: SessionDep,
):
    """Authenticate a student by phone and SMS verification code."""
    phone = body.phone.strip()
    code = body.code.strip()
    now = datetime.now(timezone.utc)
    _cleanup_sms_codes(now)

    sms_item = _sms_codes.get(phone)
    if not sms_item or sms_item["expires_at"] <= now or sms_item["code"] != code:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user = (
        await session.execute(select(User).where(User.phone == phone))
    ).scalar_one_or_none()
    if user is None or user.role not in ("sales", "student"):
        raise HTTPException(status_code=404, detail="培训账号不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    _sms_codes.pop(phone, None)
    user.last_login = now
    await session.flush()
    return _create_training_token_response(user)


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(
    user: CurrentUserDep,
):
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(user)


@router.post("/change-password", summary="Change password")
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
    _set_user_must_change_password(user, False)
    await session.flush()
    return {"message": "密码修改成功"}


@router.post("/init-password", response_model=ApiResponse, summary="Set initial password")
async def init_password(
    body: InitPasswordRequest,
    user: CurrentUserDep,
    session: SessionDep,
):
    """Set a new password for users that must change password after SMS login."""
    user.password_hash = hash_password(body.new_password)
    _set_user_must_change_password(user, False)
    await session.flush()
    return ApiResponse(message="密码设置成功", data=_to_training_user(user).model_dump())


@router.post("/refresh", response_model=ApiResponse, summary="Refresh token")
async def refresh_token(
    body: RefreshTokenRequest,
    session: SessionDep,
):
    """Return a fresh access token for the current authenticated user."""
    user = await _get_user_from_refresh_token(body.refresh_token, session)
    return _create_training_token_response(user)


@router.get("/user-info", response_model=ApiResponse, summary="Get training user info")
async def get_user_info(
    user: CurrentUserDep,
):
    """Return the currently authenticated user in training-web shape."""
    return ApiResponse(data=_to_training_user(user).model_dump())


@router.post("/logout", response_model=ApiResponse, summary="Logout")
async def logout():
    """Stateless JWT logout endpoint for frontend compatibility."""
    return ApiResponse(message="已退出登录")
