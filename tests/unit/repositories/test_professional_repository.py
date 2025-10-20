"""Unit tests for ProfessionalRepository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import List

from backend.app.db.repositories.professional import ProfessionalRepository
from backend.app.db.models.professional import Professional


class TestProfessionalRepository:
    """Test ProfessionalRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def professional_repo(self, mock_session):
        """ProfessionalRepository instance with mocked session."""
        return ProfessionalRepository(mock_session)

    @pytest.fixture
    def sample_professional(self):
        """Sample professional data."""
        return Professional(
            id=1,
            user_id=1,
            salon_id=1,
            specialties=["Hair Cut", "Coloring"],
            bio="Experienced hair stylist",
            license_number="ABC123",
            commission_percentage=50.0,
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_create_professional_success(self, professional_repo, mock_session):
        """Test successful professional creation."""
        # Mock session methods
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Call the method
        result = await professional_repo.create(
            user_id=1,
            salon_id=1,
            specialties=["Hair Cut", "Coloring"],
            bio="Experienced stylist",
            license_number="ABC123",
        )

        # Verify calls
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Check that a Professional was added
        added_professional = mock_session.add.call_args[0][0]
        assert isinstance(added_professional, Professional)
        assert added_professional.user_id == 1
        assert added_professional.salon_id == 1

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, professional_repo, mock_session, sample_professional):
        """Test get_by_id returns professional when found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_professional
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await professional_repo.get_by_id(1)

        # Assert
        assert result == sample_professional
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, professional_repo, mock_session):
        """Test get_by_id returns None when not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await professional_repo.get_by_id(999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_id_found(self, professional_repo, mock_session, sample_professional):
        """Test get_by_user_id returns professional when found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_professional
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await professional_repo.get_by_user_id(1)

        # Assert
        assert result == sample_professional
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_id_not_found(self, professional_repo, mock_session):
        """Test get_by_user_id returns None when not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await professional_repo.get_by_user_id(999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_salon_id(self, professional_repo, mock_session):
        """Test listing professionals by salon ID."""
        # Mock professionals list
        professionals = [
            Professional(id=1, user_id=1, salon_id=1, specialties=["Hair"]),
            Professional(id=2, user_id=2, salon_id=1, specialties=["Nails"]),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = professionals
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await professional_repo.list_by_salon_id(salon_id=1)

        # Assert
        assert result == professionals
        mock_session.execute.assert_called_once()



    @pytest.mark.asyncio
    async def test_exists_by_user_id_true(self, professional_repo, mock_session):
        """Test exists_by_user_id returns True when professional exists."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await professional_repo.exists_by_user_id(1)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_by_user_id_false(self, professional_repo, mock_session):
        """Test exists_by_user_id returns False when professional doesn't exist."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await professional_repo.exists_by_user_id(999)

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()

