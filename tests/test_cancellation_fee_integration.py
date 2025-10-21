"""
Tests for cancellation fee integration in booking endpoints.

Tests the integration between booking system and cancellation policies.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.booking import BookingStatus
from backend.app.db.models.cancellation_policy import CancellationPolicyStatus


class TestCancellationFeeIntegration:
    """Test suite for cancellation fee integration in booking endpoints."""

    @pytest.fixture
    async def sample_cancellation_policy(self, db_session: AsyncSession):
        """Create a sample cancellation policy for testing."""
        from backend.app.db.repositories.cancellation_policy import CancellationPolicyRepository

        policy_repo = CancellationPolicyRepository(db_session)

        # Create policy
        policy = await policy_repo.create_policy(
            name="Test Policy",
            description="Policy for testing",
            salon_id=None,
            is_default=True,
            effective_from=datetime.utcnow(),
            effective_until=None,
            status=CancellationPolicyStatus.ACTIVE,
        )

        # Create tiers
        await policy_repo.create_tier(
            policy_id=policy.id,
            name="No Refund",
            advance_notice_hours=0,
            fee_type="percentage",
            fee_value=Decimal("100.00"),
            allows_refund=False,
            display_order=0,
        )

        await policy_repo.create_tier(
            policy_id=policy.id,
            name="50% Fee",
            advance_notice_hours=24,
            fee_type="percentage",
            fee_value=Decimal("50.00"),
            allows_refund=True,
            display_order=1,
        )

        await policy_repo.create_tier(
            policy_id=policy.id,
            name="No Fee",
            advance_notice_hours=72,
            fee_type="percentage",
            fee_value=Decimal("0.00"),
            allows_refund=True,
            display_order=2,
        )

        await db_session.commit()
        return policy

    @pytest.fixture
    async def sample_booking(self, client: AsyncClient, admin_headers, sample_cancellation_policy):
        """Create a sample booking for testing."""
        booking_data = {
            "professional_id": 1,
            "service_id": 1,
            "scheduled_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "notes": "Test booking for cancellation"
        }

        response = await client.post(
            "/v1/bookings",
            json=booking_data,
            headers=admin_headers
        )

        assert response.status_code == 201
        return response.json()

    async def test_booking_creation_includes_policy(self, client: AsyncClient, admin_headers, sample_cancellation_policy):
        """Test that booking creation includes applicable cancellation policy."""
        booking_data = {
            "professional_id": 1,
            "service_id": 1,
            "scheduled_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "notes": "Test booking"
        }

        response = await client.post(
            "/v1/bookings",
            json=booking_data,
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()

        # Check that policy was applied
        assert data["cancellation_policy_id"] == sample_cancellation_policy.id

    async def test_calculate_cancellation_fee_current_time(self, client: AsyncClient, admin_headers, sample_booking):
        """Test calculating cancellation fee for current time."""
        booking_id = sample_booking["id"]

        response = await client.get(
            f"/v1/bookings/{booking_id}/cancellation-fee",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "fee_amount" in data
        assert "refund_amount" in data
        assert "tier_name" in data
        assert "policy_name" in data
        assert "advance_hours" in data
        assert "allows_refund" in data

        # Should be no fee since booking is 2 days away (> 72h)
        assert data["fee_amount"] == 0.0
        assert data["tier_name"] == "No Fee"
        assert data["allows_refund"] is True

    async def test_calculate_cancellation_fee_hypothetical_time(self, client: AsyncClient, admin_headers, sample_booking):
        """Test calculating cancellation fee for hypothetical cancellation time."""
        booking_id = sample_booking["id"]

        # Calculate fee if cancelled 12 hours before appointment (should be 50% fee)
        scheduled_at = datetime.fromisoformat(sample_booking["scheduled_at"].replace('Z', '+00:00'))
        cancellation_time = (scheduled_at - timedelta(hours=12)).isoformat()

        response = await client.get(
            f"/v1/bookings/{booking_id}/cancellation-fee",
            params={"cancellation_time": cancellation_time},
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should be 50% fee (12h < 24h advance notice)
        expected_fee = sample_booking["service_price"] * 0.5
        assert data["fee_amount"] == expected_fee
        assert data["tier_name"] == "50% Fee"
        assert data["allows_refund"] is True

    async def test_calculate_cancellation_fee_no_refund_scenario(self, client: AsyncClient, admin_headers, sample_booking):
        """Test calculating cancellation fee for no-refund scenario."""
        booking_id = sample_booking["id"]

        # Calculate fee if cancelled after appointment time (no refund)
        scheduled_at = datetime.fromisoformat(sample_booking["scheduled_at"].replace('Z', '+00:00'))
        cancellation_time = (scheduled_at + timedelta(hours=1)).isoformat()

        response = await client.get(
            f"/v1/bookings/{booking_id}/cancellation-fee",
            params={"cancellation_time": cancellation_time},
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should be 100% fee (no advance notice)
        assert data["fee_amount"] == sample_booking["service_price"]
        assert data["tier_name"] == "No Refund"
        assert data["allows_refund"] is False
        assert data["refund_amount"] == 0.0

    async def test_calculate_cancellation_fee_nonexistent_booking(self, client: AsyncClient, admin_headers):
        """Test calculating cancellation fee for non-existent booking."""
        response = await client.get(
            "/v1/bookings/99999/cancellation-fee",
            headers=admin_headers
        )

        assert response.status_code == 404

    async def test_calculate_cancellation_fee_access_control(self, client: AsyncClient, sample_booking):
        """Test access control for cancellation fee calculation."""
        booking_id = sample_booking["id"]

        # Test without authentication
        response = await client.get(f"/v1/bookings/{booking_id}/cancellation-fee")
        assert response.status_code == 401

    async def test_can_cancel_booking_integration(self, client: AsyncClient, admin_headers, sample_booking):
        """Test the can-cancel endpoint integration."""
        booking_id = sample_booking["id"]

        response = await client.get(
            f"/v1/bookings/{booking_id}/can-cancel",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should be able to cancel since booking is in the future
        assert data["can_cancel"] is True
        assert "fee_info" in data

    async def test_actual_cancellation_with_policy(self, client: AsyncClient, admin_headers, sample_booking):
        """Test actual booking cancellation applies the policy correctly."""
        booking_id = sample_booking["id"]

        # First check current fee
        fee_response = await client.get(
            f"/v1/bookings/{booking_id}/cancellation-fee",
            headers=admin_headers
        )
        assert fee_response.status_code == 200
        expected_fee = fee_response.json()["fee_amount"]

        # Cancel the booking
        cancel_data = {
            "reason": "Test cancellation",
            "cancellation_time": datetime.utcnow().isoformat()
        }

        response = await client.post(
            f"/v1/bookings/{booking_id}/cancel-with-policy",
            json=cancel_data,
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cancellation_fee"] == expected_fee
        assert "refund_amount" in data
        assert "policy_applied" in data

    async def test_multiple_bookings_different_policies(self, client: AsyncClient, admin_headers, db_session: AsyncSession):
        """Test that different bookings can have different policies."""
        from backend.app.db.repositories.cancellation_policy import CancellationPolicyRepository

        policy_repo = CancellationPolicyRepository(db_session)

        # Create a second policy for salon-specific use
        salon_policy = await policy_repo.create_policy(
            name="Salon Policy",
            description="Salon-specific policy",
            salon_id=1,
            is_default=False,
            effective_from=datetime.utcnow(),
            effective_until=None,
            status=CancellationPolicyStatus.ACTIVE,
        )

        await policy_repo.create_tier(
            policy_id=salon_policy.id,
            name="Strict Fee",
            advance_notice_hours=24,
            fee_type="fixed",
            fee_value=Decimal("25.00"),
            allows_refund=True,
            display_order=0,
        )

        await db_session.commit()

        # Create booking (should use default policy since no salon_id in service)
        booking_data = {
            "professional_id": 1,
            "service_id": 1,
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "notes": "Test booking"
        }

        response = await client.post(
            "/v1/bookings",
            json=booking_data,
            headers=admin_headers
        )

        assert response.status_code == 201
        # Note: In real implementation, this would depend on how salon_id is determined

    async def test_fee_calculation_edge_cases(self, client: AsyncClient, admin_headers, sample_booking):
        """Test edge cases in fee calculation."""
        booking_id = sample_booking["id"]

        # Test exactly at tier boundary (24 hours)
        scheduled_at = datetime.fromisoformat(sample_booking["scheduled_at"].replace('Z', '+00:00'))
        cancellation_time = (scheduled_at - timedelta(hours=24)).isoformat()

        response = await client.get(
            f"/v1/bookings/{booking_id}/cancellation-fee",
            params={"cancellation_time": cancellation_time},
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should apply the 24h tier (50% fee)
        assert data["tier_name"] == "50% Fee"
        assert data["advance_hours"] == 24

    async def test_booking_status_integration(self, client: AsyncClient, admin_headers, sample_booking):
        """Test that booking status affects cancellation calculations."""
        booking_id = sample_booking["id"]

        # First cancel the booking
        cancel_data = {
            "reason": "Test cancellation",
            "cancellation_time": datetime.utcnow().isoformat()
        }

        await client.post(
            f"/v1/bookings/{booking_id}/cancel-with-policy",
            json=cancel_data,
            headers=admin_headers
        )

        # Try to calculate fee for already cancelled booking
        response = await client.get(
            f"/v1/bookings/{booking_id}/cancellation-fee",
            headers=admin_headers
        )

        # Should return error for cancelled booking
        assert response.status_code == 400
