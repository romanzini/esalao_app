"""Unit tests for auth routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security.jwt import create_access_token, create_refresh_token
from backend.app.db.models.user import User, UserRole
from backend.app.api.v1.schemas.auth import UserRegisterRequest, UserLoginRequest


class TestAuthRoutes:
    """Test authentication routes."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Mock user instance."""
        from datetime import datetime
        user = User(
            id=1,
            email="test@example.com",
            full_name="Test User",
            role=UserRole.CLIENT,
            is_active=True,
            is_verified=True,
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$vVdKqVXq3fv/X0vp/f+/Vw$IKViXT5ZiFX+FY5nvQ4FAG3arwI6j0vZGRn3VUMEZ54"
        )
        # Set required timestamp fields
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        return user

    @pytest.fixture
    def valid_user_data(self):
        """Valid user registration data."""
        return {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "phone": "123-456-7890",
        }

    @pytest.fixture
    def valid_login_data(self):
        """Valid login data."""
        return {
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }

    @patch('backend.app.api.v1.routes.auth.UserRepository')
    @patch('backend.app.core.security.hash_password')
    @patch('backend.app.core.security.create_token_pair')
    def test_register_success(self, mock_create_tokens, mock_hash_password, mock_user_repo_class, client, valid_user_data, mock_user):
        """Test successful user registration."""
        # Mock password hashing
        mock_hash_password.return_value = "hashed_password"

        # Mock token creation
        mock_create_tokens.return_value = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "token_type": "bearer",
            "expires_in": 3600
        }

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.exists_by_email.return_value = False
        mock_repo.create.return_value = mock_user
        mock_user_repo_class.return_value = mock_repo

        # Make request
        response = client.post("/api/v1/auth/register", json=valid_user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @patch('backend.app.api.v1.routes.auth.UserRepository')
    def test_register_email_exists(self, mock_user_repo_class, client, valid_user_data):
        """Test registration with existing email."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.exists_by_email.return_value = True
        mock_user_repo_class.return_value = mock_repo

        # Make request
        response = client.post("/api/v1/auth/register", json=valid_user_data)

        # Assert
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "password": "SecurePassword123!",
            "full_name": "Test User",
        }

        response = client.post("/api/v1/auth/register", json=invalid_data)
        assert response.status_code == 422

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        weak_password_data = {
            "email": "test@example.com",
            "password": "123",
            "full_name": "Test User",
        }

        response = client.post("/api/v1/auth/register", json=weak_password_data)
        assert response.status_code == 422

    @patch('backend.app.api.v1.routes.auth.UserRepository')
    @patch('backend.app.core.security.verify_password')
    @patch('backend.app.core.security.create_token_pair')
    def test_login_success(self, mock_create_tokens, mock_verify_password, mock_user_repo_class, client, valid_login_data, mock_user):
        """Test successful login."""
        # Mock token creation
        mock_create_tokens.return_value = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "token_type": "bearer",
            "expires_in": 3600
        }

        # Mock repository and password verification
        mock_repo = AsyncMock()
        mock_repo.get_by_email.return_value = mock_user
        mock_repo.update_last_login.return_value = None
        mock_user_repo_class.return_value = mock_repo
        mock_verify_password.return_value = True

        # Make request
        response = client.post("/api/v1/auth/login", json=valid_login_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @patch('backend.app.api.v1.routes.auth.UserRepository')
    def test_login_user_not_found(self, mock_user_repo_class, client, valid_login_data):
        """Test login with non-existent user."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_email.return_value = None
        mock_user_repo_class.return_value = mock_repo

        # Make request
        response = client.post("/api/v1/auth/login", json=valid_login_data)

        # Assert
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @patch('backend.app.api.v1.routes.auth.verify_password')
    @patch('backend.app.api.v1.routes.auth.UserRepository')
    def test_login_wrong_password(self, mock_user_repo_class, mock_verify_password, client, valid_login_data, mock_user):
        """Test login with wrong password."""
        # Mock repository and password verification
        mock_repo = AsyncMock()
        mock_repo.get_by_email.return_value = mock_user
        mock_user_repo_class.return_value = mock_repo
        mock_verify_password.return_value = False

        # Make request
        response = client.post("/api/v1/auth/login", json=valid_login_data)

        # Assert
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @patch('backend.app.api.v1.routes.auth.verify_password')
    @patch('backend.app.api.v1.routes.auth.UserRepository')
    def test_login_inactive_user(self, mock_user_repo_class, mock_verify_password, client, valid_login_data, mock_user):
        """Test login with inactive user."""
        # Make user inactive
        mock_user.is_active = False

        # Mock repository and password verification
        mock_repo = AsyncMock()
        mock_repo.get_by_email.return_value = mock_user
        mock_user_repo_class.return_value = mock_repo
        mock_verify_password.return_value = True

        # Make request
        response = client.post("/api/v1/auth/login", json=valid_login_data)

        # Assert
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"]

    def test_login_invalid_data(self, client):
        """Test login with invalid request data."""
        invalid_data = {
            "email": "invalid-email",
            "password": "",
        }

        response = client.post("/api/v1/auth/login", json=invalid_data)
        assert response.status_code == 422

    @patch('backend.app.api.v1.routes.auth.verify_token')
    @patch('backend.app.api.v1.routes.auth.UserRepository')
    @patch('backend.app.core.security.create_token_pair')
    def test_refresh_token_success(self, mock_create_tokens, mock_user_repo_class, mock_verify_token, client, mock_user):
        """Test successful token refresh."""
        # Mock token verification
        mock_payload = MagicMock()
        mock_payload.sub = "1"
        mock_verify_token.return_value = mock_payload

        # Mock token creation
        mock_create_tokens.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "bearer",
            "expires_in": 3600
        }

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_user
        mock_user_repo_class.return_value = mock_repo

        # Make request
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid_refresh_token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_missing(self, client):
        """Test refresh without token."""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422

    @patch('backend.app.api.v1.routes.auth.verify_token')
    def test_refresh_token_invalid(self, mock_verify_token, client):
        """Test refresh with invalid token."""
        # Mock token verification to raise JWTError
        from jose import JWTError
        mock_verify_token.side_effect = JWTError("Invalid token")

        # Make request
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )

        # Assert
        assert response.status_code == 401

    @patch('backend.app.api.v1.routes.auth.verify_token')
    @patch('backend.app.api.v1.routes.auth.UserRepository')
    def test_refresh_token_user_not_found(self, mock_user_repo_class, mock_verify_token, client):
        """Test refresh with token for non-existent user."""
        # Mock token verification
        mock_payload = MagicMock()
        mock_payload.sub = "999"
        mock_verify_token.return_value = mock_payload

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_user_repo_class.return_value = mock_repo

        # Make request
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid_token_format"}
        )

        # Assert
        assert response.status_code == 401
