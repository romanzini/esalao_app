"""Unit tests for UserRepository."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.db.repositories.user import UserRepository
from backend.app.db.models.user import User, UserRole


class TestUserRepository:
    """Test UserRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def user_repo(self, mock_session):
        """UserRepository instance with mocked session."""
        return UserRepository(mock_session)

    @pytest.fixture
    def sample_user(self):
        """Sample user data."""
        return User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            phone="+5511999999999",
            role=UserRole.CLIENT,
            is_active=True,
            is_verified=False,
        )

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_repo, mock_session, sample_user):
        """Test successful user creation."""
        # Mock session.add and commit
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Call the method
        result = await user_repo.create(
            email=sample_user.email,
            password_hash=sample_user.password_hash,
            full_name=sample_user.full_name,
            phone=sample_user.phone,
            role=sample_user.role,
        )

        # Verify calls
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Check that a User was added
        added_user = mock_session.add.call_args[0][0]
        assert isinstance(added_user, User)
        assert added_user.email == sample_user.email
        assert added_user.full_name == sample_user.full_name

    @pytest.mark.asyncio
    async def test_exists_by_email_true(self, user_repo, mock_session):
        """Test exists_by_email returns True when user exists."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await user_repo.exists_by_email("test@example.com")

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_by_email_false(self, user_repo, mock_session):
        """Test exists_by_email returns False when user doesn't exist."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await user_repo.exists_by_email("nonexistent@example.com")

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, user_repo, mock_session, sample_user):
        """Test get_by_email returns user when found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await user_repo.get_by_email("test@example.com")

        # Assert
        assert result == sample_user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, user_repo, mock_session):
        """Test get_by_email returns None when not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await user_repo.get_by_email("nonexistent@example.com")

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, user_repo, mock_session, sample_user):
        """Test get_by_id returns user when found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await user_repo.get_by_id(1)

        # Assert
        assert result == sample_user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repo, mock_session):
        """Test get_by_id returns None when not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await user_repo.get_by_id(999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_login(self, user_repo, mock_session, sample_user):
        """Test updating user's last login timestamp."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Call method
        await user_repo.update_last_login(1)

        # Assert
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        assert sample_user.last_login is not None

    @pytest.mark.asyncio
    async def test_update_last_login_user_not_found(self, user_repo, mock_session):
        """Test update_last_login when user not found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method (should not raise exception)
        await user_repo.update_last_login(999)

        # Assert
        mock_session.execute.assert_called_once()
        # Commit should not be called if user not found
        mock_session.commit.assert_not_called()
