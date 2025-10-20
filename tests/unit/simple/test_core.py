"""Simple tests for core functionality."""

import pytest
from datetime import datetime, timezone

from backend.app.core.security.password import hash_password, verify_password
from backend.app.core.security.jwt import create_access_token, verify_token
from backend.app.db.models.user import UserRole


class TestPasswordSecurity:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test password hashing and verification cycle."""
        password = "test_password_123"

        # Hash password
        hashed = hash_password(password)

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Verify incorrect password
        assert verify_password("wrong_password", hashed) is False

    def test_password_hash_not_empty(self):
        """Test that password hash is generated."""
        password = "test_password"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password


class TestJWTSecurity:
    """Test JWT token functionality."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_data = {"sub": "1", "email": "test@example.com"}

        token = create_access_token(data=user_data)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT tokens have 3 parts separated by dots
        assert token.count('.') == 2

    def test_verify_valid_token(self):
        """Test verification of valid token."""
        user_data = {"sub": "1", "email": "test@example.com"}

        token = create_access_token(data=user_data)
        payload = verify_token(token)

        assert payload is not None
        assert payload.get("sub") == "1"
        assert payload.get("email") == "test@example.com"


class TestUserRole:
    """Test user role enum."""

    def test_user_roles_exist(self):
        """Test that all expected user roles exist."""
        assert hasattr(UserRole, 'CLIENT')
        assert hasattr(UserRole, 'PROFESSIONAL')
        assert hasattr(UserRole, 'SALON_OWNER')
        assert hasattr(UserRole, 'ADMIN')

    def test_user_role_values(self):
        """Test user role string values."""
        assert UserRole.CLIENT.value == "CLIENT"
        assert UserRole.PROFESSIONAL.value == "PROFESSIONAL"
        assert UserRole.SALON_OWNER.value == "SALON_OWNER"
        assert UserRole.ADMIN.value == "ADMIN"


class TestBasicTypes:
    """Test basic type handling."""

    def test_datetime_creation(self):
        """Test datetime creation with timezone."""
        now = datetime.now(timezone.utc)

        assert isinstance(now, datetime)
        assert now.tzinfo is timezone.utc

    def test_string_operations(self):
        """Test basic string operations."""
        test_str = "Hello World"

        assert test_str.lower() == "hello world"
        assert test_str.upper() == "HELLO WORLD"
        assert len(test_str) == 11

    def test_list_operations(self):
        """Test basic list operations."""
        test_list = [1, 2, 3, 4, 5]

        assert len(test_list) == 5
        assert test_list[0] == 1
        assert test_list[-1] == 5
        assert 3 in test_list

    def test_dict_operations(self):
        """Test basic dictionary operations."""
        test_dict = {"key1": "value1", "key2": "value2"}

        assert len(test_dict) == 2
        assert test_dict["key1"] == "value1"
        assert "key1" in test_dict
        assert test_dict.get("key3", "default") == "default"


class TestConfigValues:
    """Test configuration access."""

    def test_settings_import(self):
        """Test that settings can be imported."""
        from backend.app.core.config import settings

        assert settings is not None
        assert hasattr(settings, 'PROJECT_NAME')
        assert hasattr(settings, 'VERSION')

    def test_project_name(self):
        """Test project name setting."""
        from backend.app.core.config import settings

        assert settings.PROJECT_NAME == "eSalão Platform"
        assert isinstance(settings.VERSION, str)


class TestModelImports:
    """Test that models can be imported without error."""

    def test_user_model_import(self):
        """Test user model import."""
        from backend.app.db.models.user import User, UserRole

        assert User is not None
        assert UserRole is not None

    def test_service_model_import(self):
        """Test service model import."""
        from backend.app.db.models.service import Service

        assert Service is not None

    def test_booking_model_import(self):
        """Test booking model import."""
        from backend.app.db.models.booking import Booking, BookingStatus

        assert Booking is not None
        assert BookingStatus is not None
