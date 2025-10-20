"""
Tests for BookingCancellationService
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from backend.app.domain.policies.booking_cancellation import BookingCancellationService
from backend.app.domain.policies.cancellation import CancellationPolicy, CancellationTier


class MockBooking:
    """Mock booking object for testing"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.client_id = kwargs.get('client_id', 1)
        self.professional_id = kwargs.get('professional_id', 1)
        self.service_id = kwargs.get('service_id', 1)
        self.scheduled_at = kwargs.get('scheduled_at', datetime.now(timezone.utc) + timedelta(hours=48))
        self.service_price = kwargs.get('service_price', 100.0)
        self.deposit_amount = kwargs.get('deposit_amount', None)
        self.status = kwargs.get('status', 'pending')
        self.cancellation_policy_id = kwargs.get('cancellation_policy_id', None)
        self.cancelled_at = kwargs.get('cancelled_at', None)
        self.cancellation_reason = kwargs.get('cancellation_reason', None)
        self.cancelled_by_id = kwargs.get('cancelled_by_id', None)
        self.cancellation_fee_amount = kwargs.get('cancellation_fee_amount', None)


class MockCancellationPolicy:
    """Mock cancellation policy for testing"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.name = kwargs.get('name', 'Test Policy')
        self.is_default = kwargs.get('is_default', True)
        self.status = kwargs.get('status', 'ACTIVE')

    def evaluate_cancellation(self, context):
        """Mock evaluation returning standard tier"""
        from backend.app.domain.policies.cancellation import CancellationEvaluation, CancellationResult

        tier = CancellationTier(
            id=1,
            name="Standard (24-72h)",
            advance_notice_hours=24,
            fee_type="percentage",
            fee_value=Decimal('15'),
            allows_refund=True,
            display_order=1
        )

        return CancellationEvaluation(
            result=CancellationResult.ALLOWED_WITH_FEE,
            applicable_tier=tier,
            fee_amount=context.service_price * Decimal('0.15'),
            refund_amount=context.service_price * Decimal('0.85'),
            message="Standard cancellation fee applied",
            policy_used=self,
        )


@pytest.fixture
def mock_booking_repo():
    """Mock booking repository"""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_policy_repo():
    """Mock policy repository"""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_platform_default = AsyncMock()
    repo.get_default_for_salon = AsyncMock()
    return repo


@pytest.fixture
def cancellation_service(mock_booking_repo, mock_policy_repo):
    """BookingCancellationService instance with mocked dependencies"""
    return BookingCancellationService(mock_booking_repo, mock_policy_repo)


class TestBookingCancellationService:
    """Test cases for BookingCancellationService"""

    @pytest.mark.asyncio
    async def test_calculate_cancellation_fee_success(self, cancellation_service, mock_booking_repo, mock_policy_repo):
        """Test successful fee calculation"""
        # Setup
        booking = MockBooking(
            id=1,
            service_price=100.0,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=48)
        )
        policy = MockCancellationPolicy()

        mock_booking_repo.get_by_id.return_value = booking
        mock_policy_repo.get_platform_default.return_value = policy

        # Execute
        result = await cancellation_service.calculate_cancellation_fee(1)

        # Verify
        assert result['fee_amount'] == Decimal('15.0')  # 15% of 100
        assert result['tier_name'] == "Standard (24-72h)"
        assert result['allows_refund'] is True
        assert result['policy_name'] == "Test Policy"
        assert result['refund_amount'] == Decimal('85.0')

    @pytest.mark.asyncio
    async def test_calculate_fee_booking_not_found(self, cancellation_service, mock_booking_repo):
        """Test fee calculation when booking not found"""
        mock_booking_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Booking 999 not found"):
            await cancellation_service.calculate_cancellation_fee(999)

    @pytest.mark.asyncio
    async def test_calculate_fee_already_cancelled(self, cancellation_service, mock_booking_repo):
        """Test fee calculation for already cancelled booking"""
        booking = MockBooking(status='cancelled')
        mock_booking_repo.get_by_id.return_value = booking

        with pytest.raises(ValueError, match="Booking 1 already cancelled"):
            await cancellation_service.calculate_cancellation_fee(1)

    @pytest.mark.asyncio
    async def test_can_cancel_booking_success(self, cancellation_service, mock_booking_repo, mock_policy_repo):
        """Test successful cancellation check"""
        booking = MockBooking(
            status='confirmed',
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=48)
        )
        policy = MockCancellationPolicy()

        mock_booking_repo.get_by_id.return_value = booking
        mock_policy_repo.get_platform_default.return_value = policy

        result = await cancellation_service.can_cancel_booking(1)

        assert result['can_cancel'] is True
        assert result['reason'] == 'Cancellation allowed'
        assert 'fee_info' in result

    @pytest.mark.asyncio
    async def test_can_cancel_booking_not_found(self, cancellation_service, mock_booking_repo):
        """Test cancellation check when booking not found"""
        mock_booking_repo.get_by_id.return_value = None

        result = await cancellation_service.can_cancel_booking(999)

        assert result['can_cancel'] is False
        assert result['reason'] == 'Booking not found'

    @pytest.mark.asyncio
    async def test_can_cancel_already_cancelled(self, cancellation_service, mock_booking_repo):
        """Test cancellation check for already cancelled booking"""
        booking = MockBooking(status='cancelled')
        mock_booking_repo.get_by_id.return_value = booking

        result = await cancellation_service.can_cancel_booking(1)

        assert result['can_cancel'] is False
        assert result['reason'] == 'Booking already cancelled'

    @pytest.mark.asyncio
    async def test_can_cancel_completed_booking(self, cancellation_service, mock_booking_repo):
        """Test cancellation check for completed booking"""
        booking = MockBooking(status='completed')
        mock_booking_repo.get_by_id.return_value = booking

        result = await cancellation_service.can_cancel_booking(1)

        assert result['can_cancel'] is False
        assert result['reason'] == 'Cannot cancel completed booking'

    @pytest.mark.asyncio
    async def test_can_cancel_past_booking(self, cancellation_service, mock_booking_repo):
        """Test cancellation check for past booking"""
        booking = MockBooking(
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1)  # 1 hour ago
        )
        mock_booking_repo.get_by_id.return_value = booking

        result = await cancellation_service.can_cancel_booking(1)

        assert result['can_cancel'] is False
        assert result['reason'] == 'Cannot cancel past bookings'

    @pytest.mark.asyncio
    async def test_cancel_booking_success(self, cancellation_service, mock_booking_repo, mock_policy_repo):
        """Test successful booking cancellation"""
        booking = MockBooking(
            status='confirmed',
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=48),
            deposit_amount=20.0
        )
        policy = MockCancellationPolicy()
        updated_booking = MockBooking(status='cancelled')

        mock_booking_repo.get_by_id.return_value = booking
        mock_policy_repo.get_platform_default.return_value = policy
        mock_booking_repo.update.return_value = updated_booking

        result = await cancellation_service.cancel_booking(
            booking_id=1,
            cancelled_by_id=1,
            reason="Client emergency"
        )

        assert result['success'] is True
        assert result['message'] == 'Booking cancelled with Standard (24-72h) fee'
        assert result['cancellation_fee'] == Decimal('15.0')
        assert result['refund_amount'] == Decimal('85.0')
        assert result['payment_required'] is False  # fee (15) < deposit (20)
        assert result['policy_applied'] == "Test Policy"

    @pytest.mark.asyncio
    async def test_cancel_booking_payment_required(self, cancellation_service, mock_booking_repo, mock_policy_repo):
        """Test cancellation when additional payment is required"""
        booking = MockBooking(
            status='confirmed',
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=48),
            deposit_amount=10.0  # Less than fee amount (15)
        )
        policy = MockCancellationPolicy()
        updated_booking = MockBooking(status='cancelled')

        mock_booking_repo.get_by_id.return_value = booking
        mock_policy_repo.get_platform_default.return_value = policy
        mock_booking_repo.update.return_value = updated_booking

        result = await cancellation_service.cancel_booking(
            booking_id=1,
            cancelled_by_id=1,
            reason="Client emergency"
        )

        assert result['payment_required'] is True  # fee (15) > deposit (10)

    @pytest.mark.asyncio
    async def test_cancel_booking_cannot_cancel(self, cancellation_service, mock_booking_repo):
        """Test cancellation when booking cannot be cancelled"""
        booking = MockBooking(status='completed')
        mock_booking_repo.get_by_id.return_value = booking

        with pytest.raises(ValueError, match="Cannot cancel completed booking"):
            await cancellation_service.cancel_booking(
                booking_id=1,
                cancelled_by_id=1,
                reason="Test"
            )

    @pytest.mark.asyncio
    async def test_assign_cancellation_policy_success(self, cancellation_service, mock_booking_repo, mock_policy_repo):
        """Test successful policy assignment"""
        booking = MockBooking()
        policy = MockCancellationPolicy(id=2, name="Custom Policy")

        mock_booking_repo.get_by_id.return_value = booking
        mock_policy_repo.get_by_id.return_value = policy
        mock_booking_repo.update.return_value = booking

        result = await cancellation_service.assign_cancellation_policy(1, 2)

        assert result['success'] is True
        assert result['policy_assigned'] == "Custom Policy"
        assert result['policy_id'] == 2

        # Verify update was called with correct data
        mock_booking_repo.update.assert_called_once_with(1, {'cancellation_policy_id': 2})

    @pytest.mark.asyncio
    async def test_assign_default_policy(self, cancellation_service, mock_booking_repo, mock_policy_repo):
        """Test assigning default policy when none specified"""
        booking = MockBooking()
        policy = MockCancellationPolicy(name="Default Policy")

        mock_booking_repo.get_by_id.return_value = booking
        mock_policy_repo.get_platform_default.return_value = policy
        mock_booking_repo.update.return_value = booking

        result = await cancellation_service.assign_cancellation_policy(1, None)

        assert result['success'] is True
        assert result['policy_assigned'] == "Default Policy"

    @pytest.mark.asyncio
    async def test_assign_policy_booking_not_found(self, cancellation_service, mock_booking_repo):
        """Test policy assignment when booking not found"""
        mock_booking_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Booking not found"):
            await cancellation_service.assign_cancellation_policy(999, 1)

    @pytest.mark.asyncio
    async def test_assign_policy_not_found(self, cancellation_service, mock_booking_repo, mock_policy_repo):
        """Test policy assignment when policy not found"""
        booking = MockBooking()
        mock_booking_repo.get_by_id.return_value = booking
        mock_policy_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Policy not found"):
            await cancellation_service.assign_cancellation_policy(1, 999)
