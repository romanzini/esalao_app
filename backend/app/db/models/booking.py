"""Booking model for service reservations."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    String,
    Text,
    Numeric,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, IDMixin, TimestampMixin


class BookingStatus(str, Enum):
    """Booking status enumeration."""

    PENDING = "pending"  # Awaiting confirmation/payment
    CONFIRMED = "confirmed"  # Confirmed and scheduled
    IN_PROGRESS = "in_progress"  # Service is being performed
    COMPLETED = "completed"  # Service completed successfully
    CANCELLED = "cancelled"  # Cancelled by client or salon
    NO_SHOW = "no_show"  # Client didn't show up


class Booking(Base, IDMixin, TimestampMixin):
    """
    Booking model representing service reservations.

    Manages the complete booking lifecycle from creation to completion,
    including status tracking, payment, and cancellation policies.
    """

    __tablename__ = "bookings"

    # Client relationship
    client_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Client who made the booking",
    )

    # Professional relationship
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Professional assigned to this booking",
    )

    # Service relationship
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Service to be performed",
    )

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Scheduled date and time for the service",
    )
    duration_minutes: Mapped[int] = mapped_column(
        nullable=False,
        comment="Expected duration in minutes (copied from service)",
    )

    # Status tracking
    status: Mapped[BookingStatus] = mapped_column(
        SQLEnum(BookingStatus, native_enum=False),
        nullable=False,
        default=BookingStatus.PENDING,
        index=True,
        comment="Current booking status",
    )

    # Pricing (snapshot at booking time)
    service_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Service price at booking time (BRL)",
    )
    deposit_amount: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Deposit/prepayment amount (BRL)",
    )

    # Client notes
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Client notes or special requests",
    )

    # Cancellation tracking
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When booking was cancelled",
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Reason for cancellation",
    )
    cancelled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who cancelled the booking",
    )

    # Completion tracking
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When service was completed",
    )

    # No-show tracking
    marked_no_show_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When client was marked as no-show",
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
    cancelled_by: Mapped["User"] = relationship(
        foreign_keys=[cancelled_by_id],
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="booking",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of Booking."""
        return (
            f"<Booking(id={self.id}, "
            f"client_id={self.client_id}, "
            f"professional_id={self.professional_id}, "
            f"status={self.status.value}, "
            f"scheduled_at={self.scheduled_at})>"
        )
