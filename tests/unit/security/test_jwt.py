"""Unit tests for JWT token utilities."""

from datetime import timedelta, datetime, UTC

import pytest
from jose import jwt, JWTError

from backend.app.core.config import settings
from backend.app.core.security.jwt import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    verify_token,
)


class TestCreateAccessToken:
    """Tests for create_access_token function."""

    def test_create_access_token_returns_string(self):
        """Test that create_access_token returns a string."""
        token = create_access_token(user_id=1, role="client")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_valid_jwt(self):
        """Test that created token is a valid JWT."""
        token = create_access_token(user_id=1, role="client")

        # Decode without verification to check structure
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert "sub" in decoded
        assert "exp" in decoded
        assert "type" in decoded
        assert "role" in decoded

    def test_create_access_token_correct_payload(self):
        """Test that access token contains correct payload."""
        user_id = 42
        role = "admin"

        token = create_access_token(user_id=user_id, role=role)

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert decoded["sub"] == str(user_id)
        assert decoded["type"] == "access"
        assert decoded["role"] == role

    def test_create_access_token_with_custom_expiration(self):
        """Test creating access token with custom expiration."""
        user_id = 1
        role = "client"
        custom_delta = timedelta(minutes=5)

        token = create_access_token(
            user_id=user_id,
            role=role,
            expires_delta=custom_delta,
        )

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Check that expiration is approximately correct
        exp_time = datetime.fromtimestamp(decoded["exp"], UTC)
        now = datetime.now(UTC)
        time_diff = (exp_time - now).total_seconds()

        # Should be around 5 minutes (300 seconds), allow 10 second margin
        assert 290 <= time_diff <= 310

    def test_create_access_token_with_different_roles(self):
        """Test creating access tokens with different roles."""
        user_id = 1
        roles = ["admin", "client", "professional", "salon_owner"]

        for role in roles:
            token = create_access_token(user_id=user_id, role=role)
            decoded = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            assert decoded["role"] == role

    def test_create_access_token_different_users(self):
        """Test that tokens for different users are different."""
        token1 = create_access_token(user_id=1, role="client")
        token2 = create_access_token(user_id=2, role="client")

        assert token1 != token2


class TestCreateRefreshToken:
    """Tests for create_refresh_token function."""

    def test_create_refresh_token_returns_string(self):
        """Test that create_refresh_token returns a string."""
        token = create_refresh_token(user_id=1)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_correct_payload(self):
        """Test that refresh token contains correct payload."""
        user_id = 42

        token = create_refresh_token(user_id=user_id)

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert decoded["sub"] == str(user_id)
        assert decoded["type"] == "refresh"
        assert "role" not in decoded  # Refresh tokens don't have role

    def test_create_refresh_token_with_custom_expiration(self):
        """Test creating refresh token with custom expiration."""
        user_id = 1
        custom_delta = timedelta(days=14)

        token = create_refresh_token(
            user_id=user_id,
            expires_delta=custom_delta,
        )

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Check that expiration is approximately correct
        exp_time = datetime.fromtimestamp(decoded["exp"], UTC)
        now = datetime.now(UTC)
        time_diff_days = (exp_time - now).total_seconds() / 86400

        # Should be around 14 days
        assert 13.9 <= time_diff_days <= 14.1

    def test_create_refresh_token_longer_expiration_than_access(self):
        """Test that refresh token has longer expiration than access token."""
        user_id = 1

        access_token = create_access_token(user_id=user_id, role="client")
        refresh_token = create_refresh_token(user_id=user_id)

        access_decoded = jwt.decode(
            access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        refresh_decoded = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert refresh_decoded["exp"] > access_decoded["exp"]


class TestCreateTokenPair:
    """Tests for create_token_pair function."""

    def test_create_token_pair_returns_dict(self):
        """Test that create_token_pair returns a dictionary."""
        result = create_token_pair(user_id=1, role="client")

        assert isinstance(result, dict)
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result

    def test_create_token_pair_tokens_are_different(self):
        """Test that access and refresh tokens are different."""
        result = create_token_pair(user_id=1, role="client")

        assert result["access_token"] != result["refresh_token"]

    def test_create_token_pair_token_type_bearer(self):
        """Test that token_type is 'bearer'."""
        result = create_token_pair(user_id=1, role="client")

        assert result["token_type"] == "bearer"

    def test_create_token_pair_access_token_has_role(self):
        """Test that access token from pair has role."""
        role = "admin"
        result = create_token_pair(user_id=1, role=role)

        access_decoded = jwt.decode(
            result["access_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert access_decoded["role"] == role

    def test_create_token_pair_refresh_token_no_role(self):
        """Test that refresh token from pair doesn't have role."""
        result = create_token_pair(user_id=1, role="admin")

        refresh_decoded = jwt.decode(
            result["refresh_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert "role" not in refresh_decoded


class TestVerifyToken:
    """Tests for verify_token function."""

    def test_verify_token_valid_access_token(self):
        """Test verifying a valid access token."""
        user_id = 42
        role = "client"
        token = create_access_token(user_id=user_id, role=role)

        payload = verify_token(token, token_type="access")

        assert isinstance(payload, TokenPayload)
        assert payload.sub == str(user_id)
        assert payload.type == "access"
        assert payload.role == role

    def test_verify_token_valid_refresh_token(self):
        """Test verifying a valid refresh token."""
        user_id = 42
        token = create_refresh_token(user_id=user_id)

        payload = verify_token(token, token_type="refresh")

        assert isinstance(payload, TokenPayload)
        assert payload.sub == str(user_id)
        assert payload.type == "refresh"
        assert payload.role is None

    def test_verify_token_wrong_type(self):
        """Test verifying token with wrong expected type."""
        token = create_access_token(user_id=1, role="client")

        with pytest.raises(JWTError) as exc_info:
            verify_token(token, token_type="refresh")

        assert "Invalid token type" in str(exc_info.value)

    def test_verify_token_expired(self):
        """Test verifying an expired token."""
        # Create token that expires immediately
        token = create_access_token(
            user_id=1,
            role="client",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(JWTError) as exc_info:
            verify_token(token, token_type="access")

        assert "Token verification failed" in str(exc_info.value)

    def test_verify_token_invalid_signature(self):
        """Test verifying token with invalid signature."""
        token = create_access_token(user_id=1, role="client")

        # Tamper with the token
        tampered_token = token[:-10] + "tampered123"

        with pytest.raises(JWTError):
            verify_token(tampered_token, token_type="access")

    def test_verify_token_malformed(self):
        """Test verifying a malformed token."""
        malformed_token = "not.a.valid.jwt.token"

        with pytest.raises(JWTError):
            verify_token(malformed_token, token_type="access")

    def test_verify_token_empty_string(self):
        """Test verifying an empty string token."""
        with pytest.raises(JWTError):
            verify_token("", token_type="access")


class TestTokenPayload:
    """Tests for TokenPayload model."""

    def test_token_payload_creation(self):
        """Test creating TokenPayload instance."""
        payload = TokenPayload(
            sub="123",
            exp=1234567890,
            type="access",
            role="admin",
        )

        assert payload.sub == "123"
        assert payload.exp == 1234567890
        assert payload.type == "access"
        assert payload.role == "admin"

    def test_token_payload_optional_role(self):
        """Test TokenPayload with optional role field."""
        payload = TokenPayload(
            sub="123",
            exp=1234567890,
            type="refresh",
        )

        assert payload.sub == "123"
        assert payload.role is None


class TestTokenIntegration:
    """Integration tests for JWT token workflow."""

    def test_complete_authentication_flow(self):
        """Test complete authentication token flow."""
        user_id = 42
        role = "client"

        # 1. User logs in, receives token pair
        tokens = create_token_pair(user_id=user_id, role=role)

        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # 2. User makes authenticated request with access token
        access_payload = verify_token(tokens["access_token"], token_type="access")

        assert int(access_payload.sub) == user_id
        assert access_payload.role == role

        # 3. Access token expires, use refresh token to get new access token
        refresh_payload = verify_token(tokens["refresh_token"], token_type="refresh")

        assert int(refresh_payload.sub) == user_id

        # 4. Generate new access token from refresh token
        new_access_token = create_access_token(
            user_id=int(refresh_payload.sub),
            role=role,
        )

        new_access_payload = verify_token(new_access_token, token_type="access")
        assert int(new_access_payload.sub) == user_id

    def test_token_refresh_workflow(self):
        """Test token refresh workflow."""
        user_id = 1
        role = "admin"

        # Initial tokens
        initial_tokens = create_token_pair(user_id=user_id, role=role)

        # Verify refresh token
        refresh_payload = verify_token(
            initial_tokens["refresh_token"],
            token_type="refresh",
        )

        # Create new access token using refresh token payload
        new_access_token = create_access_token(
            user_id=int(refresh_payload.sub),
            role=role,
        )

        # Verify new access token
        new_payload = verify_token(new_access_token, token_type="access")

        assert int(new_payload.sub) == user_id
        assert new_payload.role == role
        assert new_payload.type == "access"

    def test_access_token_cannot_be_used_as_refresh(self):
        """Test that access token cannot be used for refresh."""
        user_id = 1
        role = "client"

        tokens = create_token_pair(user_id=user_id, role=role)

        # Try to use access token as refresh token
        with pytest.raises(JWTError) as exc_info:
            verify_token(tokens["access_token"], token_type="refresh")

        assert "Invalid token type" in str(exc_info.value)

    def test_refresh_token_cannot_be_used_as_access(self):
        """Test that refresh token cannot be used for access."""
        user_id = 1
        role = "client"

        tokens = create_token_pair(user_id=user_id, role=role)

        # Try to use refresh token as access token
        with pytest.raises(JWTError) as exc_info:
            verify_token(tokens["refresh_token"], token_type="access")

        assert "Invalid token type" in str(exc_info.value)
