"""Authentication service layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserResponse


class AuthService:
    """Handles user authentication and token management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def authenticate(self, username: str, password: str) -> TokenResponse | None:
        """Validate credentials and return a token response."""
        result = await self.session.execute(
            select(User).where(
                (User.username == username) | (User.phone == username),
                User.is_active == True,
            )
        )
        user = result.scalar_one_or_none()

        if user is None or not verify_password(password, user.password_hash):
            return None

        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )

    async def get_user_by_token(self, token: str) -> User | None:
        """Extract and validate user from a JWT token."""
        payload = decode_access_token(token)
        if payload is None:
            return None
        subject = payload.get("sub")
        if subject is None:
            return None
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            return None
        return await self.session.get(User, user_id)
