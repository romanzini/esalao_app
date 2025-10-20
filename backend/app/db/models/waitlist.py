"""Waitlist model for managing client waiting lists for services."""

from datetime import datetime, timezone, time
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, String, Float, Time, Enum as SQLEnum, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base


class WaitlistStatus(str, Enum):
    """Status of waitlist entry."""

    WAITING = "waiting"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WaitlistPriority(str, Enum):
    """Priority levels for waitlist entries."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Waitlist(Base):
    """
    Waitlist entry for booking requests when slots are unavailable.

    Manages the queue of clients waiting for specific time slots,
    services, or professionals with priority-based ordering.
    """

    __tablename__ = "waitlists"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for waitlist entry",
    )

    # Foreign Keys
    client_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Client requesting the slot",
    )
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Requested professional",
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Requested service",
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Salon/unit where service will be performed",
    )

    # Waitlist Details
    preferred_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Preferred appointment time",
    )
    flexibility_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False,
        comment="Hours of flexibility around preferred time",
    )
    status: Mapped[WaitlistStatus] = mapped_column(
        SQLEnum(WaitlistStatus),
        default=WaitlistStatus.WAITING,
        nullable=False,
        index=True,
        comment="Current status of waitlist entry",
    )
    priority: Mapped[WaitlistPriority] = mapped_column(
        SQLEnum(WaitlistPriority),
        default=WaitlistPriority.NORMAL,
        nullable=False,
        index=True,
        comment="Priority level in the queue",
    )

    # Queue Management
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Position in the waitlist queue",
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        comment="When client joined the waitlist",
    )

    # Offer Management
    offered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When slot was offered to client",
    )
    offered_slot_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start time of offered slot",
    )
    offered_slot_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="End time of offered slot",
    )
    offer_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the offer expires",
    )

    # Response Management
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When client responded to offer",
    )
    response_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Client's response notes or decline reason",
    )

    # Booking Creation
    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        comment="Created booking if offer was accepted",
    )

    # Client Preferences
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes or special requests",
    )

    # Notification preferences
    notify_email: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Send email notifications",
    )
    notify_sms: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Send SMS notifications",
    )
    notify_push: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Send push notifications",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "client_id", "professional_id", "service_id", "preferred_datetime",
            name="uq_waitlist_client_professional_service_datetime"
        ),
    )

    # Relationships
    client: Mapped["User"] = relationship(
        foreign_keys=[client_id],
        lazy="selectin",
    )
    professional: Mapped["Professional"] = relationship(
        lazy="selectin",
    )
    service: Mapped["Service"] = relationship(
        lazy="selectin",
    )
    unit: Mapped["Salon"] = relationship(
        lazy="selectin",
    )
    booking: Mapped["Booking | None"] = relationship(
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of Waitlist."""
        return (
            f"<Waitlist(id={self.id}, "
            f"client_id={self.client_id}, "
            f"professional_id={self.professional_id}, "
            f"service_id={self.service_id}, "
            f"status={self.status.value}, "
            f"position={self.position}, "
            f"preferred_datetime={self.preferred_datetime})>"
        )

    @property
    def is_active(self) -> bool:
        """Check if waitlist entry is still active."""
        return self.status == WaitlistStatus.ACTIVE

    @property
    def has_pending_offer(self) -> bool:
        """Check if there's a pending offer waiting for response."""
        return self.status == WaitlistStatus.OFFERED

    @property
    def is_offer_expired(self) -> bool:
        """Check if the current offer has expired."""
        if not self.offer_expires_at:
            return False
        return datetime.utcnow() > self.offer_expires_at

    def can_receive_offer(self) -> bool:
        """Check if this entry can receive a new offer."""
        return (
            self.status == WaitlistStatus.ACTIVE and
            not self.has_pending_offer and
            not self.is_offer_expired
        )

    def get_time_window(self) -> tuple[datetime, datetime]:
        """Get the acceptable time window based on preferred time and flexibility."""
        from datetime import timedelta

        start_time = self.preferred_datetime - timedelta(hours=self.flexibility_hours // 2)
        end_time = self.preferred_datetime + timedelta(hours=self.flexibility_hours // 2)

        return start_time, end_time
