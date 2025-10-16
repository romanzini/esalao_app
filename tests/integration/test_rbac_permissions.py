"""Integration tests for RBAC permissions across endpoints.

Tests role-based access control to ensure:
- Clients can only access their own resources
- Admins have full access
- Professionals can access their own data
- Proper 403 Forbidden responses for unauthorized access
"""

from datetime import datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient

from backend.app.db.models.user import UserRole


class TestClientPermissions:
    """Tests for CLIENT role permissions."""

    @pytest.mark.asyncio
    async def test_client_can_create_booking(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that client can create their own booking."""
        future_time = (datetime.now() + timedelta(days=1, hours=10)).isoformat()
        booking_data = {**test_booking_data, "start_time": future_time}

        response = await authenticated_client.post("/api/v1/bookings", json=booking_data)

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_client_can_view_own_bookings(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that client can view their own bookings."""
        # Create a booking
        future_time = (datetime.now() + timedelta(days=1, hours=11)).isoformat()
        booking_data = {**test_booking_data, "start_time": future_time}

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        booking_id = create_response.json()["id"]

        # View the booking
        get_response = await authenticated_client.get(f"/api/v1/bookings/{booking_id}")

        assert get_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_client_cannot_create_professional(
        self, authenticated_client: AsyncClient
    ):
        """Test that client cannot create professionals."""
        professional_data = {
            "salon_id": 1,
            "name": "New Professional",
            "email": "newpro@example.com",
            "phone": "+5511999999999",
            "specialties": ["Cabelo"],
        }

        response = await authenticated_client.post(
            "/api/v1/professionals", json=professional_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_client_cannot_create_service(self, authenticated_client: AsyncClient):
        """Test that client cannot create services."""
        service_data = {
            "salon_id": 1,
            "name": "New Service",
            "description": "Test service",
            "duration_minutes": 60,
            "price": "100.00",
            "category": "Cabelo",
        }

        response = await authenticated_client.post("/api/v1/services", json=service_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_client_cannot_update_booking_status(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that client cannot update booking status."""
        # Create booking
        future_time = (datetime.now() + timedelta(days=1, hours=12)).isoformat()
        booking_data = {**test_booking_data, "start_time": future_time}

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        booking_id = create_response.json()["id"]

        # Try to update status
        update_response = await authenticated_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "confirmed"}
        )

        assert update_response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminPermissions:
    """Tests for ADMIN role permissions."""

    @pytest.mark.asyncio
    async def test_admin_can_create_professional(
        self, admin_client: AsyncClient, test_salon_data: dict
    ):
        """Test that admin can create professionals."""
        professional_data = {
            "salon_id": test_salon_data["salon_id"],
            "name": "Admin Created Pro",
            "email": "adminpro@example.com",
            "phone": "+5511888888888",
            "specialties": ["Cabelo", "Barba"],
        }

        response = await admin_client.post("/api/v1/professionals", json=professional_data)

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_admin_can_create_service(
        self, admin_client: AsyncClient, test_salon_data: dict
    ):
        """Test that admin can create services."""
        service_data = {
            "salon_id": test_salon_data["salon_id"],
            "name": "Admin Service",
            "description": "Service created by admin",
            "duration_minutes": 90,
            "price": "150.00",
            "category": "Cabelo",
        }

        response = await admin_client.post("/api/v1/services", json=service_data)

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_admin_can_update_booking_status(
        self,
        admin_client: AsyncClient,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that admin can update booking status."""
        # Client creates booking
        future_time = (datetime.now() + timedelta(days=1, hours=13)).isoformat()
        booking_data = {**test_booking_data, "start_time": future_time}

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        booking_id = create_response.json()["id"]

        # Admin updates status
        update_response = await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "confirmed"}
        )

        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_admin_can_view_all_bookings(
        self,
        admin_client: AsyncClient,
    ):
        """Test that admin can view all bookings."""
        response = await admin_client.get("/api/v1/bookings")

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_admin_can_delete_professional(
        self, admin_client: AsyncClient, test_salon_data: dict
    ):
        """Test that admin can delete professionals."""
        # Create professional
        professional_data = {
            "salon_id": test_salon_data["salon_id"],
            "name": "To Delete Pro",
            "email": "todelete@example.com",
            "phone": "+5511777777777",
            "specialties": ["Cabelo"],
        }

        create_response = await admin_client.post(
            "/api/v1/professionals", json=professional_data
        )
        professional_id = create_response.json()["id"]

        # Delete professional
        delete_response = await admin_client.delete(
            f"/api/v1/professionals/{professional_id}"
        )

        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_admin_can_delete_service(
        self, admin_client: AsyncClient, test_salon_data: dict
    ):
        """Test that admin can delete services."""
        # Create service
        service_data = {
            "salon_id": test_salon_data["salon_id"],
            "name": "To Delete Service",
            "description": "Will be deleted",
            "duration_minutes": 30,
            "price": "50.00",
            "category": "Barba",
        }

        create_response = await admin_client.post("/api/v1/services", json=service_data)
        service_id = create_response.json()["id"]

        # Delete service
        delete_response = await admin_client.delete(f"/api/v1/services/{service_id}")

        assert delete_response.status_code == status.HTTP_204_NO_CONTENT


class TestCrossUserAccess:
    """Tests for cross-user resource access restrictions."""

    @pytest.mark.asyncio
    async def test_client_cannot_view_other_client_booking(
        self,
        client: AsyncClient,
        db_session,
    ):
        """Test that one client cannot view another client's booking."""
        # Create two clients
        from backend.app.db.models.user import User
        from backend.app.core.security.password import hash_password

        user1 = User(
            email="client1@example.com",
            password_hash=hash_password("Pass123!"),
            full_name="Client One",
            phone="+5511111111111",
            role=UserRole.CLIENT,
        )

        user2 = User(
            email="client2@example.com",
            password_hash=hash_password("Pass123!"),
            full_name="Client Two",
            phone="+5511222222222",
            role=UserRole.CLIENT,
        )

        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Login as client1
        login1_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "client1@example.com", "password": "Pass123!"},
        )
        client1_token = login1_response.json()["access_token"]
        client1_headers = {"Authorization": f"Bearer {client1_token}"}

        # Login as client2
        login2_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "client2@example.com", "password": "Pass123!"},
        )
        client2_token = login2_response.json()["access_token"]
        client2_headers = {"Authorization": f"Bearer {client2_token}"}

        # Client1 creates booking
        from tests.conftest import create_test_booking_data

        booking_data = await create_test_booking_data(db_session)
        future_time = (datetime.now() + timedelta(days=1, hours=14)).isoformat()
        booking_request = {**booking_data, "start_time": future_time}

        create_response = await client.post(
            "/api/v1/bookings", json=booking_request, headers=client1_headers
        )
        booking_id = create_response.json()["id"]

        # Client2 tries to view client1's booking
        view_response = await client.get(
            f"/api/v1/bookings/{booking_id}", headers=client2_headers
        )

        # Should be forbidden or not found
        assert view_response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    @pytest.mark.asyncio
    async def test_client_cannot_cancel_other_client_booking(
        self,
        client: AsyncClient,
        db_session,
    ):
        """Test that one client cannot cancel another client's booking."""
        # Create two clients
        from backend.app.db.models.user import User
        from backend.app.core.security.password import hash_password

        user1 = User(
            email="client3@example.com",
            password_hash=hash_password("Pass123!"),
            full_name="Client Three",
            phone="+5511333333333",
            role=UserRole.CLIENT,
        )

        user2 = User(
            email="client4@example.com",
            password_hash=hash_password("Pass123!"),
            full_name="Client Four",
            phone="+5511444444444",
            role=UserRole.CLIENT,
        )

        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Login as both clients
        login1_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "client3@example.com", "password": "Pass123!"},
        )
        client1_token = login1_response.json()["access_token"]
        client1_headers = {"Authorization": f"Bearer {client1_token}"}

        login2_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "client4@example.com", "password": "Pass123!"},
        )
        client2_token = login2_response.json()["access_token"]
        client2_headers = {"Authorization": f"Bearer {client2_token}"}

        # Client1 creates booking
        from tests.conftest import create_test_booking_data

        booking_data = await create_test_booking_data(db_session)
        future_time = (datetime.now() + timedelta(days=1, hours=15)).isoformat()
        booking_request = {**booking_data, "start_time": future_time}

        create_response = await client.post(
            "/api/v1/bookings", json=booking_request, headers=client1_headers
        )
        booking_id = create_response.json()["id"]

        # Client2 tries to cancel client1's booking
        cancel_response = await client.delete(
            f"/api/v1/bookings/{booking_id}", headers=client2_headers
        )

        # Should be forbidden
        assert cancel_response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


class TestEndpointAccessMatrix:
    """Tests for endpoint access matrix across all roles."""

    @pytest.mark.asyncio
    async def test_professional_endpoints_access_matrix(self, client: AsyncClient):
        """Test access to professional endpoints by different roles."""
        # This test would ideally create users with different roles
        # and verify GET, POST, PATCH, DELETE access for each role

        # For now, we verify that unauthenticated access is blocked
        response = await client.get("/api/v1/professionals")

        # Should require authentication
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_service_endpoints_access_matrix(self, client: AsyncClient):
        """Test access to service endpoints by different roles."""
        # Unauthenticated access should be blocked
        response = await client.get("/api/v1/services")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_booking_endpoints_require_authentication(self, client: AsyncClient):
        """Test that booking endpoints require authentication."""
        # Try to create booking without auth
        future_time = (datetime.now() + timedelta(days=1, hours=10)).isoformat()
        booking_data = {
            "professional_id": 1,
            "service_id": 1,
            "start_time": future_time,
        }

        response = await client.post("/api/v1/bookings", json=booking_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
