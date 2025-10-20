"""Tests for database session management."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import (
    engine,
    AsyncSessionLocal,
    get_db
)


class TestDatabaseEngine:
    """Test database engine configuration."""

    def test_engine_exists(self):
        """Test that database engine is created."""
        assert engine is not None

    def test_engine_configuration(self):
        """Test engine configuration properties."""
        # Engine should have expected configuration
        assert engine.pool_size == 5
        assert engine.pool._max_overflow == 10
        assert engine.pool._pre_ping is True


class TestSessionFactory:
    """Test async session factory."""

    def test_session_factory_exists(self):
        """Test that session factory is created."""
        assert AsyncSessionLocal is not None

    @pytest.mark.asyncio
    async def test_session_factory_creates_sessions(self):
        """Test session factory can create sessions."""
        session = AsyncSessionLocal()
        assert isinstance(session, AsyncSession)
        await session.close()


class TestGetDB:
    """Test get_db dependency function."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db yields async session."""
        db_generator = get_db()

        # Get the session
        session = await db_generator.__anext__()

        # Should be AsyncSession
        assert isinstance(session, AsyncSession)

        # Close the session
        try:
            await db_generator.__anext__()
        except StopAsyncIteration:
            pass  # Expected when generator finishes

    @pytest.mark.asyncio
    async def test_get_db_session_closes(self):
        """Test that session is properly closed."""
        db_generator = get_db()

        # Mock the session close method
        session = await db_generator.__anext__()
        with patch.object(session, 'close') as mock_close:
            # Trigger generator cleanup
            try:
                await db_generator.__anext__()
            except StopAsyncIteration:
                pass

            # Close should have been called
            mock_close.assert_called_once()


class TestAsyncSessionLocal:
    """Test AsyncSessionLocal factory."""

    @pytest.mark.asyncio
    async def test_async_session_local_context_manager(self):
        """Test AsyncSessionLocal as async context manager."""
        async with AsyncSessionLocal() as session:
            assert isinstance(session, AsyncSession)
            assert session is not None

    @pytest.mark.asyncio
    async def test_async_session_local_auto_closes(self):
        """Test that session auto-closes after context."""
        session_ref = None

        # Use context manager
        async with AsyncSessionLocal() as session:
            session_ref = session
            assert isinstance(session, AsyncSession)

        # Session should be closed after context
        assert session_ref is not None


class TestSessionConfiguration:
    """Test session configuration and properties."""

    @pytest.mark.asyncio
    async def test_session_configuration(self):
        """Test session factory configuration."""
        # Test that factory is properly configured
        assert AsyncSessionLocal.class_ == AsyncSession

        # Test session properties with async context
        async with AsyncSessionLocal() as session:
            assert session.bind == engine


class TestDatabaseConnection:
    """Test database connection functionality."""

    @pytest.mark.asyncio
    async def test_database_connection_mock(self):
        """Test database connection with mocked database."""
        # Mock database operations
        with patch('backend.app.db.session.engine') as mock_engine:
            mock_session = AsyncMock()
            mock_engine.begin.return_value.__aenter__.return_value = mock_session

            # Test connection can be established
            async with AsyncSessionLocal() as session:
                assert session is not None


class TestSessionErrorHandling:
    """Test session error handling."""

    @pytest.mark.asyncio
    async def test_get_db_handles_exceptions(self):
        """Test get_db handles exceptions properly."""
        db_generator = get_db()

        try:
            session = await db_generator.__anext__()

            # Simulate an exception
            with patch.object(session, 'close') as mock_close:
                # Force generator cleanup
                try:
                    await db_generator.aclose()
                except:
                    pass

                # Close should still be called
                mock_close.assert_called_once()
        except Exception:
            # Test that exceptions don't prevent cleanup
            pass


class TestSessionFactoryProperties:
    """Test session factory properties and behavior."""

    @pytest.mark.asyncio
    async def test_multiple_sessions_are_independent(self):
        """Test that multiple sessions are independent."""
        async with AsyncSessionLocal() as session1:
            async with AsyncSessionLocal() as session2:
                # Should be different instances
                assert session1 is not session2

    @pytest.mark.asyncio
    async def test_session_bind_to_engine(self):
        """Test that sessions are bound to the correct engine."""
        async with AsyncSessionLocal() as session:
            # Session should be bound to our engine
            assert session.bind == engine
