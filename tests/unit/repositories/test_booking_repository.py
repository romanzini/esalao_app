"""Unit tests for BookingRepository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.models.booking import Booking, BookingStatus


class TestBookingRepository:
    """Test BookingRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def booking_repo(self, mock_session):
        """BookingRepository instance with mocked session."""
        return BookingRepository(mock_session)

    @pytest.fixture
    def sample_booking(self):
        """Sample booking data."""
        return Booking(
            id=1,
            client_id=1,
            professional_id=1,
            service_id=1,
            scheduled_at=datetime.utcnow(),
            duration_minutes=60,
            status=BookingStatus.PENDING,
            service_price=50.00,
            notes="Test booking",
        )

    @pytest.mark.asyncio
    async def test_create_booking_success(self, booking_repo, mock_session):
        """Test successful booking creation."""
        # Mock session methods
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        scheduled_at = datetime.utcnow()

        # Call the method
        result = await booking_repo.create(
            client_id=1,
            professional_id=1,
            service_id=1,
            scheduled_at=scheduled_at,
            duration_minutes=60,
            service_price=50.00,
            notes="Test booking",
        )

        # Verify calls
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Check that a Booking was added
        added_booking = mock_session.add.call_args[0][0]
        assert isinstance(added_booking, Booking)
        assert added_booking.client_id == 1
        assert added_booking.professional_id == 1

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, booking_repo, mock_session, sample_booking):
        """Test get_by_id returns booking when found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_booking
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.get_by_id(1)

        # Assert
        assert result == sample_booking
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, booking_repo, mock_session):
        """Test get_by_id returns None when not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.get_by_id(999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_client_id(self, booking_repo, mock_session):
        """Test listing bookings by client ID."""
        # Mock bookings list
        bookings = [
            Booking(id=1, client_id=1, professional_id=1, service_id=1),
            Booking(id=2, client_id=1, professional_id=2, service_id=2),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = bookings
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.list_by_client_id(client_id=1)

        # Assert
        assert result == bookings
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_professional_id(self, booking_repo, mock_session):
        """Test listing bookings by professional ID."""
        # Mock bookings list
        bookings = [
            Booking(id=1, client_id=1, professional_id=1, service_id=1),
            Booking(id=3, client_id=2, professional_id=1, service_id=3),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = bookings
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.list_by_professional_id(professional_id=1)

        # Assert
        assert result == bookings
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_status(self, booking_repo, mock_session):
        """Test listing bookings by status."""
        # Mock bookings list
        confirmed_bookings = [
            Booking(id=1, client_id=1, status=BookingStatus.CONFIRMED),
            Booking(id=2, client_id=2, status=BookingStatus.CONFIRMED),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = confirmed_bookings
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.list_by_status(status=BookingStatus.CONFIRMED)

        # Assert
        assert result == confirmed_bookings
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status(self, booking_repo, mock_session, sample_booking):
        """Test updating booking status."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_booking
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        # Call method
        result = await booking_repo.update_status(
            booking_id=1,
            new_status=BookingStatus.CONFIRMED,
        )

        # Assert
        assert result == sample_booking
        assert sample_booking.status == BookingStatus.CONFIRMED
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, booking_repo, mock_session):
        """Test updating status of non-existent booking."""
        # Mock query result - no booking found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.update_status(
            booking_id=999,
            new_status=BookingStatus.CONFIRMED,
        )

        # Assert
        assert result is None



    @pytest.mark.asyncio
    async def test_exists_by_id_true(self, booking_repo, mock_session):
        """Test exists_by_id returns True when booking exists."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.exists_by_id(1)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_by_id_false(self, booking_repo, mock_session):
        """Test exists_by_id returns False when booking doesn't exist."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await booking_repo.exists_by_id(999)

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()
