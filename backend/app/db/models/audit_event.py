"""
Audit event model for tracking system actions and changes.

This module provides comprehensive auditing capabilities for the salon platform,
tracking user actions, system events, and data changes.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase

from backend.app.db.models.base import Base


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"

    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"

    # Booking events
    BOOKING_CREATED = "booking_created"
    BOOKING_UPDATED = "booking_updated"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_COMPLETED = "booking_completed"
    BOOKING_NO_SHOW = "booking_no_show"
    BOOKING_RESCHEDULED = "booking_rescheduled"

    # Payment events
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_DISPUTED = "payment_disputed"

    # Policy events
    CANCELLATION_POLICY_CREATED = "cancellation_policy_created"
    CANCELLATION_POLICY_UPDATED = "cancellation_policy_updated"
    CANCELLATION_POLICY_ACTIVATED = "cancellation_policy_activated"
    CANCELLATION_POLICY_DEACTIVATED = "cancellation_policy_deactivated"

    # System events
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_ERROR = "system_error"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"

    # Notification events
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"
    NOTIFICATION_OPENED = "notification_opened"

    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH_DETECTED = "data_breach_detected"

    # Business events
    SALON_CREATED = "salon_created"
    SALON_UPDATED = "salon_updated"
    SERVICE_CREATED = "service_created"
    SERVICE_UPDATED = "service_updated"
    PROFESSIONAL_ADDED = "professional_added"
    PROFESSIONAL_REMOVED = "professional_removed"


class AuditEventSeverity(str, Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent(Base):
    """
    Audit event model for tracking system actions and changes.

    This model captures detailed information about user actions,
    system events, and data changes for compliance and security purposes.
    """

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)

    # Event identification
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default=AuditEventSeverity.LOW)

    # User and session information
    user_id = Column(Integer, nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    user_role = Column(String(50), nullable=True)

    # Request information
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    endpoint = Column(String(255), nullable=True)
    http_method = Column(String(10), nullable=True)

    # Event details
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Data changes
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Additional context
    event_metadata = Column(JSON, nullable=True)

    # Timing
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Correlation and tracing
    correlation_id = Column(String(255), nullable=True, index=True)
    parent_event_id = Column(Integer, nullable=True, index=True)

    # Status and outcome
    success = Column(String(10), nullable=True)  # success, failure, partial
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation of audit event."""
        return (
            f"<AuditEvent(id={self.id}, "
            f"type={self.event_type}, "
            f"user_id={self.user_id}, "
            f"action={self.action}, "
            f"timestamp={self.timestamp})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "user_role": self.user_role,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "http_method": self.http_method,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "description": self.description,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "metadata": self.event_metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "correlation_id": self.correlation_id,
            "parent_event_id": self.parent_event_id,
            "success": self.success,
            "error_message": self.error_message,
        }

    @classmethod
    def create_login_event(
        cls,
        user_id: int,
        success: bool,
        ip_address: str,
        user_agent: str,
        session_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> "AuditEvent":
        """Create a login audit event."""
        return cls(
            event_type=AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            severity=AuditEventSeverity.LOW if success else AuditEventSeverity.MEDIUM,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action="user_login",
            description=f"User login {'successful' if success else 'failed'}",
            success="success" if success else "failure",
            error_message=error_message,
        )

    @classmethod
    def create_booking_event(
        cls,
        event_type: AuditEventType,
        booking_id: int,
        user_id: int,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "AuditEvent":
        """Create a booking-related audit event."""
        return cls(
            event_type=event_type,
            severity=AuditEventSeverity.LOW,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            resource_type="booking",
            resource_id=str(booking_id),
            action=event_type.value,
            description=description or f"Booking {event_type.value}",
            old_values=old_values,
            new_values=new_values,
            success="success",
        )

    @classmethod
    def create_payment_event(
        cls,
        event_type: AuditEventType,
        payment_id: str,
        user_id: Optional[int],
        amount: float,
        success: bool,
        description: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> "AuditEvent":
        """Create a payment-related audit event."""
        return cls(
            event_type=event_type,
            severity=AuditEventSeverity.MEDIUM if not success else AuditEventSeverity.LOW,
            user_id=user_id,
            resource_type="payment",
            resource_id=payment_id,
            action=event_type.value,
            description=description or f"Payment {event_type.value}",
            new_values={"amount": amount},
            event_metadata=metadata,
            success="success" if success else "failure",
            error_message=error_message,
        )

    @classmethod
    def create_security_event(
        cls,
        event_type: AuditEventType,
        ip_address: str,
        description: str,
        user_id: Optional[int] = None,
        severity: AuditEventSeverity = AuditEventSeverity.HIGH,
        metadata: Optional[Dict] = None,
    ) -> "AuditEvent":
        """Create a security-related audit event."""
        return cls(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            action=event_type.value,
            description=description,
            event_metadata=metadata,
            success="failure",  # Security events are usually failures/alerts
        )

    @classmethod
    def create_system_event(
        cls,
        event_type: AuditEventType,
        description: str,
        severity: AuditEventSeverity = AuditEventSeverity.LOW,
        metadata: Optional[Dict] = None,
        success: bool = True,
    ) -> "AuditEvent":
        """Create a system-related audit event."""
        return cls(
            event_type=event_type,
            severity=severity,
            action=event_type.value,
            description=description,
            event_metadata=metadata,
            success="success" if success else "failure",
        )
