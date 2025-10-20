"""
Pytest configuration and fixtures for unit tests.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator

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
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    """Create database session for testing."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def override_get_db(db_session):
    """Override get_db dependency for testing."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    return _override_get_db


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_db_session() -> Mock:
    """Create a mock database session."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.refresh = Mock()
    session.execute = Mock()
    session.query = Mock()

    return session


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """Create a mock async database session."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()

    return session


# Payment fixtures
@pytest.fixture
def sample_payment_request() -> PaymentRequest:
    """Create a sample payment request."""
    return PaymentRequest(
        amount=Decimal("100.00"),
        currency="BRL",
        method=PaymentMethod.CREDIT_CARD,
        description="Test payment",
        customer_id="customer_123",
        metadata={"booking_id": "456", "user_id": "789"}
    )


@pytest.fixture
def sample_payment_response() -> PaymentResponse:
    """Create a sample payment response."""
    return PaymentResponse(
        payment_id="pay_123",
        status=PaymentStatus.PENDING,
        amount=Decimal("100.00"),
        currency="BRL",
        provider_data={
            "created_at": "2023-01-01T12:00:00Z",
            "payment_intent_id": "pi_123"
        }
    )


@pytest.fixture
def sample_refund_request() -> RefundRequest:
    """Create a sample refund request."""
    return RefundRequest(
        payment_id="pay_123",
        amount=Decimal("50.00"),
        reason="Customer request",
        metadata={"admin_id": "admin_123"}
    )


@pytest.fixture
def sample_refund_response() -> RefundResponse:
    """Create a sample refund response."""
    return RefundResponse(
        refund_id="ref_123",
        payment_id="pay_123",
        amount=Decimal("50.00"),
        currency="BRL",
        status="processing",
        provider_data={
            "created_at": "2023-01-01T12:30:00Z",
            "expected_date": "2023-01-08"
        }
    )


@pytest.fixture
def sample_payment_model() -> Payment:
    """Create a sample payment model."""
    return Payment(
        id=1,
        provider_payment_id="pay_123",
        provider_name="mock",
        amount=Decimal("100.00"),
        currency="BRL",
        method=PaymentMethod.CREDIT_CARD,
        status=PaymentStatus.PENDING,
        description="Test payment",
        customer_id="customer_123",
        booking_id=1,
        metadata={"user_id": "456"},
        provider_data={"created_at": "2023-01-01T12:00:00Z"},
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_refund_model() -> Refund:
    """Create a sample refund model."""
    return Refund(
        id=1,
        provider_refund_id="ref_123",
        payment_id=1,
        amount=Decimal("50.00"),
        currency="BRL",
        status=RefundStatus.PROCESSING,
        reason="Customer request",
        metadata={"admin_id": "admin_123"},
        provider_data={"created_at": "2023-01-01T12:30:00Z"},
        created_at=datetime(2023, 1, 1, 12, 30, 0),
        updated_at=datetime(2023, 1, 1, 12, 30, 0),
    )


@pytest.fixture
def sample_webhook_event() -> WebhookEvent:
    """Create a sample webhook event."""
    return WebhookEvent(
        event_type="payment.completed",
        payment_id="pay_123",
        data={
            "status": "completed",
            "amount": 100.00,
            "currency": "BRL"
        },
        timestamp=datetime(2023, 1, 1, 12, 0, 0)
    )


@pytest.fixture
def sample_webhook_event_model() -> PaymentWebhookEvent:
    """Create a sample webhook event model."""
    return PaymentWebhookEvent(
        id=1,
        provider_name="stripe",
        event_id="evt_123",
        event_type="payment.completed",
        payment_id=1,
        data={
            "status": "completed",
            "amount": 100.00,
            "currency": "BRL"
        },
        processed=False,
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        processed_at=None,
    )


@pytest.fixture
def sample_payment_log() -> PaymentLog:
    """Create a sample payment log."""
    return PaymentLog(
        id=1,
        payment_id=1,
        action="payment_created",
        status=PaymentStatus.PENDING,
        amount=Decimal("100.00"),
        details={
            "payment_created": True,
            "provider": "mock",
            "method": "credit_card"
        },
        metadata={"user_id": "456"},
        created_at=datetime(2023, 1, 1, 12, 0, 0),
    )


# Notification fixtures
@pytest.fixture
def sample_notification_context() -> NotificationContext:
    """Create a sample notification context."""
    return NotificationContext(
        user_id="user_123",
        user_name="João Silva",
        user_email="joao@example.com",
        user_phone="+5511999999999",
        custom_data={
            "payment_amount": Decimal("100.00"),
            "booking_service": "Corte de Cabelo",
            "booking_date": "2023-12-25",
            "booking_time": "14:00"
        }
    )


# Mock provider fixtures
@pytest.fixture
def mock_payment_provider() -> Mock:
    """Create a mock payment provider."""
    provider = Mock()
    provider.get_provider_name.return_value = "mock"

    # Mock successful payment creation
    provider.create_payment.return_value = PaymentResponse(
        payment_id="pay_123",
        status=PaymentStatus.PENDING,
        amount=Decimal("100.00"),
        currency="BRL"
    )

    # Mock successful payment status check
    provider.get_payment_status.return_value = PaymentResponse(
        payment_id="pay_123",
        status=PaymentStatus.COMPLETED,
        amount=Decimal("100.00"),
        currency="BRL"
    )

    # Mock successful payment cancellation
    provider.cancel_payment.return_value = PaymentResponse(
        payment_id="pay_123",
        status=PaymentStatus.CANCELLED,
        amount=Decimal("100.00"),
        currency="BRL"
    )

    # Mock successful refund creation
    provider.create_refund.return_value = RefundResponse(
        refund_id="ref_123",
        payment_id="pay_123",
        amount=Decimal("50.00"),
        currency="BRL",
        status="processing"
    )

    # Mock webhook validation
    provider.validate_webhook_signature.return_value = True

    # Mock webhook event processing
    provider.process_webhook_event.return_value = WebhookEvent(
        event_type="payment.completed",
        payment_id="pay_123",
        data={"status": "completed"},
        timestamp=datetime.now()
    )

    return provider


@pytest.fixture
def mock_provider_factory(mock_payment_provider) -> Mock:
    """Create a mock payment provider factory."""
    factory = Mock()
    factory.get_provider.return_value = mock_payment_provider
    return factory


@pytest.fixture
def mock_logging_service() -> Mock:
    """Create a mock payment logging service."""
    service = Mock()
    service.log_payment_created = Mock()
    service.log_payment_status_changed = Mock()
    service.log_refund_created = Mock()
    service.log_webhook_received = Mock()
    service.log_payment_action = Mock()
    return service


@pytest.fixture
def mock_notification_service() -> AsyncMock:
    """Create a mock notification service."""
    service = AsyncMock()
    service.send_notification = AsyncMock()
    service.get_available_channels.return_value = ["email", "sms", "push", "in_app"]
    service.get_available_templates.return_value = [
        "payment_confirmation",
        "payment_failed",
        "refund_confirmation",
        "booking_reminder",
        "booking_cancelled",
        "welcome"
    ]
    return service


# Test data fixtures
@pytest.fixture
def payment_create_data() -> dict:
    """Create payment creation test data."""
    return {
        "amount": "100.00",
        "currency": "BRL",
        "method": "credit_card",
        "description": "Test payment",
        "customer_id": "customer_123",
        "booking_id": 1,
        "metadata": {"user_id": "456"}
    }


@pytest.fixture
def refund_create_data() -> dict:
    """Create refund creation test data."""
    return {
        "amount": "50.00",
        "reason": "Customer request",
        "metadata": {"admin_id": "admin_123"}
    }


@pytest.fixture
def webhook_payload() -> dict:
    """Create webhook payload test data."""
    return {
        "event": "payment.completed",
        "payment_id": "pay_123",
        "timestamp": "2023-01-01T12:00:00Z",
        "data": {
            "status": "completed",
            "amount": 100.00,
            "currency": "BRL"
        }
    }


# Utility fixtures
@pytest.fixture
def clean_db(db_session):
    """Clean the database before each test."""
    # Delete all records from test tables
    db_session.query(PaymentLog).delete()
    db_session.query(PaymentWebhookEvent).delete()
    db_session.query(Refund).delete()
    db_session.query(Payment).delete()
    db_session.commit()

    yield db_session

    # Clean up after test
    db_session.rollback()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    # Mock environment variables for testing
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", SQLALCHEMY_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")  # Test Redis DB
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")


# Async test utilities
@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to all tests in tests/unit/
        if "tests/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker to all tests in tests/integration/
        if "tests/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add slow marker to tests with 'slow' in the name
        if "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)

        # Add external marker to tests that use external services
        if any(marker in item.name.lower() for marker in ["stripe", "webhook", "external"]):
            item.add_marker(pytest.mark.external)
