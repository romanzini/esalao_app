"""Authentication endpoints (register, login, refresh)."""

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_token_pair,
    verify_token,
)
from backend.app.db.repositories.user import UserRepository
from backend.app.db.models.user import UserRole
from backend.app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description=(
        "Create a new user account and return authentication tokens. "
        "Email must be unique and password must be at least 8 characters."
    ),
)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user and return access tokens."""
    user_repo = UserRepository(db)

    # Check if user already exists
    if await user_repo.exists_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Create user
    user = await user_repo.create(
        email=user_data.email,
        password_hash=password_hash,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=UserRole.CLIENT,  # Default role for registration
    )

    # Generate tokens
    tokens = create_token_pair(user.id, user.role.value)

    return TokenResponse(**tokens)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user",
    description=(
        "Authenticate user with email and password. "
        "Returns access and refresh tokens on success."
    ),
)
async def login(
    credentials: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return access tokens."""
    user_repo = UserRepository(db)

    # Get user by email
    user = await user_repo.get_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Update last login timestamp
    await user_repo.update_last_login(user.id)

    # Generate tokens
    tokens = create_token_pair(user.id, user.role.value)

    return TokenResponse(**tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token. "
        "Refresh token rotation: returns new refresh token as well."
    ),
)
async def refresh(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = verify_token(token_data.refresh_token, token_type="refresh")

        # Get user to verify they still exist and are active
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(int(payload.sub))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # Generate new token pair (refresh token rotation)
        tokens = create_token_pair(user.id, user.role.value)

        return TokenResponse(**tokens)

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
