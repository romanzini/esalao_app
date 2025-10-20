"""Tests for cancellation policy domain logic."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from backend.app.domain.policies.cancellation import (
    CancellationPolicy,
    CancellationTier,
    CancellationContext,
    CancellationResult,
    CancellationEvaluation,
    CancellationPolicyService,
)


class TestCancellationTier:
    """Test cancellation tier domain logic."""

    def test_calculate_percentage_fee(self):
        """Test percentage fee calculation."""
        tier = CancellationTier(
            id=1,
            name="Standard",
            advance_notice_hours=24,
            fee_type="percentage",
            fee_value=Decimal("20"),
            allows_refund=True,
            display_order=1,
        )

        service_price = Decimal("100.00")
        fee = tier.calculate_fee(service_price)

        assert fee == Decimal("20.00")

    def test_calculate_fixed_fee(self):
        """Test fixed fee calculation."""
        tier = CancellationTier(
            id=1,
            name="Last Minute",
            advance_notice_hours=2,
            fee_type="fixed",
            fee_value=Decimal("25.00"),
            allows_refund=True,
            display_order=2,
        )

        service_price = Decimal("150.00")
        fee = tier.calculate_fee(service_price)

        assert fee == Decimal("25.00")

    def test_applies_to_advance_notice(self):
        """Test advance notice application logic."""
        tier = CancellationTier(
            id=1,
            name="Standard",
            advance_notice_hours=24,
            fee_type="percentage",
            fee_value=Decimal("10"),
            allows_refund=True,
            display_order=1,
        )

        # Should apply for 24+ hours
        assert tier.applies_to_advance_notice(24.0) is True
        assert tier.applies_to_advance_notice(25.0) is True
        assert tier.applies_to_advance_notice(48.0) is True

        # Should not apply for < 24 hours
        assert tier.applies_to_advance_notice(23.0) is False
        assert tier.applies_to_advance_notice(12.0) is False
        assert tier.applies_to_advance_notice(1.0) is False

    def test_invalid_fee_type_raises_error(self):
        """Test invalid fee type raises ValueError."""
        tier = CancellationTier(
            id=1,
            name="Invalid",
            advance_notice_hours=24,
            fee_type="invalid",
            fee_value=Decimal("10"),
            allows_refund=True,
            display_order=1,
        )

        with pytest.raises(ValueError, match="Invalid fee type"):
            tier.calculate_fee(Decimal("100.00"))


class TestCancellationContext:
    """Test cancellation context logic."""

    def test_advance_notice_hours_calculation(self):
        """Test advance notice hours calculation."""
        scheduled_time = datetime(2025, 1, 15, 14, 0, 0)
        cancellation_time = datetime(2025, 1, 14, 14, 0, 0)

        context = CancellationContext(
            booking_id=1,
            scheduled_time=scheduled_time,
            cancellation_time=cancellation_time,
            service_price=Decimal("100.00"),
            client_id=1,
            professional_id=1,
        )

        assert context.advance_notice_hours == 24.0

    def test_advance_notice_timedelta(self):
        """Test advance notice timedelta calculation."""
        scheduled_time = datetime(2025, 1, 15, 14, 0, 0)
        cancellation_time = datetime(2025, 1, 14, 14, 0, 0)

        context = CancellationContext(
            booking_id=1,
            scheduled_time=scheduled_time,
            cancellation_time=cancellation_time,
            service_price=Decimal("100.00"),
            client_id=1,
            professional_id=1,
        )

        expected_delta = timedelta(hours=24)
        assert context.advance_notice_timedelta == expected_delta


class TestCancellationPolicy:
    """Test cancellation policy domain logic."""

    def create_sample_policy(self) -> CancellationPolicy:
        """Create a sample policy for testing."""
        tiers = [
            CancellationTier(
                id=1,
                name="Early Bird",
                advance_notice_hours=72,
                fee_type="percentage",
                fee_value=Decimal("0"),
                allows_refund=True,
                display_order=1,
            ),
            CancellationTier(
                id=2,
                name="Standard",
                advance_notice_hours=24,
                fee_type="percentage",
                fee_value=Decimal("20"),
                allows_refund=True,
                display_order=2,
            ),
            CancellationTier(
                id=3,
                name="Last Minute",
                advance_notice_hours=2,
                fee_type="fixed",
                fee_value=Decimal("50"),
                allows_refund=True,
                display_order=3,
            ),
        ]

        return CancellationPolicy(
            id=1,
            name="Standard Policy",
            description="Standard cancellation policy",
            salon_id=None,
            is_default=True,
            effective_from=datetime(2025, 1, 1),
            effective_until=None,
            tiers=tiers,
        )

    def test_is_effective_at(self):
        """Test policy effectiveness check."""
        policy = self.create_sample_policy()

        # Should be effective after start date
        assert policy.is_effective_at(datetime(2025, 1, 2)) is True
        assert policy.is_effective_at(datetime(2025, 6, 15)) is True

        # Should not be effective before start date
        assert policy.is_effective_at(datetime(2024, 12, 31)) is False

    def test_is_effective_at_with_end_date(self):
        """Test policy effectiveness with end date."""
        policy = self.create_sample_policy()
        policy.effective_until = datetime(2025, 12, 31)

        # Should be effective within range
        assert policy.is_effective_at(datetime(2025, 6, 15)) is True

        # Should not be effective after end date
        assert policy.is_effective_at(datetime(2026, 1, 1)) is False

    def test_find_applicable_tier_early_bird(self):
        """Test finding early bird tier."""
        policy = self.create_sample_policy()

        tier = policy.find_applicable_tier(72.0)
        assert tier is not None
        assert tier.name == "Early Bird"
        assert tier.fee_value == Decimal("0")

    def test_find_applicable_tier_standard(self):
        """Test finding standard tier."""
        policy = self.create_sample_policy()

        tier = policy.find_applicable_tier(24.0)
        assert tier is not None
        assert tier.name == "Standard"
        assert tier.fee_value == Decimal("20")

    def test_find_applicable_tier_last_minute(self):
        """Test finding last minute tier."""
        policy = self.create_sample_policy()

        tier = policy.find_applicable_tier(2.0)
        assert tier is not None
        assert tier.name == "Last Minute"
        assert tier.fee_value == Decimal("50")

    def test_find_applicable_tier_no_match(self):
        """Test when no tier matches."""
        policy = self.create_sample_policy()

        tier = policy.find_applicable_tier(1.0)  # Less than minimum 2 hours
        assert tier is None

    def test_evaluate_cancellation_early_bird_no_fee(self):
        """Test early bird cancellation with no fee."""
        policy = self.create_sample_policy()

        context = CancellationContext(
            booking_id=1,
            scheduled_time=datetime(2025, 1, 15, 14, 0, 0),
            cancellation_time=datetime(2025, 1, 12, 14, 0, 0),  # 72 hours
            service_price=Decimal("100.00"),
            client_id=1,
            professional_id=1,
        )

        evaluation = policy.evaluate_cancellation(context)

        assert evaluation.result == CancellationResult.ALLOWED_NO_FEE
        assert evaluation.fee_amount == Decimal("0")
        assert evaluation.refund_amount == Decimal("100.00")
        assert evaluation.applicable_tier.name == "Early Bird"

    def test_evaluate_cancellation_standard_with_fee(self):
        """Test standard cancellation with percentage fee."""
        policy = self.create_sample_policy()

        context = CancellationContext(
            booking_id=1,
            scheduled_time=datetime(2025, 1, 15, 14, 0, 0),
            cancellation_time=datetime(2025, 1, 14, 14, 0, 0),  # 24 hours
            service_price=Decimal("100.00"),
            client_id=1,
            professional_id=1,
        )

        evaluation = policy.evaluate_cancellation(context)

        assert evaluation.result == CancellationResult.ALLOWED_WITH_FEE
        assert evaluation.fee_amount == Decimal("20.00")
        assert evaluation.refund_amount == Decimal("80.00")
        assert evaluation.applicable_tier.name == "Standard"

    def test_evaluate_cancellation_last_minute_fixed_fee(self):
        """Test last minute cancellation with fixed fee."""
        policy = self.create_sample_policy()

        context = CancellationContext(
            booking_id=1,
            scheduled_time=datetime(2025, 1, 15, 14, 0, 0),
            cancellation_time=datetime(2025, 1, 15, 12, 0, 0),  # 2 hours
            service_price=Decimal("150.00"),
            client_id=1,
            professional_id=1,
        )

        evaluation = policy.evaluate_cancellation(context)

        assert evaluation.result == CancellationResult.ALLOWED_WITH_FEE
        assert evaluation.fee_amount == Decimal("50.00")
        assert evaluation.refund_amount == Decimal("100.00")
        assert evaluation.applicable_tier.name == "Last Minute"

    def test_evaluate_cancellation_not_allowed_insufficient_notice(self):
        """Test cancellation not allowed due to insufficient notice."""
        policy = self.create_sample_policy()

        context = CancellationContext(
            booking_id=1,
            scheduled_time=datetime(2025, 1, 15, 14, 0, 0),
            cancellation_time=datetime(2025, 1, 15, 13, 0, 0),  # 1 hour
            service_price=Decimal("100.00"),
            client_id=1,
            professional_id=1,
        )

        evaluation = policy.evaluate_cancellation(context)

        assert evaluation.result == CancellationResult.NOT_ALLOWED
        assert evaluation.fee_amount == Decimal("0")
        assert evaluation.refund_amount == Decimal("0")
        assert evaluation.applicable_tier is None
        assert "Insufficient advance notice" in evaluation.message

    def test_evaluate_cancellation_policy_not_effective(self):
        """Test cancellation when policy is not effective."""
        policy = self.create_sample_policy()

        # Try to cancel before policy is effective
        context = CancellationContext(
            booking_id=1,
            scheduled_time=datetime(2024, 12, 15, 14, 0, 0),
            cancellation_time=datetime(2024, 12, 10, 14, 0, 0),
            service_price=Decimal("100.00"),
            client_id=1,
            professional_id=1,
        )

        evaluation = policy.evaluate_cancellation(context)

        assert evaluation.result == CancellationResult.NOT_ALLOWED
        assert "Policy not effective" in evaluation.message

    def test_evaluate_cancellation_refund_not_allowed(self):
        """Test cancellation when tier doesn't allow refund."""
        policy = self.create_sample_policy()
        # Modify last minute tier to not allow refunds
        policy.tiers[2].allows_refund = False

        context = CancellationContext(
            booking_id=1,
            scheduled_time=datetime(2025, 1, 15, 14, 0, 0),
            cancellation_time=datetime(2025, 1, 15, 12, 0, 0),  # 2 hours
            service_price=Decimal("100.00"),
            client_id=1,
            professional_id=1,
        )

        evaluation = policy.evaluate_cancellation(context)

        assert evaluation.result == CancellationResult.NOT_ALLOWED
        assert evaluation.applicable_tier.name == "Last Minute"
        assert "Refund not allowed" in evaluation.message


class TestCancellationEvaluation:
    """Test cancellation evaluation result."""

    def test_is_allowed_property(self):
        """Test is_allowed property."""
        # Allowed cases
        eval_no_fee = CancellationEvaluation(
            result=CancellationResult.ALLOWED_NO_FEE,
            applicable_tier=None,
            fee_amount=Decimal("0"),
            refund_amount=Decimal("100"),
            message="Test",
            policy_used=None,
        )
        assert eval_no_fee.is_allowed is True

        eval_with_fee = CancellationEvaluation(
            result=CancellationResult.ALLOWED_WITH_FEE,
            applicable_tier=None,
            fee_amount=Decimal("20"),
            refund_amount=Decimal("80"),
            message="Test",
            policy_used=None,
        )
        assert eval_with_fee.is_allowed is True

        # Not allowed case
        eval_not_allowed = CancellationEvaluation(
            result=CancellationResult.NOT_ALLOWED,
            applicable_tier=None,
            fee_amount=Decimal("0"),
            refund_amount=Decimal("0"),
            message="Test",
            policy_used=None,
        )
        assert eval_not_allowed.is_allowed is False

    def test_has_fee_property(self):
        """Test has_fee property."""
        eval_no_fee = CancellationEvaluation(
            result=CancellationResult.ALLOWED_NO_FEE,
            applicable_tier=None,
            fee_amount=Decimal("0"),
            refund_amount=Decimal("100"),
            message="Test",
            policy_used=None,
        )
        assert eval_no_fee.has_fee is False

        eval_with_fee = CancellationEvaluation(
            result=CancellationResult.ALLOWED_WITH_FEE,
            applicable_tier=None,
            fee_amount=Decimal("20"),
            refund_amount=Decimal("80"),
            message="Test",
            policy_used=None,
        )
        assert eval_with_fee.has_fee is True
