"""Tests for overbooking service functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from backend.app.services.overbooking import OverbookingService
from backend.app.db.models.overbooking import OverbookingConfig, OverbookingScope, OverbookingTimeframe
from backend.app.db.models.booking import BookingStatus


class TestOverbookingService:
    """Test overbooking service functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock overbooking configuration."""
        config = OverbookingConfig(
            id=uuid4(),
            name="Test Config",
            description="Test configuration",
            scope=OverbookingScope.SALON,
            salon_id=uuid4(),
            max_overbooking_percentage=20.0,
            timeframe=OverbookingTimeframe.HOURLY,
            min_historical_bookings=10,
            historical_period_days=30,
            min_no_show_rate=5.0,
            max_no_show_rate=30.0,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return config

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_booking_repo(self):
        """Mock booking repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_overbooking_repo(self):
        """Mock overbooking repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def overbooking_service(self, mock_session, mock_booking_repo, mock_overbooking_repo):
        """Create overbooking service with mocked dependencies."""
        service = OverbookingService(mock_session)
        service.booking_repo = mock_booking_repo
        service.overbooking_repo = mock_overbooking_repo
        return service

    @pytest.mark.asyncio
    async def test_calculate_available_capacity_no_config(self, overbooking_service, mock_overbooking_repo, mock_booking_repo):
        """Test capacity calculation with no overbooking configuration."""
        # Setup - no config found
        mock_overbooking_repo.get_effective_config.return_value = None

        # Mock overlapping bookings (this is what _count_current_bookings uses)
        mock_bookings_list = [{"id": "1"}, {"id": "2"}]  # 2 bookings
        mock_booking_repo.find_overlapping_bookings.return_value = mock_bookings_list

        target_datetime = datetime.utcnow()

        result = await overbooking_service.calculate_available_capacity(
            professional_id=1,
            target_datetime=target_datetime,
            service_duration_minutes=60,
            base_capacity=5
        )

        assert result["base_capacity"] == 5
        assert result["overbooking_enabled"] is False
        assert result["max_capacity"] == 5
        assert result["current_bookings"] == 2
        assert result["available_slots"] == 3

    @pytest.mark.asyncio
    async def test_can_accept_booking_basic(self, overbooking_service, mock_overbooking_repo, mock_booking_repo):
        """Test basic booking acceptance check."""
        # Setup - no config, should accept based on base capacity
        mock_overbooking_repo.get_effective_config.return_value = None
        mock_booking_repo.find_overlapping_bookings.return_value = []  # No overlapping bookings

        target_datetime = datetime.utcnow()

        result = await overbooking_service.can_accept_booking(
            professional_id=1,
            target_datetime=target_datetime,
            service_duration_minutes=60
        )

        # Should check capacity calculation
        can_accept, capacity_info = result
        assert isinstance(can_accept, bool)
        assert isinstance(capacity_info, dict)

    @pytest.mark.asyncio
    async def test_get_overbooking_status(self, overbooking_service, mock_overbooking_repo):
        """Test getting overbooking status."""
        # Setup mock config
        mock_config = OverbookingConfig(
            id=uuid4(),
            name="Test Config",
            scope=OverbookingScope.SALON,
            salon_id=uuid4(),
            max_overbooking_percentage=20.0,
            is_active=True
        )
        mock_overbooking_repo.get_effective_config.return_value = mock_config

        result = await overbooking_service.get_overbooking_status(
            professional_id=1,
            target_date=datetime.utcnow().date()
        )

        assert "config" in result
        assert "is_enabled" in result
        assert result["is_enabled"] is True
