"""User model for authentication and authorization."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.payment import Payment
    from backend.app.db.models.review import Review, ReviewHelpfulness, ReviewFlag
    from backend.app.db.models.multi_service_booking import MultiServiceBooking
    from backend.app.db.models.notifications import NotificationPreferences, NotificationQueue


class UserRole(str, Enum):
    """User role enumeration for RBAC."""

    CLIENT = "client"
    PROFESSIONAL = "professional"
    SALON_OWNER = "salon_owner"
    ADMIN = "admin"


class User(Base, IDMixin, TimestampMixin):
    """
    User model for authentication and profile management.

    Supports multiple roles for flexible authorization:
    - CLIENT: Regular customers who book services
    - PROFESSIONAL: Service providers working at salons
    - SALON_OWNER: Business owners managing salons
    - ADMIN: Platform administrators
    """

    __tablename__ = "users"

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="User email address (login identifier)",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Argon2 password hash",
    )

    # Profile fields
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User full name",
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Contact phone number",
    )

    # Authorization fields
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False),
        nullable=False,
        default=UserRole.CLIENT,
        comment="User role for RBAC",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether user account is active",
    )
    is_verified: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether email is verified",
    )

    # Account metadata
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful login",
    )

    # Relationships (lazy loaded to avoid circular imports)
    # salons: Mapped[list["Salon"]] = relationship(
    #     back_populates="owner",
    #     lazy="selectin",
    # )
    # Booking relationships - commented to avoid ambiguity with multi_service_bookings
    # bookings: Mapped[list["Booking"]] = relationship(
    #     back_populates="client",
    #     lazy="selectin",
    # )
    multi_service_bookings: Mapped[list["MultiServiceBooking"]] = relationship(
        back_populates="client",
        foreign_keys="MultiServiceBooking.client_id",
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )

    # Notification relationships
    notification_preferences: Mapped[list["NotificationPreferences"]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["NotificationQueue"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )

    # Review relationships
    client_reviews: Mapped[list["Review"]] = relationship(
        foreign_keys="Review.client_id",
        back_populates="client",
        lazy="selectin",
    )
    professional_reviews: Mapped[list["Review"]] = relationship(
        foreign_keys="Review.professional_id",
        back_populates="professional",
        lazy="selectin",
    )
    review_helpfulness_votes: Mapped[list["ReviewHelpfulness"]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    review_flags: Mapped[list["ReviewFlag"]] = relationship(
        foreign_keys="ReviewFlag.reporter_id",
        back_populates="reporter",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return (
            f"<User(id={self.id}, email='{self.email}', "
            f"role='{self.role.value}')>"
        )
