"""User / auth Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """User login payload."""

    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserCreate(BaseModel):
    """Create a new user."""

    username: str = Field(..., min_length=2, max_length=64)
    phone: str = Field(..., min_length=11, max_length=20)
    password: str = Field(..., min_length=6, max_length=128)
    real_name: Optional[str] = ""
    role: str = "student"
    store_id: Optional[int] = None
    is_active: bool = True
    remark: Optional[str] = ""


class UserUpdate(BaseModel):
    """Update user fields."""

    username: Optional[str] = None
    phone: Optional[str] = None
    real_name: Optional[str] = None
    role: Optional[str] = None
    store_id: Optional[int] = None
    is_active: Optional[bool] = None
    remark: Optional[str] = None


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


class UserBatchImport(BaseModel):
    """Batch import users payload."""

    users: list[UserCreate]


class ChangePasswordRequest(BaseModel):
    """Change password payload."""

    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)
