"""Simple tests for SalonRepository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.salon import SalonRepository
from backend.app.db.models.salon import Salon


class TestSalonRepositoryBasic:
    """Test basic SalonRepository functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def salon_repository(self, mock_session):
        """Create SalonRepository instance."""
        return SalonRepository(mock_session)

    def test_salon_repository_initialization(self, mock_session):
        """Test SalonRepository can be initialized."""
        repo = SalonRepository(mock_session)
        assert repo is not None
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_create_salon_basic(self, salon_repository, mock_session):
        """Test basic salon creation."""
        # Mock salon data
        salon_data = {
            "name": "Test Salon",
            "address": "123 Test St",
            "phone": "123456789"
        }

        # Mock the salon instance
        mock_salon = MagicMock(spec=Salon)
        mock_salon.id = 1
        mock_salon.name = salon_data["name"]

        # Mock session operations
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Mock the Salon constructor
        with pytest.mock.patch('backend.app.db.repositories.salon.Salon', return_value=mock_salon):
            result = await salon_repository.create(salon_data)

        # Verify session operations
        mock_session.add.assert_called_once_with(mock_salon)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_salon)

        assert result == mock_salon

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, salon_repository, mock_session):
        """Test getting salon by ID when found."""
        salon_id = 1
        mock_salon = MagicMock(spec=Salon)
        mock_salon.id = salon_id

        # Mock session.get
        mock_session.get = AsyncMock(return_value=mock_salon)

        result = await salon_repository.get_by_id(salon_id)

        mock_session.get.assert_called_once_with(Salon, salon_id)
        assert result == mock_salon

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, salon_repository, mock_session):
        """Test getting salon by ID when not found."""
        salon_id = 999

        # Mock session.get returning None
        mock_session.get = AsyncMock(return_value=None)

        result = await salon_repository.get_by_id(salon_id)

        mock_session.get.assert_called_once_with(Salon, salon_id)
        assert result is None


class TestSalonRepositoryQueries:
    """Test SalonRepository query methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def salon_repository(self, mock_session):
        """Create SalonRepository instance."""
        return SalonRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_all_empty(self, salon_repository, mock_session):
        """Test getting all salons when empty."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await salon_repository.get_all()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_data(self, salon_repository, mock_session):
        """Test getting all salons with data."""
        # Create mock salons
        mock_salon1 = MagicMock(spec=Salon)
        mock_salon1.id = 1
        mock_salon2 = MagicMock(spec=Salon)
        mock_salon2.id = 2

        # Mock result with salons
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_salon1, mock_salon2]

        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await salon_repository.get_all()

        assert len(result) == 2
        assert result[0] == mock_salon1
        assert result[1] == mock_salon2
        mock_session.execute.assert_called_once()


class TestSalonRepositoryUpdates:
    """Test SalonRepository update and delete operations."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def salon_repository(self, mock_session):
        """Create SalonRepository instance."""
        return SalonRepository(mock_session)

    @pytest.mark.asyncio
    async def test_update_salon_basic(self, salon_repository, mock_session):
        """Test basic salon update."""
        salon_id = 1
        update_data = {"name": "Updated Salon Name"}

        # Mock existing salon
        mock_salon = MagicMock(spec=Salon)
        mock_salon.id = salon_id
        mock_salon.name = "Old Name"

        # Mock get_by_id
        salon_repository.get_by_id = AsyncMock(return_value=mock_salon)

        # Mock session operations
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await salon_repository.update(salon_id, update_data)

        # Verify salon was updated
        assert mock_salon.name == "Updated Salon Name"
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_salon)
        assert result == mock_salon

    @pytest.mark.asyncio
    async def test_delete_salon_basic(self, salon_repository, mock_session):
        """Test basic salon deletion."""
        salon_id = 1

        # Mock existing salon
        mock_salon = MagicMock(spec=Salon)
        mock_salon.id = salon_id

        # Mock get_by_id
        salon_repository.get_by_id = AsyncMock(return_value=mock_salon)

        # Mock session operations
        mock_session.delete = MagicMock()
        mock_session.commit = AsyncMock()

        result = await salon_repository.delete(salon_id)

        # Verify deletion
        mock_session.delete.assert_called_once_with(mock_salon)
        mock_session.commit.assert_called_once()
        assert result is True
