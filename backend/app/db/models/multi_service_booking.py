"""Multi-service booking models for package reservations."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    String,
    Text,
    Numeric,
    ForeignKey,
    Enum as SQLEnum,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.user import User
    from backend.app.db.models.professional import Professional


class MultiServiceBookingStatus(str, Enum):
    """Multi-service booking status enumeration."""

    PENDING = "pending"  # Awaiting confirmation/payment
    CONFIRMED = "confirmed"  # All services confirmed and scheduled
    PARTIALLY_COMPLETED = "partially_completed"  # Some services completed
    COMPLETED = "completed"  # All services completed successfully
    CANCELLED = "cancelled"  # Cancelled by client or salon
    PARTIALLY_CANCELLED = "partially_cancelled"  # Some services cancelled


class MultiServiceBooking(Base, IDMixin, TimestampMixin):
    """
    Multi-service booking model for package reservations.

    Manages bookings that contain multiple services scheduled consecutively
    or across different time slots, with transaction-like behavior.
    """

    __tablename__ = "multi_service_bookings"

    # Client relationship
    client_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Client who made the multi-service booking",
    )

    # Professional relationship (can be the same for all services or different)
    primary_professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Primary professional for the booking package",
    )

    # Package details
    package_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Name/description of the service package",
    )

    # Status tracking
    status: Mapped[MultiServiceBookingStatus] = mapped_column(
        SQLEnum(MultiServiceBookingStatus, native_enum=False),
        nullable=False,
        default=MultiServiceBookingStatus.PENDING,
        index=True,
        comment="Current multi-service booking status",
    )

    # Pricing (calculated totals)
    total_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total price for all services (BRL)",
    )

    total_duration_minutes: Mapped[int] = mapped_column(
        nullable=False,
        comment="Total duration for all services in minutes",
    )

    total_services_count: Mapped[int] = mapped_column(
        nullable=False,
        comment="Number of services in this package",
    )

    # Scheduling
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Start time of the first service",
    )

    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="End time of the last service",
    )

    # Additional info
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Special notes or instructions for the package",
    )

    # Cancellation
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for cancellation if applicable",
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when booking was cancelled",
    )

    cancelled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who cancelled the booking",
    )

    # Relationships
    client: Mapped["User"] = relationship(
        "User",
        foreign_keys=[client_id],
        back_populates="multi_service_bookings",
        lazy="select"
    )

    primary_professional: Mapped["Professional"] = relationship(
        "Professional",
        foreign_keys=[primary_professional_id],
        back_populates="multi_service_bookings",
        lazy="select"
    )

    cancelled_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[cancelled_by_id],
        lazy="select"
    )

    # Relationship to individual service bookings
    individual_bookings: Mapped[list["Booking"]] = relationship(
        "Booking",
        back_populates="multi_service_booking",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<MultiServiceBooking(id={self.id}, client_id={self.client_id}, status={self.status}, services={self.total_services_count})>"

    @property
    def is_active(self) -> bool:
        """Check if booking is in an active state."""
        return self.status not in (
            MultiServiceBookingStatus.CANCELLED,
            MultiServiceBookingStatus.COMPLETED
        )

    @property
    def can_be_cancelled(self) -> bool:
        """Check if booking can be cancelled."""
        return self.status in (
            MultiServiceBookingStatus.PENDING,
            MultiServiceBookingStatus.CONFIRMED,
            MultiServiceBookingStatus.PARTIALLY_COMPLETED
        )

    @property
    def is_in_progress(self) -> bool:
        """Check if any service in the package is in progress."""
        return self.status == MultiServiceBookingStatus.PARTIALLY_COMPLETED

    def calculate_completion_percentage(self) -> float:
        """Calculate completion percentage based on individual bookings."""
        if not self.individual_bookings:
            return 0.0

        completed_count = sum(
            1 for booking in self.individual_bookings
            if booking.status in ["completed", "no_show"]
        )

        return (completed_count / len(self.individual_bookings)) * 100
