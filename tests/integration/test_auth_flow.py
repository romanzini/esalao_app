"""Integration tests for complete authentication flows.

Tests the full authentication lifecycle including:
- User registration
- Login with credentials
- Token refresh
- Access to protected endpoints
- Token expiration handling
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from backend.app.db.models.user import UserRole


class TestRegistrationFlow:
    """Tests for user registration flow."""

    @pytest.mark.asyncio
    async def test_complete_registration_flow(self, client: AsyncClient):
        """Test complete user registration and immediate login."""
        # 1. Register new user
        register_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!@#",
            "full_name": "New Test User",
            "phone": "+5511999999999",
        }

        register_response = await client.post("/api/v1/auth/register", json=register_data)

        assert register_response.status_code == status.HTTP_201_CREATED
        register_json = register_response.json()
        assert "access_token" in register_json
        assert "refresh_token" in register_json
        assert register_json["token_type"] == "bearer"
        assert "user" in register_json
        assert register_json["user"]["email"] == register_data["email"]
        assert register_json["user"]["full_name"] == register_data["full_name"]
        assert register_json["user"]["role"] == UserRole.CLIENT.value

        # 2. Verify can use access token immediately
        access_token = register_json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        me_response = await client.get("/api/v1/auth/me", headers=headers)

        assert me_response.status_code == status.HTTP_200_OK
        me_json = me_response.json()
        assert me_json["email"] == register_data["email"]
        assert me_json["full_name"] == register_data["full_name"]

    @pytest.mark.asyncio
    async def test_registration_with_duplicate_email(self, client: AsyncClient, auth_user):
        """Test that registering with duplicate email fails."""
        register_data = {
            "email": auth_user["email"],  # Use existing user's email
            "password": "AnotherPass123!",
            "full_name": "Duplicate User",
            "phone": "+5511888888888",
        }

        response = await client.post("/api/v1/auth/register", json=register_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_registration_with_weak_password(self, client: AsyncClient):
        """Test that weak passwords are rejected."""
        register_data = {
            "email": "weakpass@example.com",
            "password": "123",  # Too short
            "full_name": "Weak Password User",
            "phone": "+5511777777777",
        }

        response = await client.post("/api/v1/auth/register", json=register_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginFlow:
    """Tests for login flow."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, auth_user):
        """Test successful login with correct credentials."""
        login_data = {
            "username": auth_user["email"],
            "password": auth_user["password"],
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert "access_token" in json_response
        assert "refresh_token" in json_response
        assert json_response["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, auth_user):
        """Test login fails with wrong password."""
        login_data = {
            "username": auth_user["email"],
            "password": "WrongPassword123!",
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails for non-existent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "SomePassword123!",
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_and_access_protected_endpoint(
        self, client: AsyncClient, auth_user
    ):
        """Test login followed by accessing protected endpoint."""
        # 1. Login
        login_data = {
            "username": auth_user["email"],
            "password": auth_user["password"],
        }

        login_response = await client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == status.HTTP_200_OK

        access_token = login_response.json()["access_token"]

        # 2. Access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/v1/auth/me", headers=headers)

        assert me_response.status_code == status.HTTP_200_OK
        me_json = me_response.json()
        assert me_json["email"] == auth_user["email"]


class TestTokenRefreshFlow:
    """Tests for token refresh flow."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, authenticated_client: AsyncClient):
        """Test refreshing access token with valid refresh token."""
        # Get initial tokens
        login_data = {
            "username": "test@example.com",
            "password": "TestPass123!",
        }

        login_response = await authenticated_client.post(
            "/api/v1/auth/login", data=login_data
        )
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]

        # Refresh the token
        refresh_response = await authenticated_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["token_type"] == "bearer"

        # Verify new access token works
        headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        me_response = await authenticated_client.get("/api/v1/auth/me", headers=headers)

        assert me_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """Test that invalid refresh token is rejected."""
        refresh_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"}
        )

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_with_access_token(self, authenticated_client: AsyncClient):
        """Test that access token cannot be used for refresh."""
        # Get tokens
        login_data = {
            "username": "test@example.com",
            "password": "TestPass123!",
        }

        login_response = await authenticated_client.post(
            "/api/v1/auth/login", data=login_data
        )
        tokens = login_response.json()
        access_token = tokens["access_token"]  # Try to use access token

        # Try to refresh with access token
        refresh_response = await authenticated_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": access_token}
        )

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedEndpointAccess:
    """Tests for accessing protected endpoints."""

    @pytest.mark.asyncio
    async def test_access_without_token(self, client: AsyncClient):
        """Test that protected endpoint requires authentication."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_access_with_invalid_token(self, client: AsyncClient):
        """Test that invalid token is rejected."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = await client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_access_with_malformed_header(self, client: AsyncClient):
        """Test that malformed Authorization header is rejected."""
        # Missing "Bearer" prefix
        headers = {"Authorization": "sometoken"}
        response = await client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestCompleteAuthWorkflow:
    """Tests for complete authentication workflows."""

    @pytest.mark.asyncio
    async def test_full_auth_lifecycle(self, client: AsyncClient):
        """Test complete auth lifecycle: register → login → access → refresh → access."""
        # 1. Register
        register_data = {
            "email": "lifecycle@example.com",
            "password": "LifeCycle123!",
            "full_name": "Lifecycle User",
            "phone": "+5511666666666",
        }

        register_response = await client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        # 2. Login (verify can login after registration)
        login_data = {
            "username": register_data["email"],
            "password": register_data["password"],
        }

        login_response = await client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == status.HTTP_200_OK
        login_tokens = login_response.json()

        # 3. Access protected endpoint with login token
        headers = {"Authorization": f"Bearer {login_tokens['access_token']}"}
        me_response = await client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == register_data["email"]

        # 4. Refresh token
        refresh_response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login_tokens["refresh_token"]}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()

        # 5. Access protected endpoint with new token
        new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        final_me_response = await client.get("/api/v1/auth/me", headers=new_headers)
        assert final_me_response.status_code == status.HTTP_200_OK
        assert final_me_response.json()["email"] == register_data["email"]

    @pytest.mark.asyncio
    async def test_multi_user_isolation(self, client: AsyncClient):
        """Test that different users have isolated authentication."""
        # Register two users
        user1_data = {
            "email": "user1@example.com",
            "password": "User1Pass123!",
            "full_name": "User One",
            "phone": "+5511111111111",
        }

        user2_data = {
            "email": "user2@example.com",
            "password": "User2Pass123!",
            "full_name": "User Two",
            "phone": "+5511222222222",
        }

        user1_response = await client.post("/api/v1/auth/register", json=user1_data)
        user2_response = await client.post("/api/v1/auth/register", json=user2_data)

        assert user1_response.status_code == status.HTTP_201_CREATED
        assert user2_response.status_code == status.HTTP_201_CREATED

        user1_token = user1_response.json()["access_token"]
        user2_token = user2_response.json()["access_token"]

        # Verify each token accesses correct user
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        user1_me = await client.get("/api/v1/auth/me", headers=user1_headers)
        user2_me = await client.get("/api/v1/auth/me", headers=user2_headers)

        assert user1_me.json()["email"] == user1_data["email"]
        assert user2_me.json()["email"] == user2_data["email"]
        assert user1_me.json()["id"] != user2_me.json()["id"]
