"""Tests for utility functions and helpers."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

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

    def test_password_hash_different_each_time(self):
        """Test that same password produces different hashes."""
        password = "same_password"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Different hashes due to salt
        assert hash1 != hash2

        # But both verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTSecurity:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_data = {"sub": "1", "email": "test@example.com"}

        token = create_access_token(data=user_data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self):
        """Test verification of valid token."""
        user_data = {"sub": "1", "email": "test@example.com"}

        token = create_access_token(data=user_data)
        payload = verify_token(token)

        assert payload is not None
        assert payload.get("sub") == "1"
        assert payload.get("email") == "test@example.com"

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"

        payload = verify_token(invalid_token)

        assert payload is None


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


class TestModelHelpers:
    """Test model helper functions and mixins."""

    def test_datetime_handling(self):
        """Test datetime utilities."""
        now = datetime.now(timezone.utc)

        # Basic datetime operations
        assert now.tzinfo is not None
        assert isinstance(now, datetime)

    def test_decimal_handling(self):
        """Test decimal number handling for prices."""
        price = Decimal("29.99")

        assert isinstance(price, Decimal)
        assert str(price) == "29.99"

        # Test arithmetic
        tax = price * Decimal("0.1")
        total = price + tax

        assert total == Decimal("32.989")


class TestValidationHelpers:
    """Test validation utilities."""

    def test_email_format_validation(self):
        """Test email format validation patterns."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]

        invalid_emails = [
            "invalid_email",
            "@example.com",
            "user@",
            "user space@example.com"
        ]

        # Simple regex-based validation test
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        for email in valid_emails:
            assert re.match(email_pattern, email) is not None, f"Should be valid: {email}"

        for email in invalid_emails:
            assert re.match(email_pattern, email) is None, f"Should be invalid: {email}"

    def test_phone_format_validation(self):
        """Test phone format validation patterns."""
        valid_phones = [
            "123456789",
            "11987654321",
            "+5511987654321"
        ]

        # Simple phone validation test
        for phone in valid_phones:
            # Remove non-digits
            digits_only = re.sub(r'[^\d]', '', phone)
            assert len(digits_only) >= 8, f"Phone should have at least 8 digits: {phone}"
