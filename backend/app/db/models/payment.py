"""
Payment and Refund models.

This module defines the database models for payments and refunds,
including all status tracking and provider integration data.
"""

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Boolean,
    Text, JSON, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from datetime import datetime
from enum import Enum as PyEnum

from .base import Base, TimestampMixin, IDMixin


class PaymentStatus(PyEnum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(PyEnum):
    """Payment method enumeration"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BANK_SLIP = "bank_slip"


class RefundStatus(PyEnum):
    """Refund status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Payment(Base, IDMixin, TimestampMixin):
    """
    Payment model for tracking all payment transactions.

    This model stores payment information including provider details,
    status tracking, and links to bookings.
    """
    __tablename__ = "payments"

    # Payment identification
    provider_name = Column(String(50), nullable=False, index=True)
    provider_payment_id = Column(String(255), nullable=False, index=True)

    # Amount and currency
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")

    # Payment details
    payment_method = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True, default=PaymentStatus.PENDING.value)

    # Customer information
    customer_email = Column(String(255), nullable=True)
    customer_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Provider-specific data
    provider_data = Column(JSON, nullable=True)
    payment_url = Column(Text, nullable=True)  # For PIX QR codes, checkout URLs

    # Business relationships
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Status tracking
    paid_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    # Idempotency and extra data (avoid 'metadata' which is reserved)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    extra_data = Column(JSON, nullable=True)

    # Provider webhook tracking
    last_webhook_at = Column(DateTime(timezone=True), nullable=True)
    webhook_events_count = Column(Integer, nullable=False, default=0)

    # Relationships
    user = relationship("User", back_populates="payments")
    booking = relationship("Booking", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")
    logs = relationship("PaymentLog", back_populates="payment", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='payment_amount_positive'),
        CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed', 'canceled', 'refunded', 'partially_refunded')",
            name='payment_status_valid'
        ),
        CheckConstraint(
            "payment_method IN ('credit_card', 'debit_card', 'pix', 'bank_slip')",
            name='payment_method_valid'
        ),
        CheckConstraint(
            "currency IN ('BRL', 'USD', 'EUR')",
            name='payment_currency_valid'
        ),
        Index('idx_payment_provider_id', 'provider_name', 'provider_payment_id'),
        Index('idx_payment_status_created', 'status', 'created_at'),
        Index('idx_payment_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status={self.status}, provider={self.provider_name})>"

    @property
    def is_pending(self) -> bool:
        """Check if payment is in pending status."""
        return self.status == PaymentStatus.PENDING.value

    @property
    def is_succeeded(self) -> bool:
        """Check if payment succeeded."""
        return self.status == PaymentStatus.SUCCEEDED.value

    @property
    def is_failed(self) -> bool:
        """Check if payment failed."""
        return self.status == PaymentStatus.FAILED.value

    @property
    def is_refundable(self) -> bool:
        """Check if payment can be refunded."""
        return self.status in [PaymentStatus.SUCCEEDED.value, PaymentStatus.PARTIALLY_REFUNDED.value]

    @property
    def total_refunded_amount(self) -> Decimal:
        """Calculate total amount refunded."""
        total = Decimal('0')
        for refund in self.refunds:
            if refund.status == RefundStatus.SUCCEEDED.value:
                total += refund.amount
        return total

    @property
    def remaining_refundable_amount(self) -> Decimal:
        """Calculate remaining amount that can be refunded."""
        return self.amount - self.total_refunded_amount

    def can_refund(self, amount: Decimal = None) -> bool:
        """
        Check if payment can be refunded for the specified amount.

        Args:
            amount: Amount to refund. If None, checks if any refund is possible.

        Returns:
            True if refund is possible, False otherwise.
        """
        if not self.is_refundable:
            return False

        if amount is None:
            return self.remaining_refundable_amount > 0

        return amount <= self.remaining_refundable_amount

    def update_status_timestamps(self):
        """Update status-specific timestamps based on current status."""
        now = func.now()

        if self.status == PaymentStatus.SUCCEEDED.value and not self.paid_at:
            self.paid_at = now
        elif self.status == PaymentStatus.FAILED.value and not self.failed_at:
            self.failed_at = now
        elif self.status == PaymentStatus.CANCELED.value and not self.canceled_at:
            self.canceled_at = now


class Refund(Base, IDMixin, TimestampMixin):
    """
    Refund model for tracking refund transactions.

    This model stores refund information including provider details,
    status tracking, and links to original payments.
    """
    __tablename__ = "refunds"

    # Refund identification
    provider_name = Column(String(50), nullable=False, index=True)
    provider_refund_id = Column(String(255), nullable=False, index=True)

    # Amount and currency
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")

    # Refund details
    status = Column(String(20), nullable=False, index=True, default=RefundStatus.PENDING.value)
    reason = Column(String(255), nullable=True)

    # Provider-specific data
    provider_data = Column(JSON, nullable=True)

    # Business relationships
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Status tracking
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    # Idempotency and extra data (avoid 'metadata' which is reserved)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    extra_data = Column(JSON, nullable=True)

    # Provider webhook tracking
    last_webhook_at = Column(DateTime(timezone=True), nullable=True)
    webhook_events_count = Column(Integer, nullable=False, default=0)

    # Relationships
    payment = relationship("Payment", back_populates="refunds")
    logs = relationship("PaymentLog", back_populates="refund", cascade="all, delete-orphan")
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id])

    # Constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='refund_amount_positive'),
        CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed', 'canceled')",
            name='refund_status_valid'
        ),
        CheckConstraint(
            "currency IN ('BRL', 'USD', 'EUR')",
            name='refund_currency_valid'
        ),
        Index('idx_refund_provider_id', 'provider_name', 'provider_refund_id'),
        Index('idx_refund_status_created', 'status', 'created_at'),
        Index('idx_refund_payment_status', 'payment_id', 'status'),
    )

    def __repr__(self):
        return f"<Refund(id={self.id}, amount={self.amount}, status={self.status}, payment_id={self.payment_id})>"

    @property
    def is_pending(self) -> bool:
        """Check if refund is in pending status."""
        return self.status == RefundStatus.PENDING.value

    @property
    def is_succeeded(self) -> bool:
        """Check if refund succeeded."""
        return self.status == RefundStatus.SUCCEEDED.value

    @property
    def is_failed(self) -> bool:
        """Check if refund failed."""
        return self.status == RefundStatus.FAILED.value

    def update_status_timestamps(self):
        """Update status-specific timestamps based on current status."""
        now = func.now()

        if self.status == RefundStatus.SUCCEEDED.value and not self.processed_at:
            self.processed_at = now
        elif self.status == RefundStatus.FAILED.value and not self.failed_at:
            self.failed_at = now
        elif self.status == RefundStatus.CANCELED.value and not self.canceled_at:
            self.canceled_at = now


class PaymentWebhookEvent(Base, IDMixin, TimestampMixin):
    """
    Payment webhook event model for tracking webhook processing.

    This model stores webhook events for idempotent processing and
    debugging/auditing webhook deliveries.
    """
    __tablename__ = "payment_webhook_events"

    # Event identification
    provider_name = Column(String(50), nullable=False, index=True)
    provider_event_id = Column(String(255), nullable=False, index=True)

    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)

    # Processing status
    processed = Column(Boolean, nullable=False, default=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)
    processing_attempts = Column(Integer, nullable=False, default=0)

    # Related payment/refund (may be null if event is for unknown payment)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True, index=True)
    refund_id = Column(Integer, ForeignKey("refunds.id"), nullable=True, index=True)

    # Raw webhook data for debugging
    raw_payload = Column(Text, nullable=True)
    headers = Column(JSON, nullable=True)

    # Relationships
    payment = relationship("Payment")
    refund = relationship("Refund")

    # Constraints
    __table_args__ = (
        Index('idx_webhook_provider_event', 'provider_name', 'provider_event_id', unique=True),
        Index('idx_webhook_processed_created', 'processed', 'created_at'),
        Index('idx_webhook_event_type', 'event_type', 'created_at'),
    )

    def __repr__(self):
        return f"<PaymentWebhookEvent(id={self.id}, provider={self.provider_name}, event_type={self.event_type}, processed={self.processed})>"

    def mark_processed(self):
        """Mark webhook event as successfully processed."""
        self.processed = True
        self.processed_at = func.now()

    def mark_failed(self, error_message: str):
        """Mark webhook event as failed with error message."""
        self.processing_attempts += 1
        self.processing_error = error_message
