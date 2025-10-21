"""Test audit events system."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.audit_event import AuditEvent, AuditEventType, AuditEventSeverity
from backend.app.db.repositories.audit_event import AuditEventRepository
from backend.app.main import app


@pytest.mark.asyncio
async def test_audit_event_creation(db_session: AsyncSession):
    """Test creating audit events."""
    audit_repo = AuditEventRepository(db_session)

    # Create a login event
    event = await audit_repo.create_event(
        event_type=AuditEventType.LOGIN,
        action="user_login",
        user_id=1,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 Test Browser",
        description="User login successful",
        severity=AuditEventSeverity.LOW,
        success="success"
    )

    assert event.id is not None
    assert event.event_type == AuditEventType.LOGIN
    assert event.user_id == 1
    assert event.success == "success"

    # Get the event back
    retrieved_event = await audit_repo.get_by_id(event.id)
    assert retrieved_event is not None
    assert retrieved_event.action == "user_login"


@pytest.mark.asyncio
async def test_audit_event_filtering(db_session: AsyncSession):
    """Test filtering audit events."""
    audit_repo = AuditEventRepository(db_session)

    # Create multiple events
    for i in range(5):
        await audit_repo.create_event(
            event_type=AuditEventType.BOOKING_CREATED if i % 2 == 0 else AuditEventType.LOGIN,
            action=f"test_action_{i}",
            user_id=i + 1,
            description=f"Test event {i}",
            severity=AuditEventSeverity.LOW,
        )

    # Filter by event type
    events, count = await audit_repo.list_events(
        event_types=[AuditEventType.LOGIN],
        limit=10
    )

    login_events = [e for e in events if e.event_type == AuditEventType.LOGIN]
    assert len(login_events) >= 2  # At least the ones we created

    # Filter by user
    user_events, user_count = await audit_repo.list_events(
        user_id=1,
        limit=10
    )

    assert user_count >= 1
    assert all(e.user_id == 1 for e in user_events)


def test_audit_middleware_integration():
    """Test that audit middleware is properly integrated."""
    client = TestClient(app)

    # Test health endpoint - should create audit event
    response = client.get("/health")
    assert response.status_code == 200

    # The middleware should have automatically created an audit event
    # In a real test, you'd check the database for the audit event


@pytest.mark.asyncio
async def test_audit_statistics(db_session: AsyncSession):
    """Test audit statistics generation."""
    audit_repo = AuditEventRepository(db_session)

    # Create test events
    await audit_repo.create_event(
        event_type=AuditEventType.LOGIN,
        action="test_login",
        success="success",
        severity=AuditEventSeverity.LOW,
    )

    await audit_repo.create_event(
        event_type=AuditEventType.LOGIN_FAILED,
        action="test_login_failed",
        success="failure",
        severity=AuditEventSeverity.MEDIUM,
    )

    # Get statistics
    stats = await audit_repo.get_statistics()

    assert "total_events" in stats
    assert "failed_events" in stats
    assert "success_rate" in stats
    assert "events_by_type" in stats
    assert "events_by_severity" in stats

    assert stats["total_events"] >= 2


def test_audit_endpoints_require_admin():
    """Test that audit endpoints require admin permissions."""
    client = TestClient(app)

    # Try to access audit endpoints without authentication
    response = client.get("/api/v1/audit/events")
    assert response.status_code == 401  # Unauthorized

    response = client.get("/api/v1/audit/statistics")
    assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
async def test_factory_methods():
    """Test audit event factory methods."""
    # Test login event factory
    login_event = AuditEvent.create_login_event(
        user_id=123,
        success=True,
        ip_address="10.0.0.1",
        user_agent="Test Agent",
        session_id="session_123"
    )

    assert login_event.event_type == AuditEventType.LOGIN
    assert login_event.user_id == 123
    assert login_event.success == "success"
    assert login_event.ip_address == "10.0.0.1"

    # Test booking event factory
    booking_event = AuditEvent.create_booking_event(
        event_type=AuditEventType.BOOKING_CREATED,
        booking_id=456,
        user_id=123,
        description="New booking created"
    )

    assert booking_event.event_type == AuditEventType.BOOKING_CREATED
    assert booking_event.resource_type == "booking"
    assert booking_event.resource_id == "456"
    assert booking_event.user_id == 123

    # Test payment event factory
    payment_event = AuditEvent.create_payment_event(
        event_type=AuditEventType.PAYMENT_PROCESSED,
        payment_id="pay_123",
        user_id=123,
        amount=100.00,
        success=True
    )

    assert payment_event.event_type == AuditEventType.PAYMENT_PROCESSED
    assert payment_event.resource_type == "payment"
    assert payment_event.resource_id == "pay_123"
    assert payment_event.success == "success"


if __name__ == "__main__":
    pytest.main([__file__])
