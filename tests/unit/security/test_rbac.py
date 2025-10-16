"""Unit tests for RBAC utilities.

Note: These tests focus on testable parts of RBAC.
Full integration testing of FastAPI Depends() is covered in integration tests.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from jose import jwt

from backend.app.core.config import settings
from backend.app.core.security.rbac import get_current_user
from backend.app.db.models.user import User, UserRole


class TestGetCurrentUser:
    """Tests for get_current_user function."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token."""
        user_id = 42
        role = UserRole.CLIENT

        # Create valid token
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
            "role": role.value,
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Mock user from database
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.credentials = token

        # Mock database session
        mock_db = AsyncMock()

        # Patch UserRepository
        with patch("backend.app.core.security.rbac.UserRepository") as MockRepo:
            mock_repo_instance = Mock()
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
            MockRepo.return_value = mock_repo_instance

            # Call function
            result = await get_current_user(credentials=mock_credentials, db=mock_db)

            assert result == mock_user
            mock_repo_instance.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test that invalid token raises JWTError."""
        from jose.exceptions import JWTError

        invalid_token = "invalid.jwt.token"

        mock_credentials = Mock()
        mock_credentials.credentials = invalid_token

        mock_db = AsyncMock()

        with pytest.raises(JWTError):
            await get_current_user(credentials=mock_credentials, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        """Test that expired token raises JWTError."""
        from jose.exceptions import JWTError

        # Create expired token
        payload = {
            "sub": "1",
            "exp": datetime.now(UTC) - timedelta(minutes=30),  # Expired
            "type": "access",
            "role": "client",
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        mock_credentials = Mock()
        mock_credentials.credentials = token

        mock_db = AsyncMock()

        with pytest.raises(JWTError):
            await get_current_user(credentials=mock_credentials, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self):
        """Test that non-existent user raises 401."""
        user_id = 999

        # Create valid token
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
            "role": "client",
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        mock_credentials = Mock()
        mock_credentials.credentials = token

        mock_db = AsyncMock()

        # Patch UserRepository to return None
        with patch("backend.app.core.security.rbac.UserRepository") as MockRepo:
            mock_repo_instance = Mock()
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo_instance

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_credentials, db=mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self):
        """Test that inactive user raises 403."""
        user_id = 42

        # Create valid token
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
            "role": "client",
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Mock inactive user
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.is_active = False

        mock_credentials = Mock()
        mock_credentials.credentials = token

        mock_db = AsyncMock()

        # Patch UserRepository
        with patch("backend.app.core.security.rbac.UserRepository") as MockRepo:
            mock_repo_instance = Mock()
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
            MockRepo.return_value = mock_repo_instance

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_credentials, db=mock_db)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Inactive user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_wrong_token_type(self):
        """Test that refresh token raises JWTError."""
        from jose.exceptions import JWTError

        # Create refresh token instead of access token
        payload = {
            "sub": "1",
            "exp": datetime.now(UTC) + timedelta(days=7),
            "type": "refresh",  # Wrong type
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        mock_credentials = Mock()
        mock_credentials.credentials = token

        mock_db = AsyncMock()

        with pytest.raises(JWTError):
            await get_current_user(credentials=mock_credentials, db=mock_db)


class TestRoleChecking:
    """
    Tests for role checking logic.

    Note: require_role() and require_any_role() return FastAPI dependency functions
    that use Depends(). Testing these requires FastAPI dependency injection,
    which is better suited for integration tests.

    These tests verify the basic role logic that would be executed.
    """

    def test_user_roles_enum(self):
        """Test that UserRole enum has all expected roles."""
        expected_roles = ["admin", "salon_owner", "professional", "client"]

        for role_name in expected_roles:
            assert hasattr(UserRole, role_name.upper())

    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SALON_OWNER.value == "salon_owner"
        assert UserRole.PROFESSIONAL.value == "professional"
        assert UserRole.CLIENT.value == "client"


class TestRBACIntegration:
    """
    Integration tests for RBAC workflow.

    These tests verify complete flows but are simplified for unit testing.
    Full integration tests with real FastAPI app are in tests/integration/.
    """

    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self):
        """Test complete authentication flow from token to user."""
        user_id = 42
        role = UserRole.ADMIN

        # 1. Create valid access token
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
            "role": role.value,
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # 2. Mock user from database
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        # 3. Mock credentials and database
        mock_credentials = Mock()
        mock_credentials.credentials = token
        mock_db = AsyncMock()

        # 4. Patch UserRepository
        with patch("backend.app.core.security.rbac.UserRepository") as MockRepo:
            mock_repo_instance = Mock()
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
            MockRepo.return_value = mock_repo_instance

            # 5. Get current user from token
            current_user = await get_current_user(credentials=mock_credentials, db=mock_db)

            assert current_user == mock_user
            assert current_user.role == UserRole.ADMIN
            assert current_user.is_active is True

    @pytest.mark.asyncio
    async def test_authentication_flow_client_role(self):
        """Test authentication flow with client role."""
        user_id = 123
        role = UserRole.CLIENT

        # Create token
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
            "role": role.value,
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Mock user
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        mock_credentials = Mock()
        mock_credentials.credentials = token
        mock_db = AsyncMock()

        with patch("backend.app.core.security.rbac.UserRepository") as MockRepo:
            mock_repo_instance = Mock()
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
            MockRepo.return_value = mock_repo_instance

            current_user = await get_current_user(credentials=mock_credentials, db=mock_db)

            assert current_user.role == UserRole.CLIENT

    @pytest.mark.asyncio
    async def test_authentication_flow_professional_role(self):
        """Test authentication flow with professional role."""
        user_id = 456
        role = UserRole.PROFESSIONAL

        payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
            "role": role.value,
        }
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        mock_credentials = Mock()
        mock_credentials.credentials = token
        mock_db = AsyncMock()

        with patch("backend.app.core.security.rbac.UserRepository") as MockRepo:
            mock_repo_instance = Mock()
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
            MockRepo.return_value = mock_repo_instance

            current_user = await get_current_user(credentials=mock_credentials, db=mock_db)

            assert current_user.role == UserRole.PROFESSIONAL
