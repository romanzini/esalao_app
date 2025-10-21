"""
Tests for operational reporting endpoints.

This module contains comprehensive tests for the salon operational
reporting system, including booking metrics, professional performance,
and service analytics.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.payment import Payment, PaymentStatus
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole
from tests.conftest import (
    admin_user_token,
    booking_data,
    client_user,
    professional_user,
    salon_owner_user,
    test_salon,
    test_service,
)


class TestReportsEndpoints:
    """Test suite for operational reports endpoints."""

    @pytest.mark.asyncio
    async def test_get_dashboard_metrics_success(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test successful dashboard metrics retrieval."""
        # Create test data
        professional = Professional(
            name="Test Professional",
            email="pro@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Test Service",
            duration=60,
            price=50.00,
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # Create bookings with different statuses
        now = datetime.utcnow()
        bookings = [
            Booking(
                client_id=1,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=1),
                status=BookingStatus.COMPLETED,
                service_price=50.00,
            ),
            Booking(
                client_id=1,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=2),
                status=BookingStatus.CANCELLED,
                service_price=50.00,
            ),
            Booking(
                client_id=1,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=3),
                status=BookingStatus.NO_SHOW,
                service_price=50.00,
            ),
        ]

        for booking in bookings:
            db_session.add(booking)
        await db_session.commit()

        # Test dashboard metrics
        response = client.get(
            "/api/v1/reports/dashboard",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "period_start" in data
        assert "period_end" in data
        assert "booking_metrics" in data
        assert "top_professionals" in data
        assert "top_services" in data
        assert "revenue_trend" in data
        assert "booking_trend" in data

        # Verify booking metrics
        booking_metrics = data["booking_metrics"]
        assert booking_metrics["total_bookings"] == 3
        assert booking_metrics["completed_bookings"] == 1
        assert booking_metrics["cancelled_bookings"] == 1
        assert booking_metrics["no_show_bookings"] == 1
        assert booking_metrics["completion_rate"] == 33.33
        assert booking_metrics["total_revenue"] == 50.00

    @pytest.mark.asyncio
    async def test_get_booking_metrics_with_filters(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test booking metrics with various filters."""
        # Create test data
        professional = Professional(
            name="Test Professional",
            email="pro@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Test Service",
            duration=60,
            price=75.00,
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # Create bookings
        now = datetime.utcnow()
        bookings = [
            Booking(
                client_id=1,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=5),
                status=BookingStatus.COMPLETED,
                service_price=75.00,
            ),
            Booking(
                client_id=1,
                professional_id=professional.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=10),
                status=BookingStatus.COMPLETED,
                service_price=75.00,
            ),
        ]

        for booking in bookings:
            db_session.add(booking)
        await db_session.commit()

        # Test with salon filter
        response = client.get(
            "/api/v1/reports/bookings",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={
                "salon_id": test_salon.id,
                "professional_id": professional.id,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_bookings"] == 2
        assert data["completed_bookings"] == 2
        assert data["completion_rate"] == 100.0
        assert data["total_revenue"] == 150.0
        assert data["avg_booking_value"] == 75.0

    @pytest.mark.asyncio
    async def test_get_professional_metrics(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test professional performance metrics."""
        # Create professionals
        professional1 = Professional(
            name="Top Professional",
            email="top@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        professional2 = Professional(
            name="Regular Professional",
            email="regular@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )

        db_session.add_all([professional1, professional2])
        await db_session.commit()

        service = Service(
            name="Test Service",
            duration=60,
            price=100.00,
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # Create bookings for professional1 (higher performer)
        now = datetime.utcnow()
        bookings_pro1 = [
            Booking(
                client_id=1,
                professional_id=professional1.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=100.00,
            )
            for i in range(1, 6)  # 5 completed bookings
        ]

        # Create bookings for professional2 (lower performer)
        bookings_pro2 = [
            Booking(
                client_id=1,
                professional_id=professional2.id,
                service_id=service.id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=100.00,
            )
            for i in range(1, 3)  # 2 completed bookings
        ]

        for booking in bookings_pro1 + bookings_pro2:
            db_session.add(booking)
        await db_session.commit()

        # Test professional metrics
        response = client.get(
            "/api/v1/reports/professionals",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

        # Should be sorted by revenue (top performer first)
        top_professional = data[0]
        assert top_professional["professional_name"] == "Top Professional"
        assert top_professional["total_bookings"] == 5
        assert top_professional["completed_bookings"] == 5
        assert top_professional["completion_rate"] == 100.0
        assert top_professional["total_revenue"] == 500.0
        assert top_professional["avg_booking_value"] == 100.0

    @pytest.mark.asyncio
    async def test_get_service_metrics(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test service performance metrics."""
        professional = Professional(
            name="Test Professional",
            email="pro@test.com",
            salon_id=test_salon.id,
            specialties=["haircut", "color"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        # Create services in different categories
        service1 = Service(
            name="Haircut",
            duration=60,
            price=80.00,
            salon_id=test_salon.id,
            category="haircut",
        )
        service2 = Service(
            name="Hair Color",
            duration=120,
            price=150.00,
            salon_id=test_salon.id,
            category="color",
        )

        db_session.add_all([service1, service2])
        await db_session.commit()

        # Create more bookings for service1 (more popular)
        now = datetime.utcnow()
        bookings_s1 = [
            Booking(
                client_id=1,
                professional_id=professional.id,
                service_id=service1.id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=80.00,
            )
            for i in range(1, 8)  # 7 bookings
        ]

        bookings_s2 = [
            Booking(
                client_id=1,
                professional_id=professional.id,
                service_id=service2.id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=150.00,
            )
            for i in range(1, 4)  # 3 bookings
        ]

        for booking in bookings_s1 + bookings_s2:
            db_session.add(booking)
        await db_session.commit()

        # Test service metrics
        response = client.get(
            "/api/v1/reports/services",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

        # Should be sorted by popularity score (total bookings)
        most_popular = data[0]
        assert most_popular["service_name"] == "Haircut"
        assert most_popular["total_bookings"] == 7
        assert most_popular["total_revenue"] == 560.0
        assert most_popular["popularity_score"] == 7

    @pytest.mark.asyncio
    async def test_get_revenue_trend(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test revenue trend analysis."""
        professional = Professional(
            name="Test Professional",
            email="pro@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Test Service",
            duration=60,
            price=100.00,
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # Create bookings across different days
        now = datetime.utcnow()
        daily_bookings = []

        for day in range(1, 8):  # 7 days
            for booking_num in range(2):  # 2 bookings per day
                booking = Booking(
                    client_id=1,
                    professional_id=professional.id,
                    service_id=service.id,
                    scheduled_at=now - timedelta(days=day),
                    status=BookingStatus.COMPLETED,
                    service_price=100.00,
                )
                daily_bookings.append(booking)

        for booking in daily_bookings:
            db_session.add(booking)
        await db_session.commit()

        # Test daily revenue trend
        response = client.get(
            "/api/v1/reports/revenue/trend",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={
                "salon_id": test_salon.id,
                "aggregation": "daily",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["aggregation"] == "daily"
        assert len(data["data"]) > 0
        assert "summary" in data

        # Check summary metrics
        summary = data["summary"]
        assert summary["total_revenue"] == 1400.0  # 14 bookings * 100
        assert summary["total_bookings"] == 14

    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self,
        client: TestClient,
    ):
        """Test unauthorized access to reports endpoints."""
        # Test without token
        response = client.get("/api/v1/reports/dashboard")
        assert response.status_code == 401

        # Test with invalid token
        response = client.get(
            "/api/v1/reports/dashboard",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_aggregation_parameter(
        self,
        client: TestClient,
        admin_user_token: str,
    ):
        """Test invalid aggregation parameter for revenue trend."""
        response = client.get(
            "/api/v1/reports/revenue/trend",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"aggregation": "invalid"},
        )

        assert response.status_code == 400
        assert "Invalid aggregation" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_empty_data_handling(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
    ):
        """Test handling of empty data sets."""
        # Test with no bookings in the salon
        response = client.get(
            "/api/v1/reports/bookings",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_bookings"] == 0
        assert data["completed_bookings"] == 0
        assert data["completion_rate"] == 0.0
        assert data["total_revenue"] == 0.0

    @pytest.mark.asyncio
    async def test_date_range_filtering(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test date range filtering for reports."""
        professional = Professional(
            name="Test Professional",
            email="pro@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Test Service",
            duration=60,
            price=100.00,
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # Create bookings at different times
        now = datetime.utcnow()
        old_booking = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=now - timedelta(days=60),  # Outside date range
            status=BookingStatus.COMPLETED,
            service_price=100.00,
        )
        recent_booking = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=now - timedelta(days=5),   # Within date range
            status=BookingStatus.COMPLETED,
            service_price=100.00,
        )

        db_session.add_all([old_booking, recent_booking])
        await db_session.commit()

        # Test with specific date range (last 30 days)
        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()

        response = client.get(
            "/api/v1/reports/bookings",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={
                "salon_id": test_salon.id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should only include the recent booking
        assert data["total_bookings"] == 1
        assert data["total_revenue"] == 100.0
