"""JWT token utilities for authentication."""

from datetime import datetime, timedelta, UTC

from jose import jwt, JWTError
from pydantic import BaseModel

from backend.app.core.config import settings


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # Subject (user_id)
    exp: int  # Expiration timestamp
    type: str  # Token type: "access" or "refresh"
    role: str | None = None  # User role for RBAC


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def create_access_token(
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        role: User role for authorization
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "role": role,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    user_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens have longer expiration and are used to obtain
    new access tokens without re-authentication.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_token_pair(user_id: int, role: str) -> dict[str, str]:
    """
    Create both access and refresh tokens.

    Args:
        user_id: User ID to encode in tokens
        role: User role for authorization

    Returns:
        Dictionary with access_token, refresh_token, and token_type
    """
    access_token = create_access_token(user_id, role)
    refresh_token = create_refresh_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        token_payload = TokenPayload(**payload)

        # Verify token type matches expected
        if token_payload.type != token_type:
            raise JWTError(
                f"Invalid token type. Expected '{token_type}', "
                f"got '{token_payload.type}'"
            )

        return token_payload

    except JWTError as e:
        raise JWTError(f"Token verification failed: {str(e)}")
