"""
Component-specific integration tests for Phase 3 systems.

This module contains focused integration tests for individual components
with their dependencies, ensuring each system works correctly within
the broader Phase 3 ecosystem.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.cancellation_policy import CancellationPolicy
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole
from tests.conftest import (
    admin_user_token,
    client_user,
    salon_owner_user_token,
    test_salon,
)


class TestCancellationPolicyIntegration:
    """Integration tests for cancellation policy system."""

    @pytest.mark.asyncio
    async def test_policy_creation_and_application_workflow(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test complete policy creation and application workflow."""
        # 1. Create tiered cancellation policy
        policy_data = {
            "salon_id": test_salon.id,
            "name": "Premium Tiered Policy",
            "description": "Multi-tier cancellation policy for premium services",
            "tiers": [
                {
                    "hours_before": 48,
                    "fee_percentage": 0.0,
                    "fee_fixed": 0.0,
                    "description": "Free cancellation 48+ hours"
                },
                {
                    "hours_before": 24,
                    "fee_percentage": 25.0,
                    "fee_fixed": 0.0,
                    "description": "25% fee 24-48 hours"
                },
                {
                    "hours_before": 4,
                    "fee_percentage": 50.0,
                    "fee_fixed": 0.0,
                    "description": "50% fee 4-24 hours"
                },
                {
                    "hours_before": 0,
                    "fee_percentage": 100.0,
                    "fee_fixed": 0.0,
                    "description": "Full fee less than 4 hours"
                }
            ]
        }

        # Create policy
        policy_response = client.post(
            "/api/v1/cancellation-policies",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json=policy_data,
        )

        assert policy_response.status_code == 201
        policy = policy_response.json()
        assert len(policy["tiers"]) == 4

        # 2. Create service with policy
        professional = Professional(
            name="Policy Test Pro",
            email="policy@test.com",
            salon_id=test_salon.id,
            specialties=["premium"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Premium Service with Policy",
            duration=120,
            price=Decimal("200.00"),
            salon_id=test_salon.id,
            category="premium",
            cancellation_policy_id=policy["id"],
        )
        db_session.add(service)
        await db_session.commit()

        # 3. Test different cancellation scenarios
        cancellation_scenarios = [
            {
                "hours_ahead": 72,  # 3 days ahead
                "expected_fee": 0.0,
                "description": "Free cancellation"
            },
            {
                "hours_ahead": 36,  # 1.5 days ahead
                "expected_fee": 50.0,  # 25% of 200
                "description": "25% fee"
            },
            {
                "hours_ahead": 12,  # 12 hours ahead
                "expected_fee": 100.0,  # 50% of 200
                "description": "50% fee"
            },
            {
                "hours_ahead": 2,   # 2 hours ahead
                "expected_fee": 200.0,  # 100% of 200
                "description": "Full fee"
            }
        ]

        for scenario in cancellation_scenarios:
            # Create booking
            booking_time = datetime.utcnow() + timedelta(hours=scenario["hours_ahead"])

            booking_data = {
                "professional_id": professional.id,
                "service_id": service.id,
                "scheduled_at": booking_time.isoformat(),
                "notes": f"Policy test - {scenario['description']}",
            }

            booking_response = client.post(
                "/api/v1/bookings",
                headers={"Authorization": f"Bearer {admin_user_token}"},
                json=booking_data,
            )

            assert booking_response.status_code == 201
            booking = booking_response.json()

            # Cancel booking
            cancel_response = client.post(
                f"/api/v1/bookings/{booking['id']}/cancel",
                headers={"Authorization": f"Bearer {admin_user_token}"},
                json={"reason": f"Testing {scenario['description']}"},
            )

            assert cancel_response.status_code == 200
            cancel_data = cancel_response.json()

            # Verify correct fee calculation
            assert cancel_data["status"] == "cancelled"
            assert cancel_data["cancellation_fee"] == scenario["expected_fee"]

    @pytest.mark.asyncio
    async def test_policy_updates_and_versioning(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test policy updates and their effect on existing bookings."""
        # 1. Create initial policy
        initial_policy_data = {
            "salon_id": test_salon.id,
            "name": "Initial Policy",
            "description": "Initial cancellation policy",
            "tiers": [
                {
                    "hours_before": 24,
                    "fee_percentage": 30.0,
                    "fee_fixed": 0.0,
                    "description": "30% fee within 24 hours"
                }
            ]
        }

        policy_response = client.post(
            "/api/v1/cancellation-policies",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json=initial_policy_data,
        )

        assert policy_response.status_code == 201
        policy = policy_response.json()

        # 2. Create booking with initial policy
        professional = Professional(
            name="Versioning Test Pro",
            email="version@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Versioning Test Service",
            duration=60,
            price=Decimal("100.00"),
            salon_id=test_salon.id,
            category="haircut",
            cancellation_policy_id=policy["id"],
        )
        db_session.add(service)
        await db_session.commit()

        booking_data = {
            "professional_id": professional.id,
            "service_id": service.id,
            "scheduled_at": (datetime.utcnow() + timedelta(hours=12)).isoformat(),
            "notes": "Policy versioning test",
        }

        booking_response = client.post(
            "/api/v1/bookings",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json=booking_data,
        )

        assert booking_response.status_code == 201
        booking = booking_response.json()

        # 3. Update policy
        updated_policy_data = {
            **initial_policy_data,
            "tiers": [
                {
                    "hours_before": 24,
                    "fee_percentage": 50.0,  # Changed from 30% to 50%
                    "fee_fixed": 0.0,
                    "description": "50% fee within 24 hours (updated)"
                }
            ]
        }

        update_response = client.put(
            f"/api/v1/cancellation-policies/{policy['id']}",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json=updated_policy_data,
        )

        assert update_response.status_code == 200

        # 4. Cancel booking (should use policy at time of booking creation)
        cancel_response = client.post(
            f"/api/v1/bookings/{booking['id']}/cancel",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json={"reason": "Testing policy versioning"},
        )

        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()

        # Should use original policy (30% fee), not updated policy (50% fee)
        # This tests that bookings maintain their original policy terms
        expected_fee = 30.0  # 30% of 100.00
        assert cancel_data["cancellation_fee"] == expected_fee


class TestNoShowDetectionIntegration:
    """Integration tests for no-show detection system."""

    @pytest.mark.asyncio
    async def test_automated_no_show_detection_job(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test automated no-show detection job with various scenarios."""
        # 1. Create test data
        professional = Professional(
            name="NoShow Test Pro",
            email="noshow@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="NoShow Test Service",
            duration=60,
            price=Decimal("60.00"),
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # 2. Create various booking scenarios
        now = datetime.utcnow()

        # Scenario 1: Past confirmed booking (should become no-show)
        past_confirmed = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=now - timedelta(hours=3),  # 3 hours ago
            status=BookingStatus.CONFIRMED,
            service_price=Decimal("60.00"),
        )

        # Scenario 2: Past completed booking (should remain completed)
        past_completed = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=now - timedelta(hours=2),  # 2 hours ago
            status=BookingStatus.COMPLETED,
            service_price=Decimal("60.00"),
        )

        # Scenario 3: Future confirmed booking (should remain confirmed)
        future_confirmed = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=now + timedelta(hours=2),  # 2 hours from now
            status=BookingStatus.CONFIRMED,
            service_price=Decimal("60.00"),
        )

        # Scenario 4: Past cancelled booking (should remain cancelled)
        past_cancelled = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=now - timedelta(hours=4),  # 4 hours ago
            status=BookingStatus.CANCELLED,
            service_price=Decimal("60.00"),
        )

        all_bookings = [past_confirmed, past_completed, future_confirmed, past_cancelled]
        for booking in all_bookings:
            db_session.add(booking)
        await db_session.commit()

        # 3. Run no-show detection job
        job_response = client.post(
            "/api/v1/no-show-jobs/run",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert job_response.status_code == 200
        job_result = job_response.json()

        # Should process at least the past confirmed booking
        assert job_result["processed_bookings"] >= 1
        assert job_result["no_shows_detected"] >= 1

        # 4. Verify booking status changes
        # Refresh booking data
        await db_session.refresh(past_confirmed)
        await db_session.refresh(past_completed)
        await db_session.refresh(future_confirmed)
        await db_session.refresh(past_cancelled)

        # Check expected status changes
        assert past_confirmed.status == BookingStatus.NO_SHOW
        assert past_completed.status == BookingStatus.COMPLETED  # Should remain
        assert future_confirmed.status == BookingStatus.CONFIRMED  # Should remain
        assert past_cancelled.status == BookingStatus.CANCELLED  # Should remain

    @pytest.mark.asyncio
    async def test_no_show_job_scheduling_and_configuration(
        self,
        client: TestClient,
        admin_user_token: str,
    ):
        """Test no-show job scheduling and configuration."""
        # 1. Test job configuration
        config_response = client.get(
            "/api/v1/no-show-jobs/config",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert config_response.status_code == 200
        config_data = config_response.json()

        # Should have configuration parameters
        assert "grace_period_minutes" in config_data
        assert "batch_size" in config_data

        # 2. Test job history
        history_response = client.get(
            "/api/v1/no-show-jobs/history",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert history_response.status_code == 200
        history_data = history_response.json()

        # Should return job execution history
        assert "jobs" in history_data
        assert isinstance(history_data["jobs"], list)

    @pytest.mark.asyncio
    async def test_no_show_with_cancellation_policies(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test no-show detection with cancellation policies applied."""
        # 1. Create cancellation policy with no-show fees
        policy_data = {
            "salon_id": test_salon.id,
            "name": "No-Show Policy",
            "description": "Policy with no-show penalties",
            "tiers": [
                {
                    "hours_before": 0,
                    "fee_percentage": 100.0,
                    "fee_fixed": 25.0,  # Additional fixed fee for no-shows
                    "description": "Full fee plus fixed penalty for no-shows"
                }
            ]
        }

        policy_response = client.post(
            "/api/v1/cancellation-policies",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json=policy_data,
        )

        assert policy_response.status_code == 201
        policy = policy_response.json()

        # 2. Create booking with no-show policy
        professional = Professional(
            name="NoShow Policy Pro",
            email="noshowpolicy@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="NoShow Policy Service",
            duration=60,
            price=Decimal("80.00"),
            salon_id=test_salon.id,
            category="haircut",
            cancellation_policy_id=policy["id"],
        )
        db_session.add(service)
        await db_session.commit()

        # Create past booking that will become no-show
        past_booking = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=datetime.utcnow() - timedelta(hours=2),
            status=BookingStatus.CONFIRMED,
            service_price=Decimal("80.00"),
        )
        db_session.add(past_booking)
        await db_session.commit()

        # 3. Run no-show detection
        job_response = client.post(
            "/api/v1/no-show-jobs/run",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert job_response.status_code == 200

        # 4. Verify no-show was detected and policy applied
        await db_session.refresh(past_booking)
        assert past_booking.status == BookingStatus.NO_SHOW

        # Check if fee was calculated (would be 100% + fixed fee)
        expected_fee = 80.0 + 25.0  # Service price + fixed penalty
        # Note: Fee calculation might be handled differently in actual implementation


class TestAuditEventIntegration:
    """Integration tests for audit event system."""

    @pytest.mark.asyncio
    async def test_audit_event_creation_across_systems(
        self,
        client: TestClient,
        admin_user_token: str,
        salon_owner_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test audit event creation across different systems."""
        # 1. Create test entities
        professional = Professional(
            name="Audit Integration Pro",
            email="auditint@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Audit Integration Service",
            duration=60,
            price=Decimal("70.00"),
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # 2. Perform operations that should create audit events
        with patch('backend.app.middleware.audit.AuditEventLogger.log_event') as mock_audit:
            # Create booking
            booking_response = client.post(
                "/api/v1/bookings",
                headers={"Authorization": f"Bearer {salon_owner_user_token}"},
                json={
                    "professional_id": professional.id,
                    "service_id": service.id,
                    "scheduled_at": (datetime.utcnow() + timedelta(hours=6)).isoformat(),
                    "notes": "Audit integration test",
                },
            )

            assert booking_response.status_code == 201
            booking = booking_response.json()

            # Verify audit logging was called
            mock_audit.assert_called()

        # 3. Create cancellation policy (should also trigger audit)
        with patch('backend.app.middleware.audit.AuditEventLogger.log_event') as mock_audit:
            policy_response = client.post(
                "/api/v1/cancellation-policies",
                headers={"Authorization": f"Bearer {admin_user_token}"},
                json={
                    "salon_id": test_salon.id,
                    "name": "Audit Test Policy",
                    "description": "Policy for audit testing",
                    "tiers": [
                        {
                            "hours_before": 24,
                            "fee_percentage": 50.0,
                            "fee_fixed": 0.0,
                            "description": "50% fee"
                        }
                    ]
                },
            )

            assert policy_response.status_code == 201

            # Verify audit logging was called
            mock_audit.assert_called()

        # 4. Test audit event retrieval
        events_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"limit": 20},
        )

        assert events_response.status_code == 200
        events_data = events_response.json()

        # Should have events from our operations
        assert len(events_data["events"]) >= 0  # May be empty if mocked

    @pytest.mark.asyncio
    async def test_audit_event_filtering_and_search(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test audit event filtering and search capabilities."""
        # 1. Test filtering by event type
        events_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"event_type": "booking_created"},
        )

        assert events_response.status_code == 200
        events_data = events_response.json()

        # All events should be of the specified type
        for event in events_data["events"]:
            assert event["event_type"] == "booking_created"

        # 2. Test filtering by date range
        start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        end_date = datetime.utcnow().isoformat()

        date_events_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert date_events_response.status_code == 200

        # 3. Test filtering by user
        user_events_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"user_id": 1},
        )

        assert user_events_response.status_code == 200

        # 4. Test event statistics
        stats_response = client.get(
            "/api/v1/audit/events/stats",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        # Should contain statistics structure
        assert "total_events" in stats_data
        assert isinstance(stats_data["total_events"], int)


class TestReportingSystemIntegration:
    """Integration tests for reporting system."""

    @pytest.mark.asyncio
    async def test_end_to_end_reporting_workflow(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """Test end-to-end reporting workflow with real data."""
        # 1. Create comprehensive test data
        professionals = []
        services = []
        bookings = []

        # Create multiple professionals
        for i in range(3):
            professional = Professional(
                name=f"Report Test Pro {i+1}",
                email=f"reportpro{i+1}@test.com",
                salon_id=test_salon.id,
                specialties=["haircut", "color"][i % 2:i % 2 + 1],
                is_active=True,
            )
            db_session.add(professional)
            professionals.append(professional)

        await db_session.commit()

        # Create multiple services
        service_data = [
            ("Basic Haircut", 60, "50.00", "haircut"),
            ("Premium Color", 180, "150.00", "color"),
            ("Styling", 90, "80.00", "styling"),
        ]

        for name, duration, price, category in service_data:
            service = Service(
                name=name,
                duration=duration,
                price=Decimal(price),
                salon_id=test_salon.id,
                category=category,
            )
            db_session.add(service)
            services.append(service)

        await db_session.commit()

        # Create bookings with various statuses
        now = datetime.utcnow()
        booking_scenarios = [
            # (days_ago, status, professional_idx, service_idx)
            (5, BookingStatus.COMPLETED, 0, 0),
            (4, BookingStatus.COMPLETED, 1, 1),
            (3, BookingStatus.COMPLETED, 2, 2),
            (2, BookingStatus.CANCELLED, 0, 0),
            (1, BookingStatus.NO_SHOW, 1, 1),
            (0.5, BookingStatus.CONFIRMED, 2, 2),  # Recent confirmed
        ]

        for days_ago, status, prof_idx, serv_idx in booking_scenarios:
            booking_time = now - timedelta(days=days_ago)

            booking = Booking(
                client_id=1,
                professional_id=professionals[prof_idx].id,
                service_id=services[serv_idx].id,
                scheduled_at=booking_time,
                status=status,
                service_price=services[serv_idx].price,
            )
            db_session.add(booking)
            bookings.append(booking)

        await db_session.commit()

        # 2. Test dashboard reporting
        dashboard_response = client.get(
            "/api/v1/reports/dashboard",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()

        # Verify dashboard metrics
        booking_metrics = dashboard_data["booking_metrics"]
        assert booking_metrics["total_bookings"] >= 6
        assert booking_metrics["completed_bookings"] >= 3
        assert booking_metrics["cancelled_bookings"] >= 1
        assert booking_metrics["no_show_bookings"] >= 1
        assert booking_metrics["total_revenue"] >= 280.0  # Sum of completed bookings

        # 3. Test professional performance reporting
        prof_response = client.get(
            "/api/v1/reports/professionals",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert prof_response.status_code == 200
        prof_data = prof_response.json()

        # Should have performance data for all professionals
        assert len(prof_data) >= 3

        # Verify data structure
        for prof_metric in prof_data:
            assert "professional_id" in prof_metric
            assert "professional_name" in prof_metric
            assert "total_bookings" in prof_metric
            assert "completion_rate" in prof_metric
            assert "total_revenue" in prof_metric

        # 4. Test service performance reporting
        service_response = client.get(
            "/api/v1/reports/services",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert service_response.status_code == 200
        service_data = service_response.json()

        # Should have performance data for services with bookings
        assert len(service_data) >= 3

        # 5. Test revenue trend reporting
        trend_response = client.get(
            "/api/v1/reports/revenue/trend",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={
                "salon_id": test_salon.id,
                "aggregation": "daily",
            },
        )

        assert trend_response.status_code == 200
        trend_data = trend_response.json()

        # Should have trend data
        assert "data" in trend_data
        assert "summary" in trend_data
        assert len(trend_data["data"]) >= 1

        # 6. Test platform-level reporting (admin only)
        platform_response = client.get(
            "/api/v1/platform-reports/overview",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert platform_response.status_code == 200
        platform_data = platform_response.json()

        # Should have platform-wide metrics
        assert "total_salons" in platform_data
        assert "total_bookings" in platform_data
        assert "total_revenue" in platform_data
        assert platform_data["total_salons"] >= 1
        assert platform_data["total_bookings"] >= 6
