"""Security module for authentication and authorization."""

from backend.app.core.security.jwt import (
    TokenPayload,
    TokenPair,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    verify_token,
)
from backend.app.core.security.password import (
    hash_password,
    verify_password,
    needs_rehash,
)
from backend.app.core.security.rbac import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_any_role,
    require_admin,
    require_salon_owner,
    require_professional,
    require_client,
    require_staff,
    require_professional_or_staff,
)

__all__ = [
    # JWT
    "TokenPayload",
    "TokenPair",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "verify_token",
    # Password
    "hash_password",
    "verify_password",
    "needs_rehash",
    # RBAC
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_any_role",
    "require_admin",
    "require_salon_owner",
    "require_professional",
    "require_client",
    "require_staff",
    "require_professional_or_staff",
]
