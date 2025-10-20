"""Loyalty points system model for customer retention and rewards."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, String, Float, Enum as SQLEnum, Text, UniqueConstraint, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base


class PointTransactionType(str, Enum):
    """Types of point transactions."""

    EARNED = "earned"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    BONUS = "bonus"
    ADJUSTMENT = "adjustment"
    REFUND = "refund"


class LoyaltyTier(str, Enum):
    """Customer loyalty tiers."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class PointEarnReason(str, Enum):
    """Reasons for earning points."""

    BOOKING_COMPLETED = "booking_completed"
    REFERRAL = "referral"
    REVIEW_SUBMITTED = "review_submitted"
    BIRTHDAY_BONUS = "birthday_bonus"
    PROMOTION = "promotion"
    SIGNUP_BONUS = "signup_bonus"
    LOYALTY_MILESTONE = "loyalty_milestone"


class PointRedemptionType(str, Enum):
    """Types of point redemptions."""

    DISCOUNT = "discount"
    FREE_SERVICE = "free_service"
    UPGRADE = "upgrade"
    GIFT_CARD = "gift_card"
    MERCHANDISE = "merchandise"


class LoyaltyAccount(Base):
    """Customer loyalty account with points and tier tracking."""

    __tablename__ = "loyalty_accounts"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for loyalty account",
    )

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="User who owns this loyalty account",
    )

    # Points and Tier Information
    current_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Current available points balance",
    )
    lifetime_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total points earned throughout account lifetime",
    )
    current_tier: Mapped[LoyaltyTier] = mapped_column(
        SQLEnum(LoyaltyTier),
        default=LoyaltyTier.BRONZE,
        nullable=False,
        index=True,
        comment="Current loyalty tier",
    )
    tier_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Points accumulated in current tier period",
    )

    # Tier Progress
    next_tier_threshold: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Points needed to reach next tier",
    )
    tier_expiry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When current tier expires (if applicable)",
    )

    # Account Metadata
    join_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When loyalty account was created",
    )
    last_activity_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last point transaction date",
    )

    # Account Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether account is active",
    )
    suspended_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account suspension end date",
    )

    # Statistics
    total_bookings: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total completed bookings",
    )
    total_spent: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total amount spent",
    )
    referrals_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of successful referrals",
    )

    # Preferences
    email_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Receive email notifications about points",
    )
    sms_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Receive SMS notifications about points",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Last update timestamp",
    )

    # Indexes
    __table_args__ = (
        Index("idx_loyalty_user_tier", "user_id", "current_tier"),
        Index("idx_loyalty_points", "current_points"),
        Index("idx_loyalty_tier_points", "tier_points"),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        lazy="selectin",
    )

    @property
    def points_to_next_tier(self) -> Optional[int]:
        """Calculate points needed to reach next tier."""
        if self.next_tier_threshold is None:
            return None
        return max(0, self.next_tier_threshold - self.tier_points)

    @property
    def tier_progress_percentage(self) -> float:
        """Calculate tier progress as percentage."""
        if self.next_tier_threshold is None or self.next_tier_threshold == 0:
            return 100.0
        return min(100.0, (self.tier_points / self.next_tier_threshold) * 100)

    @property
    def is_suspended(self) -> bool:
        """Check if account is currently suspended."""
        if self.suspended_until is None:
            return False
        return datetime.now(timezone.utc) < self.suspended_until

    def can_redeem_points(self, amount: int) -> bool:
        """Check if user can redeem specified amount of points."""
        return (
            self.is_active and
            not self.is_suspended and
            self.current_points >= amount and
            amount > 0
        )

    def __repr__(self) -> str:
        """String representation of LoyaltyAccount."""
        return (
            f"<LoyaltyAccount(id={self.id}, "
            f"user_id={self.user_id}, "
            f"current_points={self.current_points}, "
            f"tier={self.current_tier.value}, "
            f"active={self.is_active})>"
        )


class PointTransaction(Base):
    """Point transaction history for loyalty accounts."""

    __tablename__ = "point_transactions"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for point transaction",
    )

    # Foreign Keys
    loyalty_account_id: Mapped[int] = mapped_column(
        ForeignKey("loyalty_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Loyalty account for this transaction",
    )
    booking_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related booking (if applicable)",
    )

    # Transaction Details
    transaction_type: Mapped[PointTransactionType] = mapped_column(
        SQLEnum(PointTransactionType),
        nullable=False,
        index=True,
        comment="Type of point transaction",
    )
    points_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of points (positive for earned, negative for redeemed)",
    )
    balance_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Point balance after this transaction",
    )

    # Transaction Context
    earn_reason: Mapped[Optional[PointEarnReason]] = mapped_column(
        SQLEnum(PointEarnReason),
        nullable=True,
        comment="Reason for earning points",
    )
    redemption_type: Mapped[Optional[PointRedemptionType]] = mapped_column(
        SQLEnum(PointRedemptionType),
        nullable=True,
        comment="Type of point redemption",
    )

    # Monetary Context
    monetary_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Monetary value associated with transaction",
    )
    discount_applied: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Discount amount applied (for redemptions)",
    )

    # Expiration
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When these points expire (for earned points)",
    )
    is_expired: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether these points have expired",
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of transaction",
    )
    reference_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="External reference ID",
    )

    # System Fields
    processed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who processed this transaction (for manual adjustments)",
    )

    # Timestamps
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="When transaction occurred",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record creation timestamp",
    )

    # Indexes
    __table_args__ = (
        Index("idx_point_transaction_account_date", "loyalty_account_id", "transaction_date"),
        Index("idx_point_transaction_type_date", "transaction_type", "transaction_date"),
        Index("idx_point_transaction_booking", "booking_id"),
        Index("idx_point_transaction_expiry", "expiry_date", "is_expired"),
    )

    # Relationships
    loyalty_account: Mapped["LoyaltyAccount"] = relationship(
        foreign_keys=[loyalty_account_id],
        lazy="selectin",
    )
    booking: Mapped["Booking"] = relationship(
        foreign_keys=[booking_id],
        lazy="selectin",
    )
    processed_by: Mapped["User"] = relationship(
        foreign_keys=[processed_by_user_id],
        lazy="selectin",
    )

    @property
    def is_earning_transaction(self) -> bool:
        """Check if this is a point earning transaction."""
        return self.transaction_type in [
            PointTransactionType.EARNED,
            PointTransactionType.BONUS,
            PointTransactionType.REFUND
        ]

    @property
    def is_spending_transaction(self) -> bool:
        """Check if this is a point spending transaction."""
        return self.transaction_type in [
            PointTransactionType.REDEEMED,
            PointTransactionType.EXPIRED,
            PointTransactionType.ADJUSTMENT
        ]

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until points expire."""
        if self.expiry_date is None or self.is_expired:
            return None
        days = (self.expiry_date - datetime.now(timezone.utc)).days
        return max(0, days)

    def __repr__(self) -> str:
        """String representation of PointTransaction."""
        return (
            f"<PointTransaction(id={self.id}, "
            f"account_id={self.loyalty_account_id}, "
            f"type={self.transaction_type.value}, "
            f"points={self.points_amount}, "
            f"date={self.transaction_date})>"
        )


class LoyaltyReward(Base):
    """Available rewards that can be redeemed with points."""

    __tablename__ = "loyalty_rewards"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for loyalty reward",
    )

    # Reward Details
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Reward name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed reward description",
    )
    redemption_type: Mapped[PointRedemptionType] = mapped_column(
        SQLEnum(PointRedemptionType),
        nullable=False,
        index=True,
        comment="Type of redemption",
    )

    # Point Cost
    point_cost: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Points required to redeem this reward",
    )
    monetary_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Equivalent monetary value",
    )

    # Availability
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether reward is currently available",
    )
    available_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When reward becomes available",
    )
    available_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When reward expires",
    )

    # Limits
    max_redemptions_per_user: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum times a user can redeem this reward",
    )
    total_available: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of this reward available",
    )
    total_redeemed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of times this reward has been redeemed",
    )

    # Tier Requirements
    minimum_tier: Mapped[Optional[LoyaltyTier]] = mapped_column(
        SQLEnum(LoyaltyTier),
        nullable=True,
        comment="Minimum tier required to redeem",
    )

    # Service Association
    service_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Associated service (for service-based rewards)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Last update timestamp",
    )

    # Indexes
    __table_args__ = (
        Index("idx_loyalty_reward_cost_active", "point_cost", "is_active"),
        Index("idx_loyalty_reward_type", "redemption_type"),
        Index("idx_loyalty_reward_tier", "minimum_tier"),
        Index("idx_loyalty_reward_availability", "available_from", "available_until"),
    )

    # Relationships
    service: Mapped["Service"] = relationship(
        foreign_keys=[service_id],
        lazy="selectin",
    )

    @property
    def is_available(self) -> bool:
        """Check if reward is currently available."""
        now = datetime.now(timezone.utc)

        if not self.is_active:
            return False

        if self.available_from and now < self.available_from:
            return False

        if self.available_until and now > self.available_until:
            return False

        if self.total_available and self.total_redeemed >= self.total_available:
            return False

        return True

    @property
    def remaining_quantity(self) -> Optional[int]:
        """Calculate remaining quantity available."""
        if self.total_available is None:
            return None
        return max(0, self.total_available - self.total_redeemed)

    def can_be_redeemed_by_tier(self, user_tier: LoyaltyTier) -> bool:
        """Check if reward can be redeemed by user with given tier."""
        if self.minimum_tier is None:
            return True

        tier_hierarchy = {
            LoyaltyTier.BRONZE: 0,
            LoyaltyTier.SILVER: 1,
            LoyaltyTier.GOLD: 2,
            LoyaltyTier.PLATINUM: 3,
            LoyaltyTier.DIAMOND: 4,
        }

        return tier_hierarchy.get(user_tier, 0) >= tier_hierarchy.get(self.minimum_tier, 0)

    def __repr__(self) -> str:
        """String representation of LoyaltyReward."""
        return (
            f"<LoyaltyReward(id={self.id}, "
            f"name='{self.name}', "
            f"cost={self.point_cost}, "
            f"type={self.redemption_type.value}, "
            f"active={self.is_active})>"
        )
