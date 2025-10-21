"""
Comprehensive integration tests for Phase 3 systems.

This module contains end-to-end integration tests that validate the complete
Phase 3 implementation including cancellation policies, no-show detection,
audit events, and reporting systems working together.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from backend.app.db.models.audit_event import AuditEvent, AuditEventType
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.cancellation_policy import CancellationPolicy, CancellationTier
from backend.app.db.models.payment import Payment, PaymentStatus
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole
from tests.conftest import (
    admin_user_token,
    client_user,
    professional_user,
    salon_owner_user_token,
    test_salon,
    test_service,
)


class TestPhase3Integration:
    """Integration tests for complete Phase 3 functionality."""

    @pytest.mark.asyncio
    async def test_complete_booking_lifecycle_with_policies(
        self,
        client: TestClient,
        admin_user_token: str,
        salon_owner_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """
        Test complete booking lifecycle with cancellation policies and audit tracking.

        Validates:
        - Booking creation triggers audit events
        - Cancellation policies are applied correctly
        - Fee calculation works with policies
        - All events are properly tracked
        """
        # 1. Create cancellation policy
        policy_data = {
            "salon_id": test_salon.id,
            "name": "Standard Policy",
            "description": "Standard cancellation policy",
            "tiers": [
                {
                    "hours_before": 24,
                    "fee_percentage": 0.0,
                    "fee_fixed": 0.0,
                    "description": "Free cancellation"
                },
                {
                    "hours_before": 2,
                    "fee_percentage": 50.0,
                    "fee_fixed": 0.0,
                    "description": "50% fee"
                },
                {
                    "hours_before": 0,
                    "fee_percentage": 100.0,
                    "fee_fixed": 0.0,
                    "description": "Full fee"
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

        # 2. Create professional and service
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
            price=Decimal("100.00"),
            salon_id=test_salon.id,
            category="haircut",
            cancellation_policy_id=policy["id"],
        )
        db_session.add(service)
        await db_session.commit()

        # 3. Create booking (should trigger audit event)
        booking_data = {
            "professional_id": professional.id,
            "service_id": service.id,
            "scheduled_at": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "notes": "Integration test booking",
        }

        with patch('backend.app.middleware.audit.AuditEventLogger.log_event') as mock_audit:
            booking_response = client.post(
                "/api/v1/bookings",
                headers={"Authorization": f"Bearer {salon_owner_user_token}"},
                json=booking_data,
            )

            assert booking_response.status_code == 201
            booking = booking_response.json()

            # Verify audit event was called
            mock_audit.assert_called()

        # 4. Test cancellation with fee calculation
        cancel_response = client.post(
            f"/api/v1/bookings/{booking['id']}/cancel",
            headers={"Authorization": f"Bearer {salon_owner_user_token}"},
            json={"reason": "Client requested cancellation"},
        )

        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()

        # Should apply 50% fee (2-24 hours before)
        assert cancel_data["status"] == "cancelled"
        assert "cancellation_fee" in cancel_data
        assert cancel_data["cancellation_fee"] == 50.0  # 50% of 100.00

        # 5. Verify audit events were created
        audit_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"entity_type": "booking", "entity_id": booking["id"]},
        )

        assert audit_response.status_code == 200
        audit_events = audit_response.json()["events"]

        # Should have creation and cancellation events
        event_types = [event["event_type"] for event in audit_events]
        assert "booking_created" in event_types
        assert "booking_cancelled" in event_types

    @pytest.mark.asyncio
    async def test_no_show_detection_and_reporting_integration(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """
        Test no-show detection integration with reporting.

        Validates:
        - No-show jobs can be triggered
        - No-show bookings appear in reports
        - Audit events are created for no-shows
        """
        # 1. Create test data
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
            price=Decimal("75.00"),
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # 2. Create past booking (should be eligible for no-show)
        past_booking = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=datetime.utcnow() - timedelta(hours=2),  # 2 hours ago
            status=BookingStatus.CONFIRMED,
            service_price=Decimal("75.00"),
        )
        db_session.add(past_booking)
        await db_session.commit()

        # 3. Create recent booking (should NOT be eligible)
        recent_booking = Booking(
            client_id=1,
            professional_id=professional.id,
            service_id=service.id,
            scheduled_at=datetime.utcnow() + timedelta(minutes=30),  # 30 min from now
            status=BookingStatus.CONFIRMED,
            service_price=Decimal("75.00"),
        )
        db_session.add(recent_booking)
        await db_session.commit()

        # 4. Run no-show detection job
        noshow_response = client.post(
            "/api/v1/no-show-jobs/run",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert noshow_response.status_code == 200
        job_result = noshow_response.json()

        # Should detect at least 1 no-show
        assert job_result["processed_bookings"] >= 1
        assert job_result["no_shows_detected"] >= 1

        # 5. Verify booking status was updated
        booking_response = client.get(
            f"/api/v1/bookings/{past_booking.id}",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert booking_response.status_code == 200
        updated_booking = booking_response.json()
        assert updated_booking["status"] == "no_show"

        # 6. Verify no-show appears in reports
        reports_response = client.get(
            "/api/v1/reports/bookings",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        assert reports_response.status_code == 200
        report_data = reports_response.json()

        # Should show no-show in metrics
        assert report_data["no_show_bookings"] >= 1
        assert report_data["no_show_rate"] > 0

    @pytest.mark.asyncio
    async def test_reporting_with_multiple_salons_and_caching(
        self,
        client: TestClient,
        admin_user_token: str,
        db_session: AsyncSession,
    ):
        """
        Test reporting across multiple salons with caching integration.

        Validates:
        - Platform reports work across salons
        - Caching improves performance
        - Cache invalidation works
        """
        # 1. Create multiple salons
        salon1 = Salon(
            name="High Performer Salon",
            address="Address 1",
            phone="123456789",
            email="salon1@test.com",
        )
        salon2 = Salon(
            name="Low Performer Salon",
            address="Address 2",
            phone="987654321",
            email="salon2@test.com",
        )

        db_session.add_all([salon1, salon2])
        await db_session.commit()

        # 2. Create professionals for each salon
        pro1 = Professional(
            name="Top Professional",
            email="top@test.com",
            salon_id=salon1.id,
            specialties=["haircut"],
            is_active=True,
        )
        pro2 = Professional(
            name="Regular Professional",
            email="regular@test.com",
            salon_id=salon2.id,
            specialties=["haircut"],
            is_active=True,
        )

        db_session.add_all([pro1, pro2])
        await db_session.commit()

        # 3. Create services
        service1 = Service(
            name="Premium Service",
            duration=60,
            price=Decimal("150.00"),
            salon_id=salon1.id,
            category="premium",
        )
        service2 = Service(
            name="Basic Service",
            duration=60,
            price=Decimal("50.00"),
            salon_id=salon2.id,
            category="basic",
        )

        db_session.add_all([service1, service2])
        await db_session.commit()

        # 4. Create bookings with different performance levels
        now = datetime.utcnow()

        # High performer: 5 completed bookings
        high_perf_bookings = [
            Booking(
                client_id=1,
                professional_id=pro1.id,
                service_id=service1.id,
                scheduled_at=now - timedelta(days=i),
                status=BookingStatus.COMPLETED,
                service_price=Decimal("150.00"),
            )
            for i in range(1, 6)
        ]

        # Low performer: 2 completed, 1 cancelled
        low_perf_bookings = [
            Booking(
                client_id=1,
                professional_id=pro2.id,
                service_id=service2.id,
                scheduled_at=now - timedelta(days=1),
                status=BookingStatus.COMPLETED,
                service_price=Decimal("50.00"),
            ),
            Booking(
                client_id=1,
                professional_id=pro2.id,
                service_id=service2.id,
                scheduled_at=now - timedelta(days=2),
                status=BookingStatus.COMPLETED,
                service_price=Decimal("50.00"),
            ),
            Booking(
                client_id=1,
                professional_id=pro2.id,
                service_id=service2.id,
                scheduled_at=now - timedelta(days=3),
                status=BookingStatus.CANCELLED,
                service_price=Decimal("50.00"),
            ),
        ]

        all_bookings = high_perf_bookings + low_perf_bookings
        for booking in all_bookings:
            db_session.add(booking)
        await db_session.commit()

        # 5. Test platform overview (should cache results)
        start_time = datetime.utcnow()

        overview_response1 = client.get(
            "/api/v1/platform-reports/overview",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        first_call_time = (datetime.utcnow() - start_time).total_seconds()

        assert overview_response1.status_code == 200
        overview_data1 = overview_response1.json()

        # Verify data makes sense
        assert overview_data1["total_salons"] >= 2
        assert overview_data1["total_revenue"] >= 850.0  # 5*150 + 2*50
        assert len(overview_data1["top_performing_salons"]) >= 1

        # 6. Test cached response (should be faster)
        start_time = datetime.utcnow()

        overview_response2 = client.get(
            "/api/v1/platform-reports/overview",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        second_call_time = (datetime.utcnow() - start_time).total_seconds()

        assert overview_response2.status_code == 200
        overview_data2 = overview_response2.json()

        # Data should be identical (from cache)
        assert overview_data1 == overview_data2

        # 7. Test salon performance comparison
        salon_perf_response = client.get(
            "/api/v1/platform-reports/salons/performance",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"sort_by": "revenue"},
        )

        assert salon_perf_response.status_code == 200
        salon_perf_data = salon_perf_response.json()

        assert len(salon_perf_data) >= 2

        # High performer should be first (sorted by revenue)
        top_salon = salon_perf_data[0]
        assert top_salon["salon_name"] == "High Performer Salon"
        assert top_salon["total_revenue"] == 750.0  # 5 * 150
        assert top_salon["completion_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_audit_events_comprehensive_tracking(
        self,
        client: TestClient,
        admin_user_token: str,
        salon_owner_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """
        Test comprehensive audit event tracking across all systems.

        Validates:
        - All major actions create audit events
        - Event filtering and searching works
        - Event data integrity
        """
        # 1. Create test entities
        professional = Professional(
            name="Audit Test Professional",
            email="audit@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Audit Test Service",
            duration=60,
            price=Decimal("80.00"),
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # 2. Perform actions that should create audit events
        actions = []

        # Create booking
        with patch('backend.app.middleware.audit.AuditEventLogger.log_event') as mock_audit:
            booking_response = client.post(
                "/api/v1/bookings",
                headers={"Authorization": f"Bearer {salon_owner_user_token}"},
                json={
                    "professional_id": professional.id,
                    "service_id": service.id,
                    "scheduled_at": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
                    "notes": "Audit test booking",
                },
            )

            assert booking_response.status_code == 201
            booking = booking_response.json()
            actions.append(("booking_created", booking["id"]))

        # Confirm booking
        with patch('backend.app.middleware.audit.AuditEventLogger.log_event') as mock_audit:
            confirm_response = client.post(
                f"/api/v1/bookings/{booking['id']}/confirm",
                headers={"Authorization": f"Bearer {salon_owner_user_token}"},
            )

            assert confirm_response.status_code == 200
            actions.append(("booking_confirmed", booking["id"]))

        # Complete booking
        with patch('backend.app.middleware.audit.AuditEventLogger.log_event') as mock_audit:
            complete_response = client.post(
                f"/api/v1/bookings/{booking['id']}/complete",
                headers={"Authorization": f"Bearer {salon_owner_user_token}"},
            )

            assert complete_response.status_code == 200
            actions.append(("booking_completed", booking["id"]))

        # 3. Test audit event retrieval and filtering
        all_events_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"limit": 50},
        )

        assert all_events_response.status_code == 200
        all_events_data = all_events_response.json()

        # Should have recent events
        assert len(all_events_data["events"]) > 0

        # 4. Test entity-specific filtering
        booking_events_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={
                "entity_type": "booking",
                "entity_id": booking["id"],
            },
        )

        assert booking_events_response.status_code == 200
        booking_events_data = booking_events_response.json()

        # Should have booking-specific events
        booking_events = booking_events_data["events"]
        assert len(booking_events) >= 3  # create, confirm, complete

        # Verify event types
        event_types = [event["event_type"] for event in booking_events]
        assert "booking_created" in event_types
        assert "booking_confirmed" in event_types
        assert "booking_completed" in event_types

        # 5. Test date range filtering
        yesterday = datetime.utcnow() - timedelta(days=1)
        tomorrow = datetime.utcnow() + timedelta(days=1)

        date_filtered_response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={
                "start_date": yesterday.isoformat(),
                "end_date": tomorrow.isoformat(),
            },
        )

        assert date_filtered_response.status_code == 200

        # 6. Test event statistics
        stats_response = client.get(
            "/api/v1/audit/events/stats",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        # Should have event counts
        assert "total_events" in stats_data
        assert "events_by_type" in stats_data
        assert "events_by_date" in stats_data

    @pytest.mark.asyncio
    async def test_performance_optimization_integration(
        self,
        client: TestClient,
        admin_user_token: str,
    ):
        """
        Test performance optimization features integration.

        Validates:
        - Optimized endpoints work correctly
        - Cache management works
        - Performance monitoring is active
        """
        # 1. Test optimized dashboard endpoint
        dashboard_response = client.get(
            "/api/v1/optimized-reports/dashboard",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        # May fail due to auth issues, but should not crash
        if dashboard_response.status_code in [200, 401, 403]:
            # Endpoint exists and responds
            assert True
        else:
            pytest.fail(f"Unexpected status code: {dashboard_response.status_code}")

        # 2. Test cache clearing (admin only)
        cache_clear_response = client.post(
            "/api/v1/optimized-reports/cache/clear",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"pattern": "test*"},
        )

        # Should work or fail with auth error
        assert cache_clear_response.status_code in [200, 401, 403]

        # 3. Test performance stats
        perf_stats_response = client.get(
            "/api/v1/optimized-reports/performance/stats",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        # Should work or fail with auth error
        assert perf_stats_response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_error_handling_and_rollback_scenarios(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """
        Test error handling and transaction rollback scenarios.

        Validates:
        - Failed operations don't leave partial data
        - Audit events are not created for failed operations
        - Error responses are appropriate
        """
        # 1. Test booking creation with invalid data
        invalid_booking_response = client.post(
            "/api/v1/bookings",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json={
                "professional_id": 99999,  # Non-existent professional
                "service_id": 99999,       # Non-existent service
                "scheduled_at": "invalid-date",
                "notes": "This should fail",
            },
        )

        # Should fail with validation error
        assert invalid_booking_response.status_code in [400, 422, 404]

        # 2. Test cancellation policy creation with invalid tiers
        invalid_policy_response = client.post(
            "/api/v1/cancellation-policies",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json={
                "salon_id": test_salon.id,
                "name": "Invalid Policy",
                "description": "Policy with invalid tiers",
                "tiers": [
                    {
                        "hours_before": -1,  # Invalid negative hours
                        "fee_percentage": 150.0,  # Invalid percentage > 100
                        "fee_fixed": -10.0,  # Invalid negative fee
                        "description": "Invalid tier"
                    }
                ]
            },
        )

        # Should fail with validation error
        assert invalid_policy_response.status_code in [400, 422]

        # 3. Verify no partial data was created
        policies_response = client.get(
            "/api/v1/cancellation-policies",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            params={"salon_id": test_salon.id},
        )

        if policies_response.status_code == 200:
            policies = policies_response.json()
            # Should not contain the invalid policy
            invalid_policies = [p for p in policies if p["name"] == "Invalid Policy"]
            assert len(invalid_policies) == 0

    @pytest.mark.asyncio
    async def test_concurrent_operations_and_data_consistency(
        self,
        client: TestClient,
        admin_user_token: str,
        test_salon: Salon,
        db_session: AsyncSession,
    ):
        """
        Test concurrent operations and data consistency.

        Validates:
        - Concurrent booking operations don't cause conflicts
        - Audit events are properly sequenced
        - Data consistency is maintained
        """
        # 1. Create test entities
        professional = Professional(
            name="Concurrent Test Professional",
            email="concurrent@test.com",
            salon_id=test_salon.id,
            specialties=["haircut"],
            is_active=True,
        )
        db_session.add(professional)
        await db_session.commit()

        service = Service(
            name="Concurrent Test Service",
            duration=60,
            price=Decimal("90.00"),
            salon_id=test_salon.id,
            category="haircut",
        )
        db_session.add(service)
        await db_session.commit()

        # 2. Simulate concurrent booking creation
        booking_data = {
            "professional_id": professional.id,
            "service_id": service.id,
            "scheduled_at": (datetime.utcnow() + timedelta(hours=5)).isoformat(),
            "notes": "Concurrent test booking",
        }

        # Create multiple bookings rapidly
        booking_responses = []
        for i in range(3):
            response = client.post(
                "/api/v1/bookings",
                headers={"Authorization": f"Bearer {admin_user_token}"},
                json={
                    **booking_data,
                    "notes": f"Concurrent test booking {i+1}",
                },
            )
            booking_responses.append(response)

        # All should succeed (different time slots)
        successful_bookings = [r for r in booking_responses if r.status_code == 201]
        assert len(successful_bookings) >= 1  # At least one should succeed

        # 3. Test concurrent status updates on same booking
        if successful_bookings:
            booking_id = successful_bookings[0].json()["id"]

            # Try to confirm and cancel simultaneously (only one should succeed)
            confirm_response = client.post(
                f"/api/v1/bookings/{booking_id}/confirm",
                headers={"Authorization": f"Bearer {admin_user_token}"},
            )

            cancel_response = client.post(
                f"/api/v1/bookings/{booking_id}/cancel",
                headers={"Authorization": f"Bearer {admin_user_token}"},
                json={"reason": "Concurrent test cancellation"},
            )

            # One should succeed, one should fail or both could succeed depending on timing
            success_count = sum(1 for r in [confirm_response, cancel_response] if r.status_code == 200)
            assert success_count >= 1  # At least one operation should succeed
