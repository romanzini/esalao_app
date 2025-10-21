"""Professional model for service providers."""

from typing import List, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import json

from backend.app.db.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.overbooking import OverbookingConfig
    from backend.app.db.models.user import User
    from backend.app.db.models.salon import Salon


class Professional(Base, IDMixin, TimestampMixin):
    """
    Professional model representing service providers.

    A professional is linked to a User account and works at a Salon,
    providing specific services. Can have multiple specialties and
    custom availability schedules.
    """

    __tablename__ = "professionals"

    # User relationship
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="User account for this professional",
    )

    # Salon relationship
    salon_id: Mapped[int] = mapped_column(
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Salon where professional works",
    )

    # Professional information
    specialties: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="List of specialties (e.g., haircut, manicure, massage)",
    )
    bio: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Professional biography and experience",
    )

    # Professional registration (optional)
    license_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Professional license/registration number",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether professional is accepting bookings",
    )

    # Commission settings
    commission_percentage: Mapped[float] = mapped_column(
        default=50.0,
        nullable=False,
        comment="Commission percentage (0-100) for this professional",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        lazy="selectin",
    )
    salon: Mapped["Salon"] = relationship(
        lazy="selectin",
    )
    
    # Overbooking configurations for this professional
    overbooking_configs: Mapped[list["OverbookingConfig"]] = relationship(
        "OverbookingConfig",
        back_populates="professional",
        lazy="select"
    )

    def __repr__(self) -> str:
        """String representation of Professional."""
        return (
            f"<Professional(id={self.id}, "
            f"user_id={self.user_id}, "
            f"salon_id={self.salon_id})>"
        )
