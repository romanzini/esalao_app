"""
Tests for platform reporting endpoints.

This module contains comprehensive tests for the platform-level
reporting system, including salon comparisons, category analytics,
and user behavior metrics.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole
from tests.conftest import (
    admin_user_token,
    client_user,
    salon_owner_user_token,
)


class TestPlatformReportsEndpoints:
    """Test suite for platform reporting endpoints."""

    @pytest.mark.asyncio
    async def test_get_platform_overview_success(
        self,
        client: TestClient,
        admin_user_token: str,
        db_session: AsyncSession,
    ):
        """Test successful platform overview retrieval."""
        # Create multiple salons with data
        salon1 = Salon(
            name="Salon One",
            address="Address 1",
            phone="123456789",
            email="salon1@test.com",
        )
        salon2 = Salon(
            name="Salon Two",
            address="Address 2",
            phone="987654321",
            email="salon2@test.com",
        )

        db_session.add_all([salon1, salon2])
        await db_session.commit()

        # Create professionals for each salon
        professional1 = Professional(
            name="Pro One",
            email="pro1@test.com",
            salon_id=salon1.id,
            specialties=["haircut"],
            is_active=True,
        )
        professional2 = Professional(
            name="Pro Two",
            email="pro2@test.com",
            salon_id=salon2.id,
            specialties=["color"],
            is_active=True,
        )

        db_session.add_all([professional1, professional2])
        await db_session.commit()

        # Create services
        service1 = Service(
            name="Haircut",
            duration=60,
            price=50.00,
            salon_id=salon1.id,
            category="haircut",
        )
        service2 = Service(
            name="Hair Color",
            duration=120,
            price=100.00,
            salon_id=salon2.id,
            category="color",
        )

        db_session.add_all([service1, service2])
        await db_session.commit()

        # Create bookings
        now = datetime.utcnow()
        bookings = [
            Booking(
                client_id=1,
                professional_id=professional1.id,
                service_id=service1.id,
                scheduled_at=now - timedelta(days=1),
                status=BookingStatus.COMPLETED,
                service_price=50.00,
            ),
            Booking(
                client_id=1,
                professional_id=professional2.id,
                service_id=service2.id,
                scheduled_at=now - timedelta(days=2),
                status=BookingStatus.COMPLETED,
                service_price=100.00,
            ),
        ]

        for booking in bookings:
            db_session.add(booking)
        await db_session.commit()

        # Test platform overview
        response = client.get(
            "/api/v1/platform-reports/overview",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "total_salons" in data
        assert "active_salons" in data
        assert "total_professionals" in data
        assert "total_services" in data
        assert "total_bookings" in data
        assert "total_revenue" in data
        assert "platform_growth_rate" in data
        assert "avg_salon_revenue" in data
        assert "top_performing_salons" in data

        # Verify data
        assert data["total_salons"] >= 2
        assert data["active_salons"] >= 1  # At least one salon has bookings
        assert data["total_professionals"] >= 2
        assert data["total_services"] >= 2
        assert data["total_bookings"] >= 2
        assert data["total_revenue"] >= 150.0

    @pytest.mark.asyncio
    async def test_get_salon_performance_comparison(
        self,
        client: TestClient,
        admin_user_token: str,
        db_session: AsyncSession,
    ):
        """Test salon performance comparison."""
        # Create salons with different performance levels
        high_performing_salon = Salon(
            name="High Performer",
            address="Address 1",
            phone="123456789",
            email="high@test.com",
        )
        low_performing_salon = Salon(
            name="Low Performer",
            address="Address 2",
            phone="987654321",
            email="low@test.com",
        )

        db_session.add_all([high_performing_salon, low_performing_salon])
        await db_session.commit()

        # Create professionals
        high_pro = Professional(
            name="High Pro",
            email="highpro@test.com",
            salon_id=high_performing_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        low_pro = Professional(
            name="Low Pro",
            email="lowpro@test.com",
            salon_id=low_performing_salon.id,
            specialties=["haircut"],
            is_active=True,
        )

        db_session.add_all([high_pro, low_pro])
        await db_session.commit()

        # Create services
        high_service = Service(
            name="Premium Cut",
            duration=60,
            price=100.00,
            salon_id=high_performing_salon.id,
            category="haircut",
        )
        low_service = Service(
            name="Basic Cut",
            duration=60,
            price=50.00,
            salon_id=low_performing_salon.id,
            category="haircut",
        )

        db_session.add_all([high_service, low_service])
        await db_session.commit()

        # Create more bookings for high-performing salon
        now = datetime.utcnow()

        # High performer: 5 completed bookings
        high_bookings = [
            Booking(
                client_id=1,
                professional_id=high_pro.id,
                service_id=high_service.id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=100.00,
            )
            for i in range(1, 6)
        ]

        # Low performer: 2 completed bookings
        low_bookings = [
            Booking(
                client_id=1,
                professional_id=low_pro.id,
                service_id=low_service.id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=50.00,
            )
            for i in range(1, 3)
        ]

        for booking in high_bookings + low_bookings:
            db_session.add(booking)
        await db_session.commit()

        # Test salon performance comparison (sorted by revenue)
        response = client.get(
            "/api/v1/platform-reports/salons/performance",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"sort_by": "revenue"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 2

        # First salon should be high performer (higher revenue)
        high_perf_data = data[0]
        assert high_perf_data["salon_name"] == "High Performer"
        assert high_perf_data["total_bookings"] == 5
        assert high_perf_data["completed_bookings"] == 5
        assert high_perf_data["completion_rate"] == 100.0
        assert high_perf_data["total_revenue"] == 500.0

    @pytest.mark.asyncio
    async def test_get_category_analytics(
        self,
        client: TestClient,
        admin_user_token: str,
        db_session: AsyncSession,
    ):
        """Test service category analytics."""
        # Create salons
        salon1 = Salon(
            name="Salon One",
            address="Address 1",
            phone="123456789",
            email="salon1@test.com",
        )
        salon2 = Salon(
            name="Salon Two",
            address="Address 2",
            phone="987654321",
            email="salon2@test.com",
        )

        db_session.add_all([salon1, salon2])
        await db_session.commit()

        # Create professionals
        pro1 = Professional(
            name="Pro One",
            email="pro1@test.com",
            salon_id=salon1.id,
            specialties=["haircut"],
            is_active=True,
        )
        pro2 = Professional(
            name="Pro Two",
            email="pro2@test.com",
            salon_id=salon2.id,
            specialties=["color"],
            is_active=True,
        )

        db_session.add_all([pro1, pro2])
        await db_session.commit()

        # Create services in different categories
        haircut_services = [
            Service(
                name="Basic Haircut",
                duration=60,
                price=40.00,
                salon_id=salon1.id,
                category="haircut",
            ),
            Service(
                name="Premium Haircut",
                duration=60,
                price=80.00,
                salon_id=salon2.id,
                category="haircut",
            ),
        ]

        color_services = [
            Service(
                name="Hair Color",
                duration=120,
                price=120.00,
                salon_id=salon1.id,
                category="color",
            ),
        ]

        all_services = haircut_services + color_services
        for service in all_services:
            db_session.add(service)
        await db_session.commit()

        # Create bookings for different categories
        now = datetime.utcnow()

        # More bookings for haircut (more popular category)
        haircut_bookings = [
            Booking(
                client_id=1,
                professional_id=pro1.id,
                service_id=haircut_services[0].id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=40.00,
            )
            for i in range(1, 6)  # 5 bookings
        ]

        color_bookings = [
            Booking(
                client_id=1,
                professional_id=pro1.id,
                service_id=color_services[0].id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=120.00,
            )
            for i in range(1, 3)  # 2 bookings
        ]

        for booking in haircut_bookings + color_bookings:
            db_session.add(booking)
        await db_session.commit()

        # Test category analytics
        response = client.get(
            "/api/v1/platform-reports/categories/analytics",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have at least 2 categories
        assert len(data) >= 2

        # Find haircut category (should be first due to higher revenue or popularity)
        haircut_data = next(
            (item for item in data if item["category"] == "haircut"),
            None
        )
        color_data = next(
            (item for item in data if item["category"] == "color"),
            None
        )

        assert haircut_data is not None
        assert color_data is not None

        # Verify haircut data
        assert haircut_data["total_services"] == 2
        assert haircut_data["total_bookings"] == 5
        assert haircut_data["total_revenue"] == 200.0
        assert haircut_data["salon_adoption_rate"] == 100.0  # Both salons have haircut services

    @pytest.mark.asyncio
    async def test_get_user_analytics(
        self,
        client: TestClient,
        admin_user_token: str,
        db_session: AsyncSession,
    ):
        """Test user behavior analytics."""
        # Create additional test users
        users = [
            User(
                name="Client One",
                email="client1@test.com",
                hashed_password="hashed_pass",
                role=UserRole.CLIENT,
                created_at=datetime.utcnow() - timedelta(days=20),
            ),
            User(
                name="Client Two",
                email="client2@test.com",
                hashed_password="hashed_pass",
                role=UserRole.CLIENT,
                created_at=datetime.utcnow() - timedelta(days=10),
            ),
        ]

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # Create salon and professional for bookings
        salon = Salon(
            name="Test Salon",
            address="Address",
            phone="123456789",
            email="salon@test.com",
        )
        db_session.add(salon)
        await db_session.commit()

        professional = Professional(
            name="Test Pro",
            email="pro@test.com",
            salon_id=salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Test Service",
            duration=60,
            price=75.00,
            salon_id=salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # Create bookings for user analytics
        now = datetime.utcnow()
        bookings = [
            # Recent bookings for both users
            Booking(
                client_id=users[0].id,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=5),
                status=BookingStatus.COMPLETED,
                service_price=75.00,
            ),
            Booking(
                client_id=users[0].id,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=3),
                status=BookingStatus.COMPLETED,
                service_price=75.00,
            ),
            Booking(
                client_id=users[1].id,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=2),
                status=BookingStatus.COMPLETED,
                service_price=75.00,
            ),
        ]

        for booking in bookings:
            db_session.add(booking)
        await db_session.commit()

        # Test user analytics
        response = client.get(
            "/api/v1/platform-reports/users/analytics",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "total_users" in data
        assert "active_users_30d" in data
        assert "new_users_30d" in data
        assert "user_retention_rate" in data
        assert "avg_bookings_per_user" in data
        assert "user_lifetime_value" in data

        # Verify data makes sense
        assert data["total_users"] >= 2
        assert data["active_users_30d"] >= 2  # Both users had recent bookings
        assert data["new_users_30d"] >= 2    # Both users were created recently
        assert data["user_lifetime_value"] > 0

    @pytest.mark.asyncio
    async def test_get_growth_trends(
        self,
        client: TestClient,
        admin_user_token: str,
        db_session: AsyncSession,
    ):
        """Test platform growth trends."""
        # Create historical data across multiple months
        base_date = datetime.utcnow()

        # Create users across different months
        users = []
        for month_offset in range(3):
            for user_num in range(2):
                user = User(
                    name=f"User {month_offset}-{user_num}",
                    email=f"user{month_offset}{user_num}@test.com",
                    hashed_password="hashed_pass",
                    role=UserRole.CLIENT,
                    created_at=base_date - timedelta(days=30 * month_offset + user_num),
                )
                users.append(user)

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # Create salons across different months
        salons = []
        for month_offset in range(2):
            salon = Salon(
                name=f"Salon {month_offset}",
                address=f"Address {month_offset}",
                phone=f"12345678{month_offset}",
                email=f"salon{month_offset}@test.com",
                created_at=base_date - timedelta(days=30 * month_offset),
            )
            salons.append(salon)

        for salon in salons:
            db_session.add(salon)
        await db_session.commit()

        # Test growth trends
        response = client.get(
            "/api/v1/platform-reports/growth/trends",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"months_back": 6},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "period_months" in data
        assert "data" in data
        assert "summary" in data

        assert data["period_months"] == 6
        assert len(data["data"]) > 0

        # Verify summary
        summary = data["summary"]
        assert "total_months" in summary
        assert "avg_monthly_users" in summary
        assert "avg_monthly_revenue" in summary

    @pytest.mark.asyncio
    async def test_admin_only_access(
        self,
        client: TestClient,
        salon_owner_user_token: str,
    ):
        """Test that platform reports are admin-only."""
        # Test with salon owner token (should be denied)
        response = client.get(
            "/api/v1/platform-reports/overview",
            headers={"Authorization": f"Bearer {salon_owner_user_token}"},
        )

        assert response.status_code == 403

        # Test other platform endpoints
        endpoints = [
            "/api/v1/platform-reports/salons/performance",
            "/api/v1/platform-reports/categories/analytics",
            "/api/v1/platform-reports/users/analytics",
            "/api/v1/platform-reports/growth/trends",
        ]

        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {salon_owner_user_token}"},
            )
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_sort_parameter_validation(
        self,
        client: TestClient,
        admin_user_token: str,
    ):
        """Test sort parameter validation for salon performance."""
        # Test invalid sort parameter
        response = client.get(
            "/api/v1/platform-reports/salons/performance",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"sort_by": "invalid_sort"},
        )

        assert response.status_code == 400
        assert "Invalid sort_by" in response.json()["detail"]

        # Test valid sort parameters
        valid_sorts = ["revenue", "bookings", "completion_rate"]
        for sort_by in valid_sorts:
            response = client.get(
                "/api/v1/platform-reports/salons/performance",
                headers={"Authorization": f"Bearer {admin_user_token}"},
                params={"sort_by": sort_by},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_limit_parameter(
        self,
        client: TestClient,
        admin_user_token: str,
        db_session: AsyncSession,
    ):
        """Test limit parameter for salon performance."""
        # Create multiple salons
        salons = []
        for i in range(5):
            salon = Salon(
                name=f"Salon {i}",
                address=f"Address {i}",
                phone=f"12345678{i}",
                email=f"salon{i}@test.com",
            )
            salons.append(salon)

        for salon in salons:
            db_session.add(salon)
        await db_session.commit()

        # Test with limit parameter
        response = client.get(
            "/api/v1/platform-reports/salons/performance",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"limit": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return at most 3 salons
        assert len(data) <= 3
