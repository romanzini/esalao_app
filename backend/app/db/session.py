"""Database session management and dependency injection."""

from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import sessionmaker, Session

from backend.app.core.config import settings

# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create sync engine for Celery tasks
sync_engine = create_engine(
    str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://"),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync session factory for Celery tasks
SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Yields:
        AsyncSession instance

    Example:
        ```python
        @router.get("/users/{user_id}")
        async def get_user(
            user_id: int,
            db: AsyncSession = Depends(get_db)
        ):
            ...
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """
    Context manager for getting sync database session (for Celery tasks).

    Yields:
        Session instance

    Example:
        ```python
        def some_celery_task():
            with get_sync_db() as db:
                # Use sync session here
                pass
        ```
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_sync_db_session():
    """
    Get a sync database session for dependency injection.

    Yields:
        Session instance for FastAPI dependency injection
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
