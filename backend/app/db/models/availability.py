"""Availability model for professional working hours."""

from datetime import time
from enum import Enum

from sqlalchemy import Time, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.models.base import Base, IDMixin, TimestampMixin


class DayOfWeek(int, Enum):
    """Day of week enumeration (0=Monday, 6=Sunday)."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class Availability(Base, IDMixin, TimestampMixin):
    """
    Availability model for professional working hours.

    Defines recurring weekly availability slots for professionals.
    Each slot represents a time range on a specific day of the week.

    Example: Monday 09:00-12:00, Tuesday 14:00-18:00
    """

    __tablename__ = "availabilities"

    # Professional relationship
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Professional for this availability slot",
    )

    # Day of week
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        SQLEnum(DayOfWeek, native_enum=False),
        nullable=False,
        comment="Day of week (0=Monday, 6=Sunday)",
    )

    # Time range
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Start time of availability slot",
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="End time of availability slot",
    )

    # Slot configuration
    slot_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
        comment="Duration of each booking slot in minutes (default: 30)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether this availability slot is active",
    )

    # Relationships
    # professional: Mapped["Professional"] = relationship(
    #     back_populates="availabilities",
    #     lazy="selectin",
    # )

    def __repr__(self) -> str:
        """String representation of Availability."""
        return (
            f"<Availability(id={self.id}, "
            f"professional_id={self.professional_id}, "
            f"day={self.day_of_week.name}, "
            f"{self.start_time}-{self.end_time})>"
        )
