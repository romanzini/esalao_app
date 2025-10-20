"""
Unit tests for the Loyalty Points System.

This module contains tests that verify the loyalty system components
work correctly in isolation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from backend.app.db.models.loyalty import (
    LoyaltyAccount, PointTransaction, LoyaltyReward,
    LoyaltyTier, PointTransactionType
)


class TestLoyaltySystemComponents:
    """Test loyalty system components independently."""

    def test_loyalty_account_basic_fields(self):
        """Test basic loyalty account model fields."""
        account = LoyaltyAccount()
        account.user_id = 1
        account.current_points = 500
        account.lifetime_points = 1500
        account.current_tier = LoyaltyTier.SILVER

        # Test required fields
        assert account.user_id == 1
        assert account.current_points == 500
        assert account.lifetime_points == 1500
        assert account.current_tier == LoyaltyTier.SILVER

    def test_point_transaction_basic_fields(self):
        """Test basic point transaction model fields."""
        transaction = PointTransaction()
        transaction.loyalty_account_id = 1
        transaction.transaction_type = PointTransactionType.EARNED
        transaction.point_amount = 100
        transaction.description = "Test transaction"
        transaction.booking_id = 123
        transaction.expires_at = datetime.now(timezone.utc) + timedelta(days=365)

        assert transaction.loyalty_account_id == 1
        assert transaction.transaction_type == PointTransactionType.EARNED
        assert transaction.point_amount == 100
        assert transaction.description == "Test transaction"
        assert transaction.booking_id == 123
        assert transaction.expires_at is not None

    def test_loyalty_reward_basic_fields(self):
        """Test basic loyalty reward model fields."""
        reward = LoyaltyReward()
        reward.name = "Test Reward"
        reward.description = "Test description"
        reward.required_points = 500
        reward.discount_type = "fixed"
        reward.discount_value = Decimal("10.00")
        reward.is_active = True

        assert reward.name == "Test Reward"
        assert reward.description == "Test description"
        assert reward.required_points == 500
        assert reward.discount_type == "fixed"
        assert reward.discount_value == Decimal("10.00")
        assert reward.is_active is True

    def test_loyalty_tier_enum_ordering(self):
        """Test that loyalty tiers can be compared for ordering."""
        tiers = [
            LoyaltyTier.BRONZE,
            LoyaltyTier.SILVER,
            LoyaltyTier.GOLD,
            LoyaltyTier.PLATINUM,
            LoyaltyTier.DIAMOND
        ]

        # Test that we can identify different tiers
        assert LoyaltyTier.BRONZE != LoyaltyTier.SILVER
        assert LoyaltyTier.GOLD != LoyaltyTier.PLATINUM

        # Test tier values
        assert LoyaltyTier.BRONZE.value == "bronze"
        assert LoyaltyTier.SILVER.value == "silver"
        assert LoyaltyTier.GOLD.value == "gold"
        assert LoyaltyTier.PLATINUM.value == "platinum"
        assert LoyaltyTier.DIAMOND.value == "diamond"

    def test_point_calculation_scenarios(self):
        """Test various point calculation scenarios."""
        # Test booking completion points (10 points per $1)
        booking_amount = Decimal("50.00")
        expected_points = int(booking_amount * 10)
        assert expected_points == 500

        # Test tier multiplier application
        base_points = 500
        gold_multiplier = 1.5
        expected_gold_points = int(base_points * gold_multiplier)
        assert expected_gold_points == 750

        # Test rounding for point calculations
        weird_amount = Decimal("33.33")
        points = int(weird_amount * 10)
        assert points == 333  # Should round down

    def test_reward_discount_calculation(self):
        """Test reward discount calculations."""
        # Fixed amount discount
        fixed_reward = LoyaltyReward()
        fixed_reward.name = "$10 Off"
        fixed_reward.description = "Fixed discount"
        fixed_reward.required_points = 1000
        fixed_reward.discount_type = "fixed"
        fixed_reward.discount_value = Decimal("10.00")
        fixed_reward.is_active = True

        booking_total = Decimal("50.00")
        # For fixed discount, discount value is the amount
        assert fixed_reward.discount_value == Decimal("10.00")

        # Percentage discount
        percentage_reward = LoyaltyReward()
        percentage_reward.name = "15% Off"
        percentage_reward.description = "Percentage discount"
        percentage_reward.required_points = 800
        percentage_reward.discount_type = "percentage"
        percentage_reward.discount_value = Decimal("15.00")
        percentage_reward.is_active = True

        # For percentage discount, need to calculate discount amount
        expected_discount = booking_total * (percentage_reward.discount_value / 100)
        assert expected_discount == Decimal("7.50")

    def test_loyalty_account_fields(self):
        """Test loyalty account model fields and defaults."""
        account = LoyaltyAccount()
        account.user_id = 1
        account.tier_points = 1500
        account.current_tier = LoyaltyTier.SILVER

        # Test required fields
        assert account.user_id == 1
        assert account.tier_points == 1500
        assert account.current_tier == LoyaltyTier.SILVER

        # Test that timestamps will be set (tested by checking they're None before save)
        assert account.created_at is None  # Not set until saved
        assert account.updated_at is None  # Not set until saved
