"""User / auth Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


class LoginRequest(BaseModel):
    """User login payload."""

    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class SmsCodeRequest(BaseModel):
    """Send SMS code payload."""

    phone: str = Field(..., min_length=11, max_length=20)


class PhoneLoginRequest(BaseModel):
    """Phone + SMS code login payload."""

    phone: str = Field(..., min_length=11, max_length=20)
    code: str = Field(..., min_length=4, max_length=8)


class RefreshTokenRequest(BaseModel):
    """Refresh token payload used by the training web app."""

    refresh_token: str = Field(..., alias="refreshToken", min_length=1)

    model_config = {"populate_by_name": True}


class TrainingTokenPayload(BaseModel):
    """Token payload used by the training web response envelope."""

    token: str
    refreshToken: str
    user: "TrainingUserResponse"


class LoginTokenPayload(BaseModel):
    """Token payload for admin-web login response envelope."""

    token: str
    refreshToken: str = ""
    user: "UserResponse"


class ApiResponse(BaseModel):
    """Frontend-compatible response envelope."""

    code: int = 200
    message: str = "success"
    data: object | None = None


class UserCreate(BaseModel):
    """Create a new user."""

    username: str = Field(..., min_length=2, max_length=64)
    phone: str = Field(..., min_length=11, max_length=20)
    password: str = Field(..., min_length=6, max_length=128)
    real_name: Optional[str] = Field(
        default="",
        validation_alias=AliasChoices("real_name", "realName"),
    )
    role: str = "student"
    store_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("store_id", "storeId"),
    )
    is_active: bool = Field(
        default=True,
        validation_alias=AliasChoices("is_active", "isActive"),
    )
    remark: Optional[str] = ""

    model_config = {"populate_by_name": True}


class UserUpdate(BaseModel):
    """Update user fields."""

    username: Optional[str] = None
    phone: Optional[str] = None
    real_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("real_name", "realName"),
    )
    role: Optional[str] = None
    store_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("store_id", "storeId"),
    )
    is_active: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("is_active", "isActive"),
    )
    remark: Optional[str] = None

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    """User read model."""

    id: int
    username: str
    phone: str
    real_name: Optional[str] = ""
    role: str
    store_id: Optional[int] = None
    avatar: Optional[str] = ""
    is_active: bool
    last_login: Optional[datetime] = None
    remark: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TrainingUserResponse(BaseModel):
    """User shape consumed by the training web app."""

    id: int
    name: str
    phone: str
    avatar: str = ""
    storeName: str = ""
    joinDate: str = ""
    level: int = 1
    point: int = 0
    mustChangePassword: bool = False
    role: str = "student"


class UserBatchImport(BaseModel):
    """Batch import users payload."""

    users: list[UserCreate]


class ChangePasswordRequest(BaseModel):
    """Change password payload."""

    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)


class InitPasswordRequest(BaseModel):
    """Set initial password after SMS login."""

    new_password: str = Field(..., min_length=6, max_length=128)
