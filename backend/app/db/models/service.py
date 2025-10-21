"""Service model for beauty services catalog."""

from typing import TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.overbooking import OverbookingConfig


class Service(Base, IDMixin, TimestampMixin):
    """
    Service model representing beauty services offered by salons.

    Each service has a name, duration, price and is associated with a salon.
    Can be booked by clients through the booking system.
    """

    __tablename__ = "services"

    # Salon relationship
    salon_id: Mapped[int] = mapped_column(
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Salon offering this service",
    )

    # Service information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Service name (e.g., Haircut, Manicure, Massage)",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed service description",
    )

    # Duration in minutes
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Service duration in minutes",
    )

    # Pricing
    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Service price in BRL",
    )

    # Category for organization
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Service category (e.g., Hair, Nails, Skin)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether service is available for booking",
    )

    # Requirements
    requires_deposit: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether service requires deposit/prepayment",
    )
    deposit_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Deposit percentage if required (0-100)",
    )

    # Relationships
    # salon: Mapped["Salon"] = relationship(
    #     back_populates="services",
    #     lazy="selectin",
    # )
    # bookings: Mapped[list["Booking"]] = relationship(
    #     back_populates="service",
    #     lazy="selectin",
    # )

    # Overbooking configurations for this service
    overbooking_configs: Mapped[list["OverbookingConfig"]] = relationship(
        "OverbookingConfig",
        back_populates="service",
        lazy="select"
    )

    # Reviews for this service
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="service",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of Service."""
        return (
            f"<Service(id={self.id}, name='{self.name}', "
            f"price={self.price}, duration={self.duration_minutes}min)>"
        )
