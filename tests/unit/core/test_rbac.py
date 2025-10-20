"""Tests for RBAC (Role-Based Access Control) functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.core.security.rbac import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_any_role,
    security,
    security_optional
)
from backend.app.db.models.user import User, UserRole
from backend.app.core.security.jwt import TokenPayload


class TestRBACSecuritySchemes:
    """Test RBAC security schemes."""

    def test_security_scheme_exists(self):
        """Test that security schemes are defined."""
        assert security is not None
        assert security_optional is not None

    def test_security_scheme_properties(self):
        """Test security scheme properties."""
        from fastapi.security import HTTPBearer

        assert isinstance(security, HTTPBearer)
        assert isinstance(security_optional, HTTPBearer)

        # Optional security should not auto-error
        assert security_optional.auto_error is False


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @pytest.fixture
    def mock_credentials(self):
        """Mock HTTP authorization credentials."""
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token_123"
        return credentials

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.is_active = True
        user.role = UserRole.CLIENT
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_credentials, mock_user):
        """Test successful user retrieval."""
        mock_db = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = mock_user

        # Mock token verification
        mock_payload = MagicMock(spec=TokenPayload)
        mock_payload.sub = "1"

        with patch('backend.app.core.security.rbac.verify_token', return_value=mock_payload), \
             patch('backend.app.core.security.rbac.UserRepository', return_value=mock_user_repo):

            result = await get_current_user(mock_credentials, mock_db)

            assert result == mock_user
            mock_user_repo.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_credentials):
        """Test user retrieval with invalid token."""
        mock_db = AsyncMock()

        # Mock token verification failure
        with patch('backend.app.core.security.rbac.verify_token', return_value=None):

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)

            assert exc_info.value.status_code == 401
            assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_no_user_id_in_token(self, mock_credentials):
        """Test user retrieval when token has no user ID."""
        mock_db = AsyncMock()

        # Mock token with no sub
        mock_payload = MagicMock(spec=TokenPayload)
        mock_payload.sub = None

        with patch('backend.app.core.security.rbac.verify_token', return_value=mock_payload):

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, mock_credentials):
        """Test user retrieval when user doesn't exist."""
        mock_db = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = None

        # Mock token verification
        mock_payload = MagicMock(spec=TokenPayload)
        mock_payload.sub = "999"

        with patch('backend.app.core.security.rbac.verify_token', return_value=mock_payload), \
             patch('backend.app.core.security.rbac.UserRepository', return_value=mock_user_repo):

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail


class TestGetCurrentActiveUser:
    """Test get_current_active_user dependency."""

    @pytest.fixture
    def mock_active_user(self):
        """Mock active user object."""
        user = MagicMock(spec=User)
        user.id = 1
        user.is_active = True
        return user

    @pytest.fixture
    def mock_inactive_user(self):
        """Mock inactive user object."""
        user = MagicMock(spec=User)
        user.id = 1
        user.is_active = False
        return user

    def test_get_current_active_user_success(self, mock_active_user):
        """Test successful active user retrieval."""
        result = get_current_active_user(mock_active_user)
        assert result == mock_active_user

    def test_get_current_active_user_inactive(self, mock_inactive_user):
        """Test active user retrieval with inactive user."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_active_user(mock_inactive_user)

        assert exc_info.value.status_code == 403
        assert "Account is inactive" in exc_info.value.detail


class TestRequireRoles:
    """Test require_roles decorator functionality."""

    @pytest.fixture
    def mock_client_user(self):
        """Mock client user."""
        user = MagicMock(spec=User)
        user.role = UserRole.CLIENT
        return user

    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user."""
        user = MagicMock(spec=User)
        user.role = UserRole.ADMIN
        return user

    def test_require_role_single_role_success(self, mock_client_user):
        """Test role requirement with matching single role."""
        dependency = require_role(UserRole.CLIENT)

        # Should not raise exception
        result = dependency(mock_client_user)
        assert result == mock_client_user

    def test_require_any_role_multiple_roles_success(self, mock_admin_user):
        """Test role requirement with matching role in multiple allowed."""
        dependency = require_any_role(UserRole.CLIENT, UserRole.ADMIN)

        # Should not raise exception
        result = dependency(mock_admin_user)
        assert result == mock_admin_user

    def test_require_role_unauthorized(self, mock_client_user):
        """Test role requirement with unauthorized role."""
        dependency = require_role(UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_client_user)

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail


class TestUserRoleEnum:
    """Test UserRole enum functionality."""

    def test_user_roles_exist(self):
        """Test that all expected user roles exist."""
        assert hasattr(UserRole, 'CLIENT')
        assert hasattr(UserRole, 'PROFESSIONAL')
        assert hasattr(UserRole, 'SALON_OWNER')
        assert hasattr(UserRole, 'ADMIN')

    def test_user_role_comparison(self):
        """Test user role comparison."""
        client1 = UserRole.CLIENT
        client2 = UserRole.CLIENT
        admin = UserRole.ADMIN

        assert client1 == client2
        assert client1 != admin

    def test_user_role_in_list(self):
        """Test user role membership in lists."""
        allowed_roles = [UserRole.CLIENT, UserRole.PROFESSIONAL]

        assert UserRole.CLIENT in allowed_roles
        assert UserRole.PROFESSIONAL in allowed_roles
        assert UserRole.ADMIN not in allowed_roles


class TestRBACIntegration:
    """Test RBAC integration scenarios."""

    def test_role_hierarchy_concept(self):
        """Test role hierarchy conceptual validation."""
        # Test that roles can be organized hierarchically
        admin_roles = [UserRole.ADMIN]
        owner_roles = [UserRole.SALON_OWNER, UserRole.ADMIN]
        professional_roles = [UserRole.PROFESSIONAL, UserRole.SALON_OWNER, UserRole.ADMIN]
        client_roles = [UserRole.CLIENT, UserRole.PROFESSIONAL, UserRole.SALON_OWNER, UserRole.ADMIN]

        # Admin should have highest privilege level
        assert UserRole.ADMIN in admin_roles
        assert UserRole.ADMIN in owner_roles
        assert UserRole.ADMIN in professional_roles
        assert UserRole.ADMIN in client_roles

        # Client should be most restricted
        assert UserRole.CLIENT not in admin_roles
        assert UserRole.CLIENT not in owner_roles
        assert UserRole.CLIENT not in professional_roles
        assert UserRole.CLIENT in client_roles
