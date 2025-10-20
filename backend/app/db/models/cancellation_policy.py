"""Cancellation policy models for database persistence."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    String,
    Integer,
    Numeric,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, IDMixin, TimestampMixin


class CancellationPolicyStatus(str, Enum):
    """Cancellation policy status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class CancellationPolicy(Base, IDMixin, TimestampMixin):
    """
    Cancellation policy model.

    Defines the cancellation rules for a salon/unit including
    multiple tiers with different advance notice requirements.
    """

    __tablename__ = "cancellation_policies"

    # Policy identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Policy name for identification",
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Policy description",
    )

    # Policy status
    status: Mapped[CancellationPolicyStatus] = mapped_column(
        SQLEnum(CancellationPolicyStatus),
        default=CancellationPolicyStatus.DRAFT,
        nullable=False,
        comment="Policy status",
    )

    # Policy scope
    salon_id: Mapped[int | None] = mapped_column(
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=True,
        comment="Salon this policy applies to (null = global)",
    )

    # Default policy flag
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the default policy",
    )

    # Policy validity
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When policy becomes effective",
    )

    effective_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When policy expires (null = no expiry)",
    )

    # Relationships
    # salon: Mapped["Salon"] = relationship(
    #     back_populates="cancellation_policies",
    #     lazy="selectin",
    # )

    tiers: Mapped[list["CancellationTier"]] = relationship(
        back_populates="policy",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="CancellationTier.advance_notice_hours.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="valid_policy_period",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<CancellationPolicy(id={self.id}, "
            f"name='{self.name}', "
            f"status={self.status.value})>"
        )


class CancellationTier(Base, IDMixin, TimestampMixin):
    """
    Cancellation tier model.

    Defines a specific tier within a cancellation policy with
    advance notice requirements and associated fees.
    """

    __tablename__ = "cancellation_tiers"

    # Policy relationship
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("cancellation_policies.id", ondelete="CASCADE"),
        nullable=False,
        comment="Cancellation policy this tier belongs to",
    )

    # Tier identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Tier name (e.g., 'Last Minute', 'Standard')",
    )

    # Advance notice requirement
    advance_notice_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Minimum advance notice required in hours",
    )

    # Fee configuration
    fee_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Fee type: 'percentage' or 'fixed'",
    )

    fee_value: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Fee value (percentage 0-100 or fixed amount)",
    )

    # Tier behavior
    allows_refund: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether refund is allowed for this tier",
    )

    # Display order
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Display order within policy (lower = higher priority)",
    )

    # Relationships
    policy: Mapped["CancellationPolicy"] = relationship(
        back_populates="tiers",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "advance_notice_hours",
            name="unique_policy_advance_notice",
        ),
        UniqueConstraint(
            "policy_id",
            "display_order",
            name="unique_policy_display_order",
        ),
        CheckConstraint(
            "advance_notice_hours >= 0",
            name="valid_advance_notice",
        ),
        CheckConstraint(
            "fee_type IN ('percentage', 'fixed')",
            name="valid_fee_type",
        ),
        CheckConstraint(
            "(fee_type = 'percentage' AND fee_value >= 0 AND fee_value <= 100) OR "
            "(fee_type = 'fixed' AND fee_value >= 0)",
            name="valid_fee_value",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<CancellationTier(id={self.id}, "
            f"name='{self.name}', "
            f"advance_notice_hours={self.advance_notice_hours}, "
            f"fee_type={self.fee_type}, "
            f"fee_value={self.fee_value})>"
        )
