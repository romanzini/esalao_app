"""Loyalty system service for business logic and workflows."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from backend.app.db.repositories.loyalty import LoyaltyRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.db.models.loyalty import (
    LoyaltyAccount, PointTransaction, LoyaltyReward,
    PointTransactionType, LoyaltyTier, PointEarnReason, PointRedemptionType
)
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.core.exceptions import ValidationError, NotFoundError


@dataclass
class TierBenefits:
    """Benefits for each loyalty tier."""
    name: str
    point_multiplier: float
    birthday_bonus: int
    referral_bonus: int
    minimum_points: int
    next_tier_points: Optional[int] = None


class LoyaltyService:
    """Service for loyalty system business logic."""

    # Tier configuration
    TIER_CONFIG = {
        LoyaltyTier.BRONZE: TierBenefits(
            name="Bronze",
            point_multiplier=1.0,
            birthday_bonus=100,
            referral_bonus=50,
            minimum_points=0,
            next_tier_points=1000
        ),
        LoyaltyTier.SILVER: TierBenefits(
            name="Silver",
            point_multiplier=1.2,
            birthday_bonus=200,
            referral_bonus=75,
            minimum_points=1000,
            next_tier_points=3000
        ),
        LoyaltyTier.GOLD: TierBenefits(
            name="Gold",
            point_multiplier=1.5,
            birthday_bonus=300,
            referral_bonus=100,
            minimum_points=3000,
            next_tier_points=7000
        ),
        LoyaltyTier.PLATINUM: TierBenefits(
            name="Platinum",
            point_multiplier=2.0,
            birthday_bonus=500,
            referral_bonus=150,
            minimum_points=7000,
            next_tier_points=15000
        ),
        LoyaltyTier.DIAMOND: TierBenefits(
            name="Diamond",
            point_multiplier=2.5,
            birthday_bonus=1000,
            referral_bonus=200,
            minimum_points=15000,
            next_tier_points=None  # No next tier
        ),
    }

    # Point earning rates
    POINTS_PER_DOLLAR = 10  # Base points per dollar spent
    REVIEW_POINTS = 50
    SIGNUP_BONUS = 500

    # Point expiration
    POINT_EXPIRY_MONTHS = 24

    def __init__(
        self,
        loyalty_repository: LoyaltyRepository,
        booking_repository: BookingRepository,
        user_repository: UserRepository
    ):
        self.loyalty_repo = loyalty_repository
        self.booking_repo = booking_repository
        self.user_repo = user_repository

    # Account Management
    async def create_loyalty_account(self, user_id: int) -> LoyaltyAccount:
        """Create a new loyalty account for a user."""
        # Check if account already exists
        existing_account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if existing_account:
            raise ValidationError("User already has a loyalty account")

        # Create account with signup bonus
        account = await self.loyalty_repo.create_loyalty_account(
            user_id=user_id,
            current_tier=LoyaltyTier.BRONZE
        )

        # Award signup bonus
        await self._award_points(
            account.id,
            self.SIGNUP_BONUS,
            PointEarnReason.SIGNUP_BONUS,
            description="Welcome bonus for joining loyalty program"
        )

        return account

    async def get_or_create_loyalty_account(self, user_id: int) -> LoyaltyAccount:
        """Get existing loyalty account or create new one."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            account = await self.create_loyalty_account(user_id)
        return account

    async def get_loyalty_account(self, user_id: int) -> Optional[LoyaltyAccount]:
        """Get loyalty account for user."""
        return await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)

    async def suspend_account(self, user_id: int, until_date: Optional[datetime] = None) -> bool:
        """Suspend loyalty account."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            raise NotFoundError("Loyalty account not found")

        await self.loyalty_repo.update_loyalty_account(
            account.id,
            suspended_until=until_date
        )
        return True

    async def reactivate_account(self, user_id: int) -> bool:
        """Reactivate suspended loyalty account."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            raise NotFoundError("Loyalty account not found")

        await self.loyalty_repo.update_loyalty_account(
            account.id,
            suspended_until=None,
            is_active=True
        )
        return True

    # Point Earning
    async def award_booking_points(self, booking_id: int) -> Optional[PointTransaction]:
        """Award points for a completed booking."""
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking or booking.status != BookingStatus.COMPLETED:
            return None

        # Get loyalty account
        account = await self.get_or_create_loyalty_account(booking.user_id)
        if account.is_suspended:
            return None

        # Calculate points based on booking value
        base_points = int(booking.total_amount * self.POINTS_PER_DOLLAR)
        tier_multiplier = self.TIER_CONFIG[account.current_tier].point_multiplier
        total_points = int(base_points * tier_multiplier)

        # Award points
        transaction = await self._award_points(
            account.id,
            total_points,
            PointEarnReason.BOOKING_COMPLETED,
            booking_id=booking_id,
            monetary_value=booking.total_amount,
            description=f"Points for booking #{booking.id}"
        )

        # Check for tier upgrade
        await self._check_tier_upgrade(account.id)

        return transaction

    async def award_referral_points(self, referrer_user_id: int, referred_user_id: int) -> PointTransaction:
        """Award points for successful referral."""
        # Get referrer account
        account = await self.get_or_create_loyalty_account(referrer_user_id)
        if account.is_suspended:
            raise ValidationError("Account is suspended")

        # Get referral bonus amount
        bonus_points = self.TIER_CONFIG[account.current_tier].referral_bonus

        # Award points
        transaction = await self._award_points(
            account.id,
            bonus_points,
            PointEarnReason.REFERRAL,
            description=f"Referral bonus for user #{referred_user_id}"
        )

        # Update referral count
        await self.loyalty_repo.update_loyalty_account(
            account.id,
            referrals_count=account.referrals_count + 1
        )

        return transaction

    async def award_review_points(self, user_id: int, booking_id: int) -> PointTransaction:
        """Award points for submitting a review."""
        account = await self.get_or_create_loyalty_account(user_id)
        if account.is_suspended:
            raise ValidationError("Account is suspended")

        # Award review points
        transaction = await self._award_points(
            account.id,
            self.REVIEW_POINTS,
            PointEarnReason.REVIEW_SUBMITTED,
            booking_id=booking_id,
            description=f"Review bonus for booking #{booking_id}"
        )

        return transaction

    async def award_birthday_bonus(self, user_id: int) -> PointTransaction:
        """Award birthday bonus points."""
        account = await self.get_or_create_loyalty_account(user_id)
        if account.is_suspended:
            raise ValidationError("Account is suspended")

        # Get birthday bonus amount
        bonus_points = self.TIER_CONFIG[account.current_tier].birthday_bonus

        # Award points
        transaction = await self._award_points(
            account.id,
            bonus_points,
            PointEarnReason.BIRTHDAY_BONUS,
            description="Birthday bonus points"
        )

        return transaction

    async def award_custom_points(
        self,
        user_id: int,
        points: int,
        reason: str,
        processed_by_user_id: Optional[int] = None
    ) -> PointTransaction:
        """Award custom points (admin function)."""
        account = await self.get_or_create_loyalty_account(user_id)

        # Create adjustment transaction
        transaction = await self.loyalty_repo.create_point_transaction(
            loyalty_account_id=account.id,
            transaction_type=PointTransactionType.ADJUSTMENT,
            points_amount=points,
            balance_after=account.current_points + points,
            description=reason,
            processed_by_user_id=processed_by_user_id
        )

        # Update account balance
        await self._update_account_balance(account.id, points)

        return transaction

    # Point Redemption
    async def redeem_points_for_discount(
        self,
        user_id: int,
        points_to_redeem: int,
        booking_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Redeem points for booking discount."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            raise NotFoundError("Loyalty account not found")

        # Validate redemption
        if not account.can_redeem_points(points_to_redeem):
            raise ValidationError("Cannot redeem points: insufficient balance or account suspended")

        # Calculate discount amount (1 point = $0.01)
        discount_amount = Decimal(points_to_redeem) / 100

        # Create redemption transaction
        transaction = await self.loyalty_repo.create_point_transaction(
            loyalty_account_id=account.id,
            transaction_type=PointTransactionType.REDEEMED,
            points_amount=-points_to_redeem,
            balance_after=account.current_points - points_to_redeem,
            redemption_type=PointRedemptionType.DISCOUNT,
            discount_applied=discount_amount,
            booking_id=booking_id,
            description=f"Redeemed {points_to_redeem} points for ${discount_amount:.2f} discount"
        )

        # Update account balance
        await self._update_account_balance(account.id, -points_to_redeem)

        return {
            "transaction_id": transaction.id,
            "points_redeemed": points_to_redeem,
            "discount_amount": float(discount_amount),
            "remaining_balance": account.current_points - points_to_redeem
        }

    async def redeem_reward(self, user_id: int, reward_id: int) -> Dict[str, Any]:
        """Redeem points for a specific reward."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            raise NotFoundError("Loyalty account not found")

        reward = await self.loyalty_repo.get_loyalty_reward_by_id(reward_id)
        if not reward:
            raise NotFoundError("Reward not found")

        # Validate redemption
        if not reward.is_available:
            raise ValidationError("Reward is not available")

        if not reward.can_be_redeemed_by_tier(account.current_tier):
            raise ValidationError("Tier requirement not met for this reward")

        if not account.can_redeem_points(reward.point_cost):
            raise ValidationError("Insufficient points or account suspended")

        # Check redemption limits
        if reward.max_redemptions_per_user:
            user_redemptions = await self.loyalty_repo.get_user_redemption_count(user_id, reward_id)
            if user_redemptions >= reward.max_redemptions_per_user:
                raise ValidationError("Maximum redemptions exceeded for this reward")

        # Create redemption transaction
        transaction = await self.loyalty_repo.create_point_transaction(
            loyalty_account_id=account.id,
            transaction_type=PointTransactionType.REDEEMED,
            points_amount=-reward.point_cost,
            balance_after=account.current_points - reward.point_cost,
            redemption_type=reward.redemption_type,
            monetary_value=reward.monetary_value,
            description=f"Redeemed reward: {reward.name}",
            reference_id=str(reward_id)
        )

        # Update account balance
        await self._update_account_balance(account.id, -reward.point_cost)

        # Update reward redemption count
        await self.loyalty_repo.increment_reward_redemption_count(reward_id)

        return {
            "transaction_id": transaction.id,
            "reward_name": reward.name,
            "points_redeemed": reward.point_cost,
            "remaining_balance": account.current_points - reward.point_cost
        }

    # Point Expiration
    async def expire_user_points(self, user_id: int) -> int:
        """Expire points for a specific user."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            return 0

        expired_points = await self.loyalty_repo.expire_points(account.id)

        if expired_points > 0:
            # Update account balance
            await self._update_account_balance(account.id, -expired_points)

        return expired_points

    async def expire_all_points(self) -> Dict[str, int]:
        """Expire points for all users (batch operation)."""
        # This would typically be run as a scheduled task
        # Implementation would iterate through all accounts
        # For now, return placeholder
        return {"expired_accounts": 0, "total_expired_points": 0}

    # Tier Management
    async def calculate_tier_for_points(self, total_points: int) -> LoyaltyTier:
        """Calculate appropriate tier based on points."""
        for tier in reversed(list(self.TIER_CONFIG.keys())):
            if total_points >= self.TIER_CONFIG[tier].minimum_points:
                return tier
        return LoyaltyTier.BRONZE

    async def upgrade_user_tier(self, user_id: int, new_tier: LoyaltyTier) -> bool:
        """Manually upgrade user tier (admin function)."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            raise NotFoundError("Loyalty account not found")

        # Update tier
        next_tier_threshold = self.TIER_CONFIG[new_tier].next_tier_points

        await self.loyalty_repo.update_loyalty_account(
            account.id,
            current_tier=new_tier,
            next_tier_threshold=next_tier_threshold
        )

        return True

    # Analytics and Information
    async def get_user_loyalty_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive loyalty summary for user."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            return None

        # Get transaction summary
        points_summary = await self.loyalty_repo.get_points_summary(account.id)

        # Get expiring points
        expiring_points = await self.loyalty_repo.get_expiring_points(account.id, days_ahead=30)
        total_expiring = sum(t.points_amount for t in expiring_points)

        # Get tier benefits
        tier_benefits = self.TIER_CONFIG[account.current_tier]

        return {
            "account_id": account.id,
            "current_points": account.current_points,
            "lifetime_points": account.lifetime_points,
            "current_tier": account.current_tier.value,
            "tier_name": tier_benefits.name,
            "tier_points": account.tier_points,
            "points_to_next_tier": account.points_to_next_tier,
            "tier_progress_percentage": account.tier_progress_percentage,
            "points_expiring_soon": total_expiring,
            "total_bookings": account.total_bookings,
            "total_spent": float(account.total_spent),
            "referrals_count": account.referrals_count,
            "is_suspended": account.is_suspended,
            "points_summary": points_summary,
            "tier_benefits": {
                "point_multiplier": tier_benefits.point_multiplier,
                "birthday_bonus": tier_benefits.birthday_bonus,
                "referral_bonus": tier_benefits.referral_bonus
            }
        }

    async def get_available_rewards_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get rewards available for user based on their tier and points."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            return []

        rewards = await self.loyalty_repo.get_available_rewards(
            user_tier=account.current_tier,
            max_cost=account.current_points
        )

        result = []
        for reward in rewards:
            user_redemptions = await self.loyalty_repo.get_user_redemption_count(user_id, reward.id)
            can_redeem = (
                reward.is_available and
                reward.can_be_redeemed_by_tier(account.current_tier) and
                account.can_redeem_points(reward.point_cost) and
                (not reward.max_redemptions_per_user or user_redemptions < reward.max_redemptions_per_user)
            )

            result.append({
                "id": reward.id,
                "name": reward.name,
                "description": reward.description,
                "point_cost": reward.point_cost,
                "monetary_value": float(reward.monetary_value) if reward.monetary_value else None,
                "redemption_type": reward.redemption_type.value,
                "can_redeem": can_redeem,
                "user_redemptions": user_redemptions,
                "max_redemptions": reward.max_redemptions_per_user,
                "remaining_quantity": reward.remaining_quantity
            })

        return result

    async def get_transaction_history(
        self,
        user_id: int,
        transaction_type: Optional[PointTransactionType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's point transaction history."""
        account = await self.loyalty_repo.get_loyalty_account_by_user_id(user_id)
        if not account:
            return []

        transactions = await self.loyalty_repo.get_transaction_history(
            account.id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )

        return [
            {
                "id": t.id,
                "transaction_type": t.transaction_type.value,
                "points_amount": t.points_amount,
                "balance_after": t.balance_after,
                "description": t.description,
                "transaction_date": t.transaction_date.isoformat(),
                "earn_reason": t.earn_reason.value if t.earn_reason else None,
                "redemption_type": t.redemption_type.value if t.redemption_type else None,
                "monetary_value": float(t.monetary_value) if t.monetary_value else None,
                "discount_applied": float(t.discount_applied) if t.discount_applied else None,
                "expiry_date": t.expiry_date.isoformat() if t.expiry_date else None,
                "days_until_expiry": t.days_until_expiry
            }
            for t in transactions
        ]

    # Internal Helper Methods
    async def _award_points(
        self,
        loyalty_account_id: int,
        points: int,
        reason: PointEarnReason,
        booking_id: Optional[int] = None,
        monetary_value: Optional[Decimal] = None,
        description: Optional[str] = None
    ) -> PointTransaction:
        """Internal method to award points."""
        # Get current account
        account = await self.loyalty_repo.get_loyalty_account_by_id(loyalty_account_id)
        if not account:
            raise NotFoundError("Loyalty account not found")

        # Calculate expiry date
        expiry_date = datetime.now(timezone.utc) + timedelta(days=self.POINT_EXPIRY_MONTHS * 30)

        # Create transaction
        transaction = await self.loyalty_repo.create_point_transaction(
            loyalty_account_id=loyalty_account_id,
            transaction_type=PointTransactionType.EARNED,
            points_amount=points,
            balance_after=account.current_points + points,
            earn_reason=reason,
            booking_id=booking_id,
            monetary_value=monetary_value,
            description=description,
            expiry_date=expiry_date
        )

        # Update account balance
        await self._update_account_balance(loyalty_account_id, points)

        return transaction

    async def _update_account_balance(self, loyalty_account_id: int, points_change: int) -> None:
        """Update account point balance and related fields."""
        account = await self.loyalty_repo.get_loyalty_account_by_id(loyalty_account_id)
        if not account:
            return

        new_balance = account.current_points + points_change
        new_lifetime = account.lifetime_points + (points_change if points_change > 0 else 0)
        new_tier_points = account.tier_points + (points_change if points_change > 0 else 0)

        await self.loyalty_repo.update_loyalty_account(
            loyalty_account_id,
            current_points=new_balance,
            lifetime_points=new_lifetime,
            tier_points=new_tier_points,
            last_activity_date=datetime.now(timezone.utc)
        )

    async def _check_tier_upgrade(self, loyalty_account_id: int) -> bool:
        """Check if user qualifies for tier upgrade."""
        account = await self.loyalty_repo.get_loyalty_account_by_id(loyalty_account_id)
        if not account:
            return False

        new_tier = await self.calculate_tier_for_points(account.tier_points)

        if new_tier != account.current_tier:
            # Upgrade tier
            tier_config = self.TIER_CONFIG[new_tier]

            await self.loyalty_repo.update_loyalty_account(
                loyalty_account_id,
                current_tier=new_tier,
                next_tier_threshold=tier_config.next_tier_points
            )

            # Award milestone bonus
            milestone_bonus = 100 * (list(self.TIER_CONFIG.keys()).index(new_tier) + 1)
            await self._award_points(
                loyalty_account_id,
                milestone_bonus,
                PointEarnReason.LOYALTY_MILESTONE,
                description=f"Tier upgrade bonus to {tier_config.name}"
            )

            return True

        return False
