"""Unit tests for ServiceRepository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from backend.app.db.repositories.service import ServiceRepository
from backend.app.db.models.service import Service


class TestServiceRepository:
    """Test ServiceRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def service_repo(self, mock_session):
        """ServiceRepository instance with mocked session."""
        return ServiceRepository(mock_session)

    @pytest.fixture
    def sample_service(self):
        """Sample service data."""
        return Service(
            id=1,
            salon_id=1,
            name="Haircut",
            description="Professional haircut service",
            duration_minutes=60,
            price=50.00,
            category="Hair",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_create_service_success(self, service_repo, mock_session):
        """Test successful service creation."""
        # Mock session methods
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        # Call the method
        result = await service_repo.create(
            salon_id=1,
            name="Haircut",
            description="Professional haircut service",
            duration_minutes=60,
            price=50.00,
            category="Hair",
        )

        # Verify calls
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Check that a Service was added and returned
        added_service = mock_session.add.call_args[0][0]
        assert isinstance(added_service, Service)
        assert added_service.name == "Haircut"
        assert added_service.salon_id == 1
        assert result.name == "Haircut"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service_repo, mock_session, sample_service):
        """Test get_by_id returns service when found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_service
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.get_by_id(1)

        # Assert
        assert result == sample_service
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service_repo, mock_session):
        """Test get_by_id returns None when not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.get_by_id(999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_salon_id(self, service_repo, mock_session):
        """Test listing all services for a salon by salon_id."""
        # Mock services list
        services = [
            Service(id=1, salon_id=1, name="Haircut", duration_minutes=60, price=50.00),
            Service(id=2, salon_id=1, name="Manicure", duration_minutes=30, price=25.00),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = services
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.list_by_salon_id(salon_id=1)

        # Assert
        assert result == services
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_price_range(self, service_repo, mock_session):
        """Test listing services by price range."""
        # Mock services list
        services = [
            Service(id=1, salon_id=1, name="Haircut", duration_minutes=60, price=50.00),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = services
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.list_by_price_range(salon_id=1, min_price=40.00, max_price=60.00)

        # Assert
        assert result == services
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_category(self, service_repo, mock_session):
        """Test listing services by category."""
        # Mock services in category
        hair_services = [
            Service(id=1, salon_id=1, name="Haircut", category="Hair", duration_minutes=60, price=50.00),
            Service(id=2, salon_id=1, name="Hair Wash", category="Hair", duration_minutes=30, price=20.00),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = hair_services
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.list_by_category(salon_id=1, category="Hair")

        # Assert
        assert result == hair_services
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_service(self, service_repo, mock_session, sample_service):
        """Test updating service data."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_service
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Call method with updates
        result = await service_repo.update(
            service_id=1,
            name="Premium Haircut",
            price=75.00,
        )

        # Assert
        assert result == sample_service
        assert sample_service.name == "Premium Haircut"
        assert sample_service.price == 75.00
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_service_not_found(self, service_repo, mock_session):
        """Test updating non-existent service."""
        # Mock query result - no service found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.update(service_id=999, name="New Name")

        # Assert
        assert result is None
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_service(self, service_repo, mock_session, sample_service):
        """Test soft deleting a service (set is_active=False)."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_service
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Call method
        result = await service_repo.delete(service_id=1)

        # Assert
        assert result is True
        assert sample_service.is_active is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_service_not_found(self, service_repo, mock_session):
        """Test deleting non-existent service."""
        # Mock query result - no service found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.delete(service_id=999)

        # Assert
        assert result is False
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_exists_by_id_true(self, service_repo, mock_session):
        """Test exists_by_id returns True when service exists."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.exists_by_id(1)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_by_id_false(self, service_repo, mock_session):
        """Test exists_by_id returns False when service doesn't exist."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await service_repo.exists_by_id(999)

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()
