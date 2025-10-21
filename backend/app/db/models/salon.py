"""Salon model for beauty establishments."""

from typing import TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.overbooking import OverbookingConfig


class Salon(Base, IDMixin, TimestampMixin):
    """
    Salon model representing beauty establishments.

    A salon is owned by a user with SALON_OWNER role and can have
    multiple professionals, services, and operating units.
    """

    __tablename__ = "salons"

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Salon business name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Salon description and amenities",
    )

    # Business registration
    cnpj: Mapped[str] = mapped_column(
        String(18),
        unique=True,
        nullable=False,
        index=True,
        comment="Brazilian business tax ID (CNPJ)",
    )

    # Contact information
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Primary contact phone",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact email address",
    )

    # Address
    address_street: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Street address",
    )
    address_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Street number",
    )
    address_complement: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Address complement (apt, suite, etc)",
    )
    address_neighborhood: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Neighborhood/district",
    )
    address_city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="City",
    )
    address_state: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="State code (UF)",
    )
    address_zipcode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="ZIP/Postal code (CEP)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether salon is accepting bookings",
    )

    # Relationships
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Salon owner (user with SALON_OWNER role)",
    )

    # Overbooking configurations for this salon
    overbooking_configs: Mapped[list["OverbookingConfig"]] = relationship(
        "OverbookingConfig",
        back_populates="salon",
        lazy="select"
    )

    def __repr__(self) -> str:
        """String representation of Salon."""
        return f"<Salon(id={self.id}, name='{self.name}', cnpj='{self.cnpj}')>"
