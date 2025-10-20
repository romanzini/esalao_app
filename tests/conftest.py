"""
Pytest configuration and fixtures for unit tests.
"""

import pytest
import pytest_asyncio
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.models.base import Base
from backend.app.db.session import get_db, get_sync_db
from backend.app.db.models.payment import Payment, Refund, PaymentWebhookEvent
from backend.app.db.models.payment_log import PaymentLog
from backend.app.domain.payments.provider import (
    PaymentMethod,
    PaymentStatus,
    PaymentRequest,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    WebhookEvent,
)
from backend.app.domain.payments import RefundStatus
from backend.app.domain.notifications.service import NotificationContext


# Test database URL (in-memory SQLite for tests)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure async test backend."""
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    # Use test database URL
    test_db_url = str(settings.DATABASE_URL).replace("/esalao_db", "/esalao_test")

    # Create test engine
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Create test client with database session override."""

    async def override_get_db():
        yield db_session

    from backend.app.db.session import get_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def professional_user(db_session: AsyncSession):
    """Create and return a professional test user."""
    from backend.app.db.models.professional import Professional
    from backend.app.db.models.salon import Salon
    from backend.app.db.models.user import User, UserRole

    # Create owner for salon
    owner = User(
        email="owner_prof@test.com",
        password_hash="hashed",
        full_name="Salon Owner",
        role=UserRole.SALON_OWNER,
    )
    db_session.add(owner)
    await db_session.flush()

    # Create salon
    salon = Salon(
        owner_id=owner.id,
        name="Test Salon",
        cnpj="12.345.678/0001-90",
        phone="555-0100",
        address_street="Test Street",
        address_number="123",
        address_neighborhood="Test Neighborhood",
        address_city="Test City",
        address_state="SP",
        address_zipcode="12345-678",
    )
    db_session.add(salon)
    await db_session.flush()

    # Create professional user
    prof_user = User(
        email="professional_test@test.com",
        password_hash="hashed",
        full_name="Test Professional",
        role=UserRole.PROFESSIONAL,
    )
    db_session.add(prof_user)
    await db_session.flush()

    # Create professional profile
    professional = Professional(
        user_id=prof_user.id,
        salon_id=salon.id,
        specialties=["Haircut", "Coloring"],
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(prof_user)

    return prof_user


@pytest_asyncio.fixture(scope="function")
async def professional_client(db_session: AsyncSession, professional_user):
    """Create test client with professional authentication."""
    from backend.app.core.security.rbac import get_current_user
    from backend.app.db.session import get_db

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return professional_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession):
    """Create and return an admin test user."""
    from backend.app.db.models.user import User, UserRole

    admin = User(
        email="admin_test@test.com",
        password_hash="hashed",
        full_name="Test Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture(scope="function")
async def admin_client(db_session: AsyncSession, admin_user):
    """Create test client with admin authentication."""
    from backend.app.core.security.rbac import get_current_user
    from backend.app.db.session import get_db

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def auth_user(db_session: AsyncSession):
    """Create and return an authenticated test user."""
    from backend.app.db.models.user import User, UserRole

    test_user = User(
        email="authenticated_test@test.com",
        password_hash="hashed",
        full_name="Test User",
        role=UserRole.CLIENT,
    )
    db_session.add(test_user)
    await db_session.flush()
    await db_session.refresh(test_user)
    return test_user


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(db_session: AsyncSession, auth_user):
    """Create test client with authentication override."""
    from backend.app.core.security.rbac import get_current_user
    from backend.app.db.session import get_db

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return auth_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
