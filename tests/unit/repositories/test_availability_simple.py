"""Tests for availability repository basic functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import time

from backend.app.db.repositories.availability import AvailabilityRepository
from backend.app.db.models.availability import DayOfWeek


class TestAvailabilityRepositoryBasic:
    """Test basic availability repository functionality."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def availability_repo(self, mock_session):
        """AvailabilityRepository instance with mocked session."""
        return AvailabilityRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initialization."""
        repo = AvailabilityRepository(mock_session)
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, availability_repo, mock_session):
        """Test get_by_id when availability not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await availability_repo.get_by_id(999)

        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_professional_empty_result(self, availability_repo, mock_session):
        """Test get_by_professional with empty result."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await availability_repo.get_by_professional(1)

        # Should return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_professional_and_day_empty(self, availability_repo, mock_session):
        """Test get_by_professional_and_day with no results."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await availability_repo.get_by_professional_and_day(1, DayOfWeek.MONDAY)

        # Should return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_update_nonexistent_availability(self, availability_repo, mock_session):
        """Test update on non-existent availability."""
        # Mock get_by_id to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call update method
        result = await availability_repo.update(
            availability_id=999,
            start_time=time(9, 0),
            end_time=time(17, 0)
        )

        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_availability(self, availability_repo, mock_session):
        """Test delete on non-existent availability."""
        # Mock get_by_id to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call delete method
        result = await availability_repo.delete(999)

        # Should return False
        assert result is False


class TestAvailabilityRepositoryQueries:
    """Test availability repository query building."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def availability_repo(self, mock_session):
        """AvailabilityRepository instance."""
        return AvailabilityRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_all_empty(self, availability_repo, mock_session):
        """Test get_all with empty database."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await availability_repo.get_all()

        assert result == []
        mock_session.execute.assert_called_once()


class TestDayOfWeekEnum:
    """Test DayOfWeek enum functionality."""

    def test_day_of_week_values(self):
        """Test DayOfWeek enum values."""
        assert DayOfWeek.MONDAY.value == 0
        assert DayOfWeek.TUESDAY.value == 1
        assert DayOfWeek.WEDNESDAY.value == 2
        assert DayOfWeek.THURSDAY.value == 3
        assert DayOfWeek.FRIDAY.value == 4
        assert DayOfWeek.SATURDAY.value == 5
        assert DayOfWeek.SUNDAY.value == 6

    def test_day_of_week_enum_members(self):
        """Test DayOfWeek enum has all expected members."""
        expected_days = [
            'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY',
            'FRIDAY', 'SATURDAY', 'SUNDAY'
        ]

        for day in expected_days:
            assert hasattr(DayOfWeek, day)

    def test_day_of_week_comparison(self):
        """Test DayOfWeek enum comparison."""
        monday1 = DayOfWeek.MONDAY
        monday2 = DayOfWeek.MONDAY
        tuesday = DayOfWeek.TUESDAY

        assert monday1 == monday2
        assert monday1 != tuesday
        assert monday1.value < tuesday.value


class TestAvailabilityRepositoryEdgeCases:
    """Test edge cases for availability repository."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def availability_repo(self, mock_session):
        """AvailabilityRepository instance."""
        return AvailabilityRepository(mock_session)

    @pytest.mark.asyncio
    async def test_repository_session_access(self, availability_repo, mock_session):
        """Test repository session access."""
        assert availability_repo.session == mock_session

    def test_time_validation_concept(self):
        """Test time validation conceptual test."""
        # Test that Python time objects work as expected
        start_time = time(9, 0)   # 9:00 AM
        end_time = time(17, 0)    # 5:00 PM

        assert start_time < end_time
        assert start_time.hour == 9
        assert end_time.hour == 17
