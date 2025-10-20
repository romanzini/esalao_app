"""
Enhanced notification models for the eSalão application.

This module contains models for managing notification preferences,
templates, channels, and delivery tracking.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List

from sqlalchemy import (
    Boolean, DateTime, Integer, String, Text, JSON, ForeignKey,
    Enum as SQLEnum, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base


class NotificationChannel(str, Enum):
    """Available notification channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WHATSAPP = "whatsapp"


class NotificationEventType(str, Enum):
    """Types of events that trigger notifications."""

    # Booking Events
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_REMINDER = "booking_reminder"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_RESCHEDULED = "booking_rescheduled"
    BOOKING_COMPLETED = "booking_completed"

    # Payment Events
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    REFUND_PROCESSED = "refund_processed"

    # Loyalty Events
    POINTS_EARNED = "points_earned"
    TIER_UPGRADED = "tier_upgraded"
    REWARD_AVAILABLE = "reward_available"
    POINTS_EXPIRING = "points_expiring"

    # Waitlist Events
    WAITLIST_ADDED = "waitlist_added"
    SLOT_AVAILABLE = "slot_available"
    WAITLIST_EXPIRED = "waitlist_expired"

    # No-show Events
    NO_SHOW_DETECTED = "no_show_detected"
    NO_SHOW_FEE_CHARGED = "no_show_fee_charged"

    # Professional Events
    NEW_BOOKING = "new_booking"
    CANCELLATION_NOTICE = "cancellation_notice"
    CLIENT_NO_SHOW = "client_no_show"

    # Marketing Events
    PROMOTIONAL_OFFER = "promotional_offer"
    BIRTHDAY_GREETING = "birthday_greeting"
    ANNIVERSARY_OFFER = "anniversary_offer"

    # System Events
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    ACCOUNT_LOCKED = "account_locked"


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class NotificationPreferences(Base):
    """User notification preferences by channel and event type."""

    __tablename__ = "notification_preferences"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for notification preference",
    )

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns these preferences",
    )

    # Preference Configuration
    event_type: Mapped[NotificationEventType] = mapped_column(
        SQLEnum(NotificationEventType),
        nullable=False,
        index=True,
        comment="Type of event this preference applies to",
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel),
        nullable=False,
        index=True,
        comment="Notification channel",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether notifications are enabled for this combination",
    )

    # Timing Preferences
    advance_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Minutes in advance for reminder notifications",
    )
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(
        String(5),  # Format: "22:00"
        nullable=True,
        comment="Start time for quiet hours (no notifications)",
    )
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(
        String(5),  # Format: "08:00"
        nullable=True,
        comment="End time for quiet hours",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When preference was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When preference was last updated",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notification_preferences",
        lazy="select",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id", "event_type", "channel",
            name="uq_user_event_channel"
        ),
        CheckConstraint(
            "advance_minutes IS NULL OR advance_minutes >= 0",
            name="ck_positive_advance_minutes"
        ),
        Index("ix_notification_prefs_user_event", "user_id", "event_type"),
        Index("ix_notification_prefs_channel_enabled", "channel", "enabled"),
    )


class NotificationTemplate(Base):
    """Configurable notification templates."""

    __tablename__ = "notification_templates"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for notification template",
    )

    # Template Identification
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique template name/identifier",
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        SQLEnum(NotificationEventType),
        nullable=False,
        index=True,
        comment="Event type this template handles",
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel),
        nullable=False,
        index=True,
        comment="Channel this template is for",
    )

    # Template Content
    subject: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Subject line for email/SMS title",
    )
    body_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Template body with variable placeholders",
    )
    variables: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Available template variables and descriptions",
    )

    # Template Configuration
    priority: Mapped[NotificationPriority] = mapped_column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.NORMAL,
        nullable=False,
        comment="Default priority for this template",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether template is active",
    )
    locale: Mapped[str] = mapped_column(
        String(10),
        default="pt_BR",
        nullable=False,
        comment="Language/locale for this template",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When template was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When template was last updated",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "event_type", "channel", "locale",
            name="uq_template_event_channel_locale"
        ),
        Index("ix_notification_templates_active", "is_active"),
        Index("ix_notification_templates_event_channel", "event_type", "channel"),
    )


class NotificationQueue(Base):
    """Queue for scheduled and pending notifications."""

    __tablename__ = "notification_queue"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for queued notification",
    )

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User to send notification to",
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("notification_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Template to use for notification",
    )

    # Queue Configuration
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel),
        nullable=False,
        index=True,
        comment="Channel to send notification through",
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.NORMAL,
        nullable=False,
        index=True,
        comment="Notification priority",
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current notification status",
    )

    # Content and Context
    subject: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Rendered subject line",
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Rendered notification body",
    )
    context_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Context data used for rendering",
    )

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="When notification should be sent",
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When notification was actually sent",
    )

    # Retry Configuration
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of retry attempts",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="Maximum retry attempts",
    )
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When to attempt next retry",
    )

    # Error Tracking
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Last error message if failed",
    )

    # External References
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="External correlation ID (booking ID, payment ID, etc.)",
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="External service notification ID",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When notification was queued",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When notification was last updated",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        lazy="select",
    )
    template: Mapped["NotificationTemplate"] = relationship(
        "NotificationTemplate",
        lazy="select",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "retry_count >= 0",
            name="ck_positive_retry_count"
        ),
        CheckConstraint(
            "max_retries >= 0",
            name="ck_positive_max_retries"
        ),
        Index("ix_notification_queue_status_scheduled", "status", "scheduled_at"),
        Index("ix_notification_queue_priority_status", "priority", "status"),
        Index("ix_notification_queue_correlation", "correlation_id"),
        Index("ix_notification_queue_retry", "next_retry_at", "retry_count"),
    )


class NotificationLog(Base):
    """Log of all notification delivery attempts."""

    __tablename__ = "notification_logs"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for log entry",
    )

    # Foreign Keys
    queue_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("notification_queue.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated queue item",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User notification was sent to",
    )

    # Delivery Information
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel),
        nullable=False,
        index=True,
        comment="Channel used for delivery",
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        SQLEnum(NotificationEventType),
        nullable=False,
        index=True,
        comment="Event type that triggered notification",
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus),
        nullable=False,
        index=True,
        comment="Final delivery status",
    )

    # Content
    subject: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Subject line that was sent",
    )

    # Delivery Details
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="When delivery was attempted",
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When delivery was confirmed",
    )

    # External Service Integration
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="External service notification ID",
    )
    provider_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Response from notification provider",
    )

    # Error Tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if delivery failed",
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Error code from provider",
    )

    # Context
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Correlation ID for tracking",
    )

    # Relationships
    queue_item: Mapped[Optional["NotificationQueue"]] = relationship(
        "NotificationQueue",
        lazy="select",
    )
    user: Mapped["User"] = relationship(
        "User",
        lazy="select",
    )

    # Constraints
    __table_args__ = (
        Index("ix_notification_logs_user_event", "user_id", "event_type"),
        Index("ix_notification_logs_status_sent", "status", "sent_at"),
        Index("ix_notification_logs_channel_status", "channel", "status"),
        Index("ix_notification_logs_correlation", "correlation_id"),
    )
