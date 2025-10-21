"""Tests for multi-service booking functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.multi_service_booking import MultiServiceBooking, MultiServiceBookingStatus
from backend.app.db.models.booking import BookingStatus
from backend.app.services.multi_service_booking import MultiServiceBookingService


class TestMultiServiceBookingService:
    """Test multi-service booking service functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_session):
        """Create service instance with mocked dependencies."""
        with patch('backend.app.services.multi_service_booking.MultiServiceBookingRepository'), \
             patch('backend.app.services.multi_service_booking.BookingRepository'), \
             patch('backend.app.services.multi_service_booking.ServiceRepository'), \
             patch('backend.app.services.multi_service_booking.SlotService'):
            return MultiServiceBookingService(mock_session)

    @pytest.mark.asyncio
    async def test_check_package_availability_success(self, service):
        """Test successful package availability check."""
        # Mock dependencies
        service.service_repo.get_by_id = AsyncMock()
        service.service_repo.get_by_id.side_effect = [
            AsyncMock(id=1, name="Haircut", duration_minutes=60, price=50.0),
            AsyncMock(id=2, name="Hair Wash", duration_minutes=30, price=25.0)
        ]

        service.slot_service.is_slot_available = AsyncMock(return_value=True)

        # Test data
        services_data = [
            {
                "service_id": 1,
                "professional_id": 1,
                "scheduled_at": datetime.now() + timedelta(days=1)
            },
            {
                "service_id": 2,
                "professional_id": 1,
                "scheduled_at": datetime.now() + timedelta(days=1, hours=1)
            }
        ]

        # Execute
        result = await service.check_package_availability(services_data)

        # Verify
        assert result["is_available"] is True
        assert len(result["suggested_times"]) == 2
        assert result["total_price"] == 75.0
        assert result["total_duration_minutes"] == 90
        assert len(result["conflicts"]) == 0

    @pytest.mark.asyncio
    async def test_check_package_availability_slot_conflict(self, service):
        """Test package availability check with slot conflicts."""
        # Mock dependencies
        service.service_repo.get_by_id = AsyncMock()
        service.service_repo.get_by_id.return_value = AsyncMock(
            id=1, name="Haircut", duration_minutes=60, price=50.0
        )

        service.slot_service.is_slot_available = AsyncMock(return_value=False)
        service.slot_service.find_available_slots = AsyncMock(return_value=[
            {"start_time": datetime.now() + timedelta(days=1, hours=2)}
        ])

        # Test data
        services_data = [
            {
                "service_id": 1,
                "professional_id": 1,
                "scheduled_at": datetime.now() + timedelta(days=1)
            }
        ]

        # Execute
        result = await service.check_package_availability(services_data)

        # Verify
        assert result["is_available"] is False
        assert len(result["conflicts"]) == 1
        assert "not available" in result["conflicts"][0]

    @pytest.mark.asyncio
    async def test_check_package_availability_gap_too_large(self, service):
        """Test package availability check with large gaps between services."""
        # Mock dependencies
        service.service_repo.get_by_id = AsyncMock()
        service.service_repo.get_by_id.side_effect = [
            AsyncMock(id=1, name="Service 1", duration_minutes=60, price=50.0),
            AsyncMock(id=2, name="Service 2", duration_minutes=30, price=25.0)
        ]

        service.slot_service.is_slot_available = AsyncMock(return_value=True)

        # Test data with 2-hour gap
        base_time = datetime.now() + timedelta(days=1)
        services_data = [
            {
                "service_id": 1,
                "professional_id": 1,
                "scheduled_at": base_time
            },
            {
                "service_id": 2,
                "professional_id": 1,
                "scheduled_at": base_time + timedelta(hours=3)  # 2-hour gap after 1-hour service
            }
        ]

        # Execute with 30-minute max gap
        result = await service.check_package_availability(services_data, max_gap_minutes=30)

        # Verify
        assert result["is_available"] is False
        assert any("Gap between services" in conflict for conflict in result["conflicts"])

    @pytest.mark.asyncio
    async def test_create_multi_service_booking_success(self, service):
        """Test successful multi-service booking creation."""
        # Mock availability check
        availability_result = {
            "is_available": True,
            "suggested_times": [
                {
                    "service_id": 1,
                    "professional_id": 1,
                    "service_name": "Haircut",
                    "suggested_time": datetime.now() + timedelta(days=1),
                    "duration_minutes": 60,
                    "price": 50.0
                }
            ],
            "total_price": 50.0,
            "total_duration_minutes": 60,
            "package_start": datetime.now() + timedelta(days=1),
            "package_end": datetime.now() + timedelta(days=1, hours=1),
            "conflicts": []
        }

        service.check_package_availability = AsyncMock(return_value=availability_result)

        # Mock repository operations
        mock_multi_booking = AsyncMock()
        mock_multi_booking.id = 1
        mock_multi_booking.individual_bookings = []

        service.multi_booking_repo.create = AsyncMock(return_value=mock_multi_booking)
        service.service_repo.get_by_id = AsyncMock(return_value=AsyncMock(name="Haircut"))

        mock_booking = AsyncMock()
        service.booking_repo.create = AsyncMock(return_value=mock_booking)
        service.multi_booking_repo.add_individual_booking = AsyncMock()

        # Test data
        services_data = [
            {
                "service_id": 1,
                "professional_id": 1,
                "scheduled_at": datetime.now() + timedelta(days=1)
            }
        ]

        # Execute
        result = await service.create_multi_service_booking(
            client_id=1,
            package_name="Test Package",
            services_data=services_data
        )

        # Verify
        assert result == mock_multi_booking
        service.multi_booking_repo.create.assert_called_once()
        service.booking_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_multi_service_booking_unavailable(self, service):
        """Test multi-service booking creation with unavailable slots."""
        # Mock availability check failure
        availability_result = {
            "is_available": False,
            "conflicts": ["Service not available"]
        }

        service.check_package_availability = AsyncMock(return_value=availability_result)

        # Test data
        services_data = [
            {
                "service_id": 1,
                "professional_id": 1,
                "scheduled_at": datetime.now() + timedelta(days=1)
            }
        ]

        # Execute and verify exception
        with pytest.raises(ValueError, match="Package not available"):
            await service.create_multi_service_booking(
                client_id=1,
                package_name="Test Package",
                services_data=services_data
            )

    @pytest.mark.asyncio
    async def test_confirm_multi_service_booking_success(self, service):
        """Test successful multi-service booking confirmation."""
        # Mock booking
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.status = MultiServiceBookingStatus.PENDING
        mock_booking.individual_bookings = [
            AsyncMock(status=BookingStatus.PENDING),
            AsyncMock(status=BookingStatus.PENDING)
        ]

        service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)
        service.multi_booking_repo.update_status = AsyncMock()

        # Execute
        result = await service.confirm_multi_service_booking(1)

        # Verify
        service.multi_booking_repo.update_status.assert_called_once_with(
            1, MultiServiceBookingStatus.CONFIRMED
        )

        # Check that individual bookings were updated
        for booking in mock_booking.individual_bookings:
            assert booking.status == BookingStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_confirm_multi_service_booking_wrong_status(self, service):
        """Test multi-service booking confirmation with wrong status."""
        # Mock booking with wrong status
        mock_booking = AsyncMock()
        mock_booking.status = MultiServiceBookingStatus.CONFIRMED

        service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)

        # Execute and verify exception
        with pytest.raises(ValueError, match="Cannot confirm booking in status"):
            await service.confirm_multi_service_booking(1)

    @pytest.mark.asyncio
    async def test_cancel_multi_service_booking_success(self, service):
        """Test successful multi-service booking cancellation."""
        # Mock booking
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.can_be_cancelled = True
        mock_booking.individual_bookings = [
            AsyncMock(status=BookingStatus.PENDING),
            AsyncMock(status=BookingStatus.CONFIRMED)
        ]

        service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)
        service.multi_booking_repo.update_status = AsyncMock()

        # Execute
        result = await service.cancel_multi_service_booking(
            1, "User request", 1, partial_cancel=False
        )

        # Verify
        service.multi_booking_repo.update_status.assert_called_once_with(
            1, MultiServiceBookingStatus.CANCELLED, "User request", 1
        )

        # Check that individual bookings were cancelled
        for booking in mock_booking.individual_bookings:
            assert booking.status == BookingStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_multi_service_booking_cannot_cancel(self, service):
        """Test multi-service booking cancellation when not allowed."""
        # Mock booking that cannot be cancelled
        mock_booking = AsyncMock()
        mock_booking.can_be_cancelled = False
        mock_booking.status = MultiServiceBookingStatus.COMPLETED

        service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)

        # Execute and verify exception
        with pytest.raises(ValueError, match="Cannot cancel booking in status"):
            await service.cancel_multi_service_booking(1, "User request", 1)

    @pytest.mark.asyncio
    async def test_update_individual_booking_status(self, service):
        """Test updating individual booking status."""
        # Mock booking
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.multi_service_booking_id = 1
        mock_booking.status = BookingStatus.PENDING

        mock_multi_booking = AsyncMock()

        service.booking_repo.get_by_id = AsyncMock(return_value=mock_booking)
        service.multi_booking_repo.calculate_and_update_status = AsyncMock()
        service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_multi_booking)

        # Execute
        booking, multi_booking = await service.update_individual_booking_status(
            1, BookingStatus.COMPLETED
        )

        # Verify
        assert mock_booking.status == BookingStatus.COMPLETED
        assert mock_booking.completed_at is not None
        service.multi_booking_repo.calculate_and_update_status.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_update_individual_booking_status_not_multi_service(self, service):
        """Test updating individual booking status for non-multi-service booking."""
        # Mock booking without multi-service association
        mock_booking = AsyncMock()
        mock_booking.multi_service_booking_id = None

        service.booking_repo.get_by_id = AsyncMock(return_value=mock_booking)

        # Execute and verify exception
        with pytest.raises(ValueError, match="not part of a multi-service package"):
            await service.update_individual_booking_status(1, BookingStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_get_package_suggestions(self, service):
        """Test getting package suggestions."""
        # Execute
        suggestions = await service.get_package_suggestions(
            client_id=1,
            duration_preference="short"
        )

        # Verify
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

        # Check that suggestions are filtered by duration
        for suggestion in suggestions:
            assert suggestion["estimated_duration"] <= 90

    @pytest.mark.asyncio
    async def test_calculate_package_discount(self, service):
        """Test package discount calculation."""
        # Mock service data
        service.service_repo.get_by_id = AsyncMock()
        service.service_repo.get_by_id.side_effect = [
            AsyncMock(id=1, name="Service 1", price=50.0),
            AsyncMock(id=2, name="Service 2", price=30.0)
        ]

        # Test data
        services_data = [
            {"service_id": 1},
            {"service_id": 2}
        ]

        # Execute
        result = await service.calculate_package_discount(services_data, 15.0)

        # Verify
        assert result["total_individual_price"] == 80.0
        assert result["discount_percentage"] == 15.0
        assert result["discount_amount"] == 12.0
        assert result["package_price"] == 68.0
        assert result["savings"] == 12.0
        assert len(result["service_details"]) == 2
