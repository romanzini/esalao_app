"""Test suite for loyalty system."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.app.db.models.loyalty import (
    LoyaltyAccount, PointTransaction, LoyaltyReward,
    PointTransactionType, LoyaltyTier, PointEarnReason, PointRedemptionType
)


class TestLoyaltyEnums:
    """Test loyalty system enums."""

    def test_point_transaction_type_enum(self):
        """Test PointTransactionType enum values."""
        assert PointTransactionType.EARNED == "earned"
        assert PointTransactionType.REDEEMED == "redeemed"
        assert PointTransactionType.EXPIRED == "expired"
        assert PointTransactionType.BONUS == "bonus"
        assert PointTransactionType.ADJUSTMENT == "adjustment"
        assert PointTransactionType.REFUND == "refund"

    def test_loyalty_tier_enum(self):
        """Test LoyaltyTier enum values."""
        assert LoyaltyTier.BRONZE == "bronze"
        assert LoyaltyTier.SILVER == "silver"
        assert LoyaltyTier.GOLD == "gold"
        assert LoyaltyTier.PLATINUM == "platinum"
        assert LoyaltyTier.DIAMOND == "diamond"

    def test_point_earn_reason_enum(self):
        """Test PointEarnReason enum values."""
        assert PointEarnReason.BOOKING_COMPLETED == "booking_completed"
        assert PointEarnReason.REFERRAL == "referral"
        assert PointEarnReason.REVIEW_SUBMITTED == "review_submitted"
        assert PointEarnReason.BIRTHDAY_BONUS == "birthday_bonus"
        assert PointEarnReason.PROMOTION == "promotion"
        assert PointEarnReason.SIGNUP_BONUS == "signup_bonus"
        assert PointEarnReason.LOYALTY_MILESTONE == "loyalty_milestone"

    def test_point_redemption_type_enum(self):
        """Test PointRedemptionType enum values."""
        assert PointRedemptionType.DISCOUNT == "discount"
        assert PointRedemptionType.FREE_SERVICE == "free_service"
        assert PointRedemptionType.UPGRADE == "upgrade"
        assert PointRedemptionType.GIFT_CARD == "gift_card"
        assert PointRedemptionType.MERCHANDISE == "merchandise"


class TestLoyaltyAccountModel:
    """Test LoyaltyAccount model functionality."""

    def test_loyalty_account_creation(self):
        """Test basic loyalty account creation."""
        account = LoyaltyAccount(
            id=1,
            user_id=123,
            current_points=1000,
            lifetime_points=5000,
            current_tier=LoyaltyTier.SILVER,
            tier_points=1500,
            next_tier_threshold=3000,
            is_active=True
        )

        assert account.id == 1
        assert account.user_id == 123
        assert account.current_points == 1000
        assert account.lifetime_points == 5000
        assert account.current_tier == LoyaltyTier.SILVER
        assert account.tier_points == 1500
        assert account.next_tier_threshold == 3000
        assert account.is_active is True

    def test_points_to_next_tier_calculation(self):
        """Test points_to_next_tier property."""
        account = LoyaltyAccount(
            user_id=123,
            tier_points=1500,
            next_tier_threshold=3000
        )

        assert account.points_to_next_tier == 1500  # 3000 - 1500

        # Test when at threshold
        account.tier_points = 3000
        assert account.points_to_next_tier == 0

        # Test when over threshold
        account.tier_points = 3500
        assert account.points_to_next_tier == 0

        # Test when no next tier
        account.next_tier_threshold = None
        assert account.points_to_next_tier is None

    def test_tier_progress_percentage(self):
        """Test tier_progress_percentage property."""
        account = LoyaltyAccount(
            user_id=123,
            tier_points=1500,
            next_tier_threshold=3000
        )

        assert account.tier_progress_percentage == 50.0  # 1500/3000 * 100

        # Test when at threshold
        account.tier_points = 3000
        assert account.tier_progress_percentage == 100.0

        # Test when over threshold
        account.tier_points = 4000
        assert account.tier_progress_percentage == 100.0

        # Test when no next tier
        account.next_tier_threshold = None
        assert account.tier_progress_percentage == 100.0

    def test_is_suspended_property(self):
        """Test is_suspended property."""
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        past_date = datetime.now(timezone.utc) - timedelta(days=7)

        account = LoyaltyAccount(user_id=123)

        # No suspension
        assert account.is_suspended is False

        # Future suspension date
        account.suspended_until = future_date
        assert account.is_suspended is True

        # Past suspension date (expired)
        account.suspended_until = past_date
        assert account.is_suspended is False

    def test_can_redeem_points(self):
        """Test can_redeem_points method."""
        account = LoyaltyAccount(
            user_id=123,
            current_points=1000,
            is_active=True
        )

        # Valid redemption
        assert account.can_redeem_points(500) is True
        assert account.can_redeem_points(1000) is True

        # Invalid redemptions
        assert account.can_redeem_points(1500) is False  # Insufficient points
        assert account.can_redeem_points(0) is False     # Zero points
        assert account.can_redeem_points(-100) is False  # Negative points

        # Inactive account
        account.is_active = False
        assert account.can_redeem_points(500) is False

        # Suspended account
        account.is_active = True
        account.suspended_until = datetime.now(timezone.utc) + timedelta(days=7)
        assert account.can_redeem_points(500) is False


class TestPointTransactionModel:
    """Test PointTransaction model functionality."""

    def test_point_transaction_creation(self):
        """Test basic point transaction creation."""
        transaction = PointTransaction(
            id=1,
            loyalty_account_id=123,
            transaction_type=PointTransactionType.EARNED,
            points_amount=500,
            balance_after=1500,
            earn_reason=PointEarnReason.BOOKING_COMPLETED,
            description="Points for booking #456"
        )

        assert transaction.id == 1
        assert transaction.loyalty_account_id == 123
        assert transaction.transaction_type == PointTransactionType.EARNED
        assert transaction.points_amount == 500
        assert transaction.balance_after == 1500
        assert transaction.earn_reason == PointEarnReason.BOOKING_COMPLETED
        assert transaction.description == "Points for booking #456"

    def test_is_earning_transaction_property(self):
        """Test is_earning_transaction property."""
        # Earning transactions
        transaction = PointTransaction(
            loyalty_account_id=123,
            transaction_type=PointTransactionType.EARNED,
            points_amount=500,
            balance_after=1500
        )
        assert transaction.is_earning_transaction is True

        transaction.transaction_type = PointTransactionType.BONUS
        assert transaction.is_earning_transaction is True

        transaction.transaction_type = PointTransactionType.REFUND
        assert transaction.is_earning_transaction is True

        # Non-earning transactions
        transaction.transaction_type = PointTransactionType.REDEEMED
        assert transaction.is_earning_transaction is False

        transaction.transaction_type = PointTransactionType.EXPIRED
        assert transaction.is_earning_transaction is False

    def test_is_spending_transaction_property(self):
        """Test is_spending_transaction property."""
        # Spending transactions
        transaction = PointTransaction(
            loyalty_account_id=123,
            transaction_type=PointTransactionType.REDEEMED,
            points_amount=-500,
            balance_after=500
        )
        assert transaction.is_spending_transaction is True

        transaction.transaction_type = PointTransactionType.EXPIRED
        assert transaction.is_spending_transaction is True

        transaction.transaction_type = PointTransactionType.ADJUSTMENT
        assert transaction.is_spending_transaction is True

        # Non-spending transactions
        transaction.transaction_type = PointTransactionType.EARNED
        assert transaction.is_spending_transaction is False

    def test_days_until_expiry_property(self):
        """Test days_until_expiry property."""
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        past_date = datetime.now(timezone.utc) - timedelta(days=30)

        transaction = PointTransaction(
            loyalty_account_id=123,
            transaction_type=PointTransactionType.EARNED,
            points_amount=500,
            balance_after=1500
        )

        # No expiry date
        assert transaction.days_until_expiry is None

        # Future expiry
        transaction.expiry_date = future_date
        assert transaction.days_until_expiry == 30

        # Past expiry (expired)
        transaction.expiry_date = past_date
        assert transaction.days_until_expiry == 0

        # Already marked as expired
        transaction.is_expired = True
        assert transaction.days_until_expiry is None


class TestLoyaltyRewardModel:
    """Test LoyaltyReward model functionality."""

    def test_loyalty_reward_creation(self):
        """Test basic loyalty reward creation."""
        reward = LoyaltyReward(
            id=1,
            name="Free Haircut",
            description="Complimentary haircut service",
            redemption_type=PointRedemptionType.FREE_SERVICE,
            point_cost=2000,
            monetary_value=Decimal("50.00"),
            is_active=True,
            minimum_tier=LoyaltyTier.SILVER
        )

        assert reward.id == 1
        assert reward.name == "Free Haircut"
        assert reward.description == "Complimentary haircut service"
        assert reward.redemption_type == PointRedemptionType.FREE_SERVICE
        assert reward.point_cost == 2000
        assert reward.monetary_value == Decimal("50.00")
        assert reward.is_active is True
        assert reward.minimum_tier == LoyaltyTier.SILVER

    def test_is_available_property(self):
        """Test is_available property."""
        now = datetime.now(timezone.utc)
        future_date = now + timedelta(days=30)
        past_date = now - timedelta(days=30)

        reward = LoyaltyReward(
            name="Test Reward",
            redemption_type=PointRedemptionType.DISCOUNT,
            point_cost=1000,
            is_active=True
        )

        # Active reward with no restrictions
        assert reward.is_available is True

        # Inactive reward
        reward.is_active = False
        assert reward.is_available is False
        reward.is_active = True

        # Not yet available
        reward.available_from = future_date
        assert reward.is_available is False
        reward.available_from = None

        # Expired
        reward.available_until = past_date
        assert reward.is_available is False
        reward.available_until = None

        # Sold out
        reward.total_available = 10
        reward.total_redeemed = 10
        assert reward.is_available is False

    def test_remaining_quantity_property(self):
        """Test remaining_quantity property."""
        reward = LoyaltyReward(
            name="Test Reward",
            redemption_type=PointRedemptionType.DISCOUNT,
            point_cost=1000,
            total_available=100,
            total_redeemed=25
        )

        assert reward.remaining_quantity == 75

        # No limit
        reward.total_available = None
        assert reward.remaining_quantity is None

        # Sold out
        reward.total_available = 100
        reward.total_redeemed = 100
        assert reward.remaining_quantity == 0

    def test_can_be_redeemed_by_tier(self):
        """Test can_be_redeemed_by_tier method."""
        reward = LoyaltyReward(
            name="Test Reward",
            redemption_type=PointRedemptionType.DISCOUNT,
            point_cost=1000,
            minimum_tier=LoyaltyTier.SILVER
        )

        # Below minimum tier
        assert reward.can_be_redeemed_by_tier(LoyaltyTier.BRONZE) is False

        # At minimum tier
        assert reward.can_be_redeemed_by_tier(LoyaltyTier.SILVER) is True

        # Above minimum tier
        assert reward.can_be_redeemed_by_tier(LoyaltyTier.GOLD) is True
        assert reward.can_be_redeemed_by_tier(LoyaltyTier.PLATINUM) is True
        assert reward.can_be_redeemed_by_tier(LoyaltyTier.DIAMOND) is True

        # No tier requirement
        reward.minimum_tier = None
        assert reward.can_be_redeemed_by_tier(LoyaltyTier.BRONZE) is True


if __name__ == "__main__":
    pytest.main([__file__])
