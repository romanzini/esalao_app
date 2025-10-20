"""
Payment log models for audit and debugging purposes.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean,
    ForeignKey, Index, Integer
)
from sqlalchemy.orm import relationship
from backend.app.db.models.base import IDMixin, Base


class PaymentLog(IDMixin, Base):
    """
    Comprehensive payment log for audit trails and debugging.

    Tracks all payment-related events including API calls,
    provider responses, state changes, and error conditions.
    """
    __tablename__ = "payment_logs"

    # Core identification
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=True)
    refund_id = Column(Integer, ForeignKey("refunds.id", ondelete="CASCADE"), nullable=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Log classification
    log_type = Column(String(50), nullable=False)  # payment_created, provider_call, webhook_received, etc.
    level = Column(String(20), nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Event details
    message = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)  # mock, stripe, paypal
    provider_transaction_id = Column(String(255), nullable=True)

    # Request/Response data (sanitized)
    request_data = Column(Text, nullable=True)  # JSON string of request data (sensitive data removed)
    response_data = Column(Text, nullable=True)  # JSON string of response data

    # Error handling
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    # Context and tracing
    correlation_id = Column(String(100), nullable=True)  # For request tracing
    session_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)

    # Processing details
    processing_time_ms = Column(Integer, nullable=True)  # Request processing time
    retry_count = Column(Integer, default=0)
    is_sensitive = Column(Boolean, default=False)  # Flag for sensitive data logs

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    payment = relationship("Payment", back_populates="logs")
    refund = relationship("Refund", back_populates="logs")
    booking = relationship("Booking")
    user = relationship("User")

    # Indexes for performance
    __table_args__ = (
        Index("idx_payment_logs_payment_id", "payment_id"),
        Index("idx_payment_logs_refund_id", "refund_id"),
        Index("idx_payment_logs_booking_id", "booking_id"),
        Index("idx_payment_logs_user_id", "user_id"),
        Index("idx_payment_logs_timestamp", "timestamp"),
        Index("idx_payment_logs_log_type", "log_type"),
        Index("idx_payment_logs_level", "level"),
        Index("idx_payment_logs_provider", "provider"),
        Index("idx_payment_logs_correlation_id", "correlation_id"),
        Index("idx_payment_logs_provider_transaction_id", "provider_transaction_id"),
    )

    def __repr__(self):
        return f"<PaymentLog(id={self.id}, type={self.log_type}, level={self.level}, timestamp={self.timestamp})>"


class PaymentLogLevel:
    """Constants for log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PaymentLogType:
    """Constants for payment log types."""

    # Payment lifecycle
    PAYMENT_CREATED = "payment_created"
    PAYMENT_UPDATED = "payment_updated"
    PAYMENT_CANCELLED = "payment_cancelled"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"

    # Provider interactions
    PROVIDER_CALL = "provider_call"
    PROVIDER_RESPONSE = "provider_response"
    PROVIDER_ERROR = "provider_error"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RETRY = "provider_retry"

    # Webhook processing
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_PROCESSED = "webhook_processed"
    WEBHOOK_FAILED = "webhook_failed"
    WEBHOOK_DUPLICATE = "webhook_duplicate"
    WEBHOOK_INVALID = "webhook_invalid"

    # Refund operations
    REFUND_CREATED = "refund_created"
    REFUND_PROCESSED = "refund_processed"
    REFUND_FAILED = "refund_failed"
    REFUND_CANCELLED = "refund_cancelled"

    # Security and validation
    SECURITY_VIOLATION = "security_violation"
    VALIDATION_FAILED = "validation_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # System events
    RECONCILIATION_RUN = "reconciliation_run"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"
    SYSTEM_ERROR = "system_error"
    CONFIG_CHANGED = "config_changed"
