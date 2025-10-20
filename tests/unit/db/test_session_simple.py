"""Simple tests for database session management."""

import pytest
from unittest.mock import AsyncMock

from backend.app.db.session import engine, AsyncSessionLocal, get_db


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

    def test_session_factory_class(self):
        """Test session factory class configuration."""
        from sqlalchemy.ext.asyncio import AsyncSession
        assert AsyncSessionLocal.class_ == AsyncSession


class TestGetDB:
    """Test get_db dependency function."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db yields async session."""
        from sqlalchemy.ext.asyncio import AsyncSession

        db_generator = get_db()

        # Get the session
        session = await db_generator.__anext__()

        # Should be AsyncSession
        assert isinstance(session, AsyncSession)

        # Close the session and generator
        try:
            await db_generator.aclose()
        except:
            pass


class TestBasicSessionOperations:
    """Test basic session operations."""

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test session as context manager."""
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSessionLocal() as session:
            assert isinstance(session, AsyncSession)
            assert session is not None

    @pytest.mark.asyncio
    async def test_session_bind(self):
        """Test session is bound to engine."""
        async with AsyncSessionLocal() as session:
            assert session.bind == engine


class TestSessionFactoryProperties:
    """Test session factory properties."""

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self):
        """Test multiple sessions are independent."""
        session1 = AsyncSessionLocal()
        session2 = AsyncSessionLocal()

        # Should be different instances
        assert session1 is not session2

        # Clean up
        await session1.close()
        await session2.close()


class TestDatabaseURL:
    """Test database URL configuration."""

    def test_database_url_used(self):
        """Test that database URL from settings is used."""
        from backend.app.core.config import settings

        # Engine should use the database URL from settings
        assert str(settings.DATABASE_URL) in str(engine.url)
