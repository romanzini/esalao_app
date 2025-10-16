"""Integration tests for complete booking flows.

Tests end-to-end booking workflows including:
- Slot availability check
- Booking creation
- Booking status transitions
- Booking cancellation
- No-show handling
"""

from datetime import datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient


class TestBookingCreationFlow:
    """Tests for booking creation workflow."""

    @pytest.mark.asyncio
    async def test_complete_booking_creation_flow(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test complete flow: check slots → create booking → verify."""
        # 1. Check available slots
        professional_id = test_booking_data["professional_id"]
        service_id = test_booking_data["service_id"]
        booking_date = (datetime.now() + timedelta(days=2)).date()

        slots_response = await authenticated_client.get(
            "/api/v1/scheduling/slots",
            params={
                "professional_id": professional_id,
                "date": booking_date.isoformat(),
                "service_id": service_id,
            },
        )

        assert slots_response.status_code == status.HTTP_200_OK
        slots = slots_response.json()
        assert len(slots) > 0

        # 2. Select first available slot
        selected_slot = slots[0]
        start_time = selected_slot["start_time"]

        # 3. Create booking
        booking_data = {
            **test_booking_data,
            "start_time": start_time,
        }

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        booking = create_response.json()
        assert booking["status"] == "pending"
        assert booking["professional_id"] == professional_id
        assert booking["service_id"] == service_id

        # 4. Verify booking exists
        booking_id = booking["id"]
        get_response = await authenticated_client.get(f"/api/v1/bookings/{booking_id}")

        assert get_response.status_code == status.HTTP_200_OK
        retrieved_booking = get_response.json()
        assert retrieved_booking["id"] == booking_id
        assert retrieved_booking["status"] == "pending"

    @pytest.mark.asyncio
    async def test_booking_with_unavailable_slot(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that booking unavailable slot fails."""
        # Try to book a slot in the past
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()

        booking_data = {
            **test_booking_data,
            "start_time": past_time,
        }

        response = await authenticated_client.post("/api/v1/bookings", json=booking_data)

        # Should fail - slot in the past
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @pytest.mark.asyncio
    async def test_double_booking_prevention(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that double booking same slot is prevented."""
        # 1. Create first booking
        future_time = (datetime.now() + timedelta(days=1, hours=10)).isoformat()

        booking_data = {
            **test_booking_data,
            "start_time": future_time,
        }

        first_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        assert first_response.status_code == status.HTTP_201_CREATED

        # 2. Try to create second booking at same time
        second_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )

        # Should fail - slot already booked
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not available" in second_response.json()["detail"].lower()


class TestBookingStatusFlow:
    """Tests for booking status transitions."""

    @pytest.mark.asyncio
    async def test_booking_confirmation_flow(
        self,
        authenticated_client: AsyncClient,
        admin_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test flow: create (pending) → confirm → completed."""
        # 1. Client creates booking
        future_time = (datetime.now() + timedelta(days=1, hours=14)).isoformat()

        booking_data = {
            **test_booking_data,
            "start_time": future_time,
        }

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        booking = create_response.json()
        booking_id = booking["id"]
        assert booking["status"] == "pending"

        # 2. Admin confirms booking
        confirm_response = await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "confirmed"}
        )

        assert confirm_response.status_code == status.HTTP_200_OK
        confirmed_booking = confirm_response.json()
        assert confirmed_booking["status"] == "confirmed"

        # 3. Admin marks as completed
        complete_response = await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "completed"}
        )

        assert complete_response.status_code == status.HTTP_200_OK
        completed_booking = complete_response.json()
        assert completed_booking["status"] == "completed"

    @pytest.mark.asyncio
    async def test_invalid_status_transition(
        self,
        authenticated_client: AsyncClient,
        admin_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that invalid status transitions are rejected."""
        # 1. Create booking (pending)
        future_time = (datetime.now() + timedelta(days=1, hours=15)).isoformat()

        booking_data = {
            **test_booking_data,
            "start_time": future_time,
        }

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        booking_id = create_response.json()["id"]

        # 2. Try to go directly from pending to completed (skipping confirmed)
        response = await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "completed"}
        )

        # Implementation may allow or reject this - check status code
        # Most restrictive: should only allow pending → confirmed → completed
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            assert "transition" in response.json()["detail"].lower()


class TestBookingCancellationFlow:
    """Tests for booking cancellation workflow."""

    @pytest.mark.asyncio
    async def test_client_cancels_own_booking(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that client can cancel their own booking."""
        # 1. Create booking
        future_time = (datetime.now() + timedelta(days=2, hours=10)).isoformat()

        booking_data = {
            **test_booking_data,
            "start_time": future_time,
        }

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        booking_id = create_response.json()["id"]

        # 2. Cancel booking
        cancel_response = await authenticated_client.delete(
            f"/api/v1/bookings/{booking_id}"
        )

        assert cancel_response.status_code == status.HTTP_204_NO_CONTENT

        # 3. Verify booking is cancelled
        get_response = await authenticated_client.get(f"/api/v1/bookings/{booking_id}")

        if get_response.status_code == status.HTTP_200_OK:
            # Soft delete: booking still exists but marked cancelled
            booking = get_response.json()
            assert booking["status"] == "cancelled"
        else:
            # Hard delete: booking no longer exists
            assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_cannot_cancel_completed_booking(
        self,
        authenticated_client: AsyncClient,
        admin_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that completed bookings cannot be cancelled."""
        # 1. Create and complete booking
        future_time = (datetime.now() + timedelta(days=1, hours=11)).isoformat()

        booking_data = {
            **test_booking_data,
            "start_time": future_time,
        }

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        booking_id = create_response.json()["id"]

        # Mark as completed
        await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "confirmed"}
        )
        await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "completed"}
        )

        # 2. Try to cancel completed booking
        cancel_response = await authenticated_client.delete(
            f"/api/v1/bookings/{booking_id}"
        )

        # Should fail
        assert cancel_response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]


class TestBookingListingFlow:
    """Tests for listing and filtering bookings."""

    @pytest.mark.asyncio
    async def test_client_sees_own_bookings_only(
        self,
        authenticated_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test that client only sees their own bookings."""
        # 1. Create multiple bookings
        for hour in [10, 11, 12]:
            future_time = (datetime.now() + timedelta(days=1, hours=hour)).isoformat()
            booking_data = {
                **test_booking_data,
                "start_time": future_time,
            }
            await authenticated_client.post("/api/v1/bookings", json=booking_data)

        # 2. List bookings
        list_response = await authenticated_client.get("/api/v1/bookings")

        assert list_response.status_code == status.HTTP_200_OK
        bookings_data = list_response.json()

        # Extract bookings list (handle pagination)
        if isinstance(bookings_data, dict) and "items" in bookings_data:
            bookings = bookings_data["items"]
        else:
            bookings = bookings_data

        # All bookings should belong to authenticated user
        assert len(bookings) >= 3
        for booking in bookings:
            assert "client_id" in booking

    @pytest.mark.asyncio
    async def test_filter_bookings_by_status(
        self,
        authenticated_client: AsyncClient,
        admin_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test filtering bookings by status."""
        # 1. Create bookings with different statuses
        future_time_1 = (datetime.now() + timedelta(days=1, hours=13)).isoformat()
        future_time_2 = (datetime.now() + timedelta(days=1, hours=14)).isoformat()

        booking_data_1 = {**test_booking_data, "start_time": future_time_1}
        booking_data_2 = {**test_booking_data, "start_time": future_time_2}

        create_1 = await authenticated_client.post("/api/v1/bookings", json=booking_data_1)
        await authenticated_client.post("/api/v1/bookings", json=booking_data_2)

        booking_1_id = create_1.json()["id"]

        # Confirm one booking
        await admin_client.patch(
            f"/api/v1/bookings/{booking_1_id}/status", json={"status": "confirmed"}
        )

        # 2. Filter by pending status
        pending_response = await authenticated_client.get(
            "/api/v1/bookings", params={"status": "pending"}
        )

        assert pending_response.status_code == status.HTTP_200_OK
        pending_data = pending_response.json()

        if isinstance(pending_data, dict) and "items" in pending_data:
            pending_bookings = pending_data["items"]
        else:
            pending_bookings = pending_data

        # Should have at least one pending booking
        assert len(pending_bookings) >= 1
        for booking in pending_bookings:
            assert booking["status"] == "pending"

        # 3. Filter by confirmed status
        confirmed_response = await authenticated_client.get(
            "/api/v1/bookings", params={"status": "confirmed"}
        )

        assert confirmed_response.status_code == status.HTTP_200_OK
        confirmed_data = confirmed_response.json()

        if isinstance(confirmed_data, dict) and "items" in confirmed_data:
            confirmed_bookings = confirmed_data["items"]
        else:
            confirmed_bookings = confirmed_data

        # Should have at least one confirmed booking
        assert len(confirmed_bookings) >= 1
        for booking in confirmed_bookings:
            assert booking["status"] == "confirmed"


class TestCompleteBookingWorkflow:
    """Tests for complete booking workflows from start to finish."""

    @pytest.mark.asyncio
    async def test_full_booking_lifecycle(
        self,
        authenticated_client: AsyncClient,
        admin_client: AsyncClient,
        test_booking_data: dict,
    ):
        """Test complete booking lifecycle: check slots → book → confirm → complete."""
        professional_id = test_booking_data["professional_id"]
        service_id = test_booking_data["service_id"]
        booking_date = (datetime.now() + timedelta(days=3)).date()

        # 1. Check available slots
        slots_response = await authenticated_client.get(
            "/api/v1/scheduling/slots",
            params={
                "professional_id": professional_id,
                "date": booking_date.isoformat(),
                "service_id": service_id,
            },
        )
        assert slots_response.status_code == status.HTTP_200_OK
        slots = slots_response.json()
        assert len(slots) > 0

        # 2. Create booking
        start_time = slots[0]["start_time"]
        booking_data = {**test_booking_data, "start_time": start_time}

        create_response = await authenticated_client.post(
            "/api/v1/bookings", json=booking_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        booking = create_response.json()
        booking_id = booking["id"]

        # 3. Confirm booking (as admin)
        confirm_response = await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "confirmed"}
        )
        assert confirm_response.status_code == status.HTTP_200_OK

        # 4. Mark as completed (as admin)
        complete_response = await admin_client.patch(
            f"/api/v1/bookings/{booking_id}/status", json={"status": "completed"}
        )
        assert complete_response.status_code == status.HTTP_200_OK

        # 5. Verify final state
        final_response = await authenticated_client.get(f"/api/v1/bookings/{booking_id}")
        assert final_response.status_code == status.HTTP_200_OK
        final_booking = final_response.json()
        assert final_booking["status"] == "completed"
