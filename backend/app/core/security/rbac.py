"""Role-Based Access Control (RBAC) dependencies and utilities."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.jwt import verify_token
from backend.app.db.models.user import User, UserRole
from backend.app.db.repositories.user import UserRepository
from backend.app.db.session import get_db

# HTTP Bearer token scheme for Authorization header
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        db: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: 401 if token is invalid or user not found
        HTTPException: 403 if user is inactive
    """
    token = credentials.credentials

    # Verify and decode JWT token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.sub
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    repo = UserRepository(db)
    user = await repo.get_by_id(int(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (already verified in get_current_user).

    This is an alias dependency for clarity in endpoint signatures.
    """
    return current_user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get current authenticated user from JWT token if provided.

    Returns None if no token is provided or if token is invalid.
    Use this for endpoints that should be accessible both authenticated
    and unauthenticated, but may behave differently based on auth status.

    Args:
        credentials: HTTP Authorization credentials (Bearer token), optional
        db: Database session

    Returns:
        User | None: Current authenticated user or None if not authenticated
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials

        # Verify and decode JWT token
        payload = verify_token(token, token_type="access")
        if not payload:
            return None

        user_id = payload.sub
        if not user_id:
            return None

        # Get user from database
        repo = UserRepository(db)
        user = await repo.get_by_id(int(user_id))

        if not user or not user.is_active:
            return None

        return user

    except Exception:
        # Silently fail and return None for optional authentication
        return None


def require_role(required_role: UserRole) -> Callable:
    """
    Create a dependency that requires a specific user role.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...

    Args:
        required_role: The required user role

    Returns:
        Dependency function that validates user role
    """

    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}",
            )
        return current_user

    return check_role


def require_any_role(*allowed_roles: UserRole) -> Callable:
    """
    Create a dependency that requires any of the specified roles.

    Usage:
        @router.get("/staff")
        async def staff_endpoint(
            user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SALON_OWNER))
        ):
            ...

    Args:
        allowed_roles: Tuple of allowed user roles

    Returns:
        Dependency function that validates user has one of the allowed roles
    """

    async def check_roles(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            roles_str = ", ".join(role.value for role in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {roles_str}",
            )
        return current_user

    return check_roles


# Convenience dependencies for common role checks
require_admin = require_role(UserRole.ADMIN)
require_salon_owner = require_role(UserRole.SALON_OWNER)
require_professional = require_role(UserRole.PROFESSIONAL)
require_client = require_role(UserRole.CLIENT)

# Staff access (admin or salon owner)
require_staff = require_any_role(UserRole.ADMIN, UserRole.SALON_OWNER)

# Professional or staff access
require_professional_or_staff = require_any_role(
    UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.PROFESSIONAL
)


__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    "require_role",
    "require_any_role",
    "require_admin",
    "require_salon_owner",
    "require_professional",
    "require_client",
    "require_staff",
    "require_professional_or_staff",
]
