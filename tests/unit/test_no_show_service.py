"""Tests for no-show service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.user import User, UserRole
from backend.app.domain.policies.no_show import NoShowReason
from backend.app.services.no_show import NoShowService


class TestNoShowService:
    """Test suite for NoShowService."""

    def setup_method(self):
        """Set up test dependencies."""
        self.booking_repository = AsyncMock()
        self.user_repository = AsyncMock()
        self.service = NoShowService(
            self.booking_repository,
            self.user_repository
        )

    def create_mock_booking(
        self,
        booking_id: int = 1,
        client_id: int = 1,
        professional_id: int = 2,
        service_id: int = 1,
        unit_id: int = 1,
        scheduled_at: datetime = None,
        status: BookingStatus = BookingStatus.CONFIRMED,
        price: float = 50.0,
        duration_minutes: int = 60,
        marked_no_show_at: datetime = None,
    ) -> Mock:
        """Create a mock booking for testing."""
        if scheduled_at is None:
            scheduled_at = datetime.utcnow() - timedelta(hours=1)

        booking = Mock(spec=Booking)
        booking.id = booking_id
        booking.client_id = client_id
        booking.professional_id = professional_id
        booking.service_id = service_id
        booking.unit_id = unit_id
        booking.scheduled_at = scheduled_at
        booking.status = status
        booking.price = price
        booking.duration_minutes = duration_minutes
        booking.marked_no_show_at = marked_no_show_at
        booking.marked_no_show_by_id = None
        booking.no_show_fee_amount = None
        booking.no_show_reason = None

        return booking

    def create_mock_user(
        self,
        user_id: int = 1,
        role: UserRole = UserRole.PROFESSIONAL,
        name: str = "Test User"
    ) -> Mock:
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = user_id
        user.role = role
        user.name = name

        return user

    @pytest.mark.asyncio
    async def test_get_default_no_show_policy(self):
        """Test getting default no-show policy."""
        policy = await self.service.get_default_no_show_policy()

        assert policy.id == 1
        assert policy.name == "Default No-Show Policy"
        assert policy.is_active is True
        assert policy.auto_detect_enabled is True
        assert policy.detection_delay_minutes == 15
        assert policy.client_no_show_rule.base_percentage == 50.0
        assert policy.dispute_window_hours == 24

    @pytest.mark.asyncio
    async def test_evaluate_booking_for_no_show_success(self):
        """Test successful no-show evaluation."""
        # Setup
        booking = self.create_mock_booking(
            scheduled_at=datetime.utcnow() - timedelta(minutes=30)
        )
        self.booking_repository.get_by_id.return_value = booking

        current_time = datetime.utcnow()

        # Execute
        evaluation = await self.service.evaluate_booking_for_no_show(
            booking.id, current_time
        )

        # Verify
        assert evaluation.should_mark_no_show is True
        assert evaluation.reason == NoShowReason.CLIENT_NO_SHOW
        assert evaluation.fee_amount == 25.0  # 50% of 50.0
        assert evaluation.minutes_late == 30
        assert evaluation.grace_period_expired is True
        assert evaluation.can_dispute is True

    @pytest.mark.asyncio
    async def test_evaluate_booking_for_no_show_not_found(self):
        """Test evaluation with non-existent booking."""
        self.booking_repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Booking not found: 999"):
            await self.service.evaluate_booking_for_no_show(999)

    @pytest.mark.asyncio
    async def test_evaluate_booking_for_no_show_wrong_status(self):
        """Test evaluation with wrong booking status."""
        booking = self.create_mock_booking(status=BookingStatus.CANCELLED)
        self.booking_repository.get_by_id.return_value = booking

        with pytest.raises(ValueError, match="cannot be evaluated for no-show"):
            await self.service.evaluate_booking_for_no_show(booking.id)

    @pytest.mark.asyncio
    async def test_evaluate_booking_for_no_show_already_marked(self):
        """Test evaluation with already marked no-show."""
        booking = self.create_mock_booking(
            marked_no_show_at=datetime.utcnow()
        )
        self.booking_repository.get_by_id.return_value = booking

        with pytest.raises(ValueError, match="already marked as no-show"):
            await self.service.evaluate_booking_for_no_show(booking.id)

    @pytest.mark.asyncio
    async def test_evaluate_booking_for_no_show_within_grace_period(self):
        """Test evaluation within grace period."""
        # Booking is only 10 minutes late (within 15 minute grace period)
        booking = self.create_mock_booking(
            scheduled_at=datetime.utcnow() - timedelta(minutes=10)
        )
        self.booking_repository.get_by_id.return_value = booking

        evaluation = await self.service.evaluate_booking_for_no_show(booking.id)

        assert evaluation.should_mark_no_show is False
        assert evaluation.reason is None
        assert evaluation.fee_amount == 0.0
        assert evaluation.grace_period_expired is False

    @pytest.mark.asyncio
    async def test_mark_booking_no_show_success(self):
        """Test successful no-show marking."""
        # Setup
        booking = self.create_mock_booking()
        user = self.create_mock_user()

        self.booking_repository.get_by_id.return_value = booking
        self.user_repository.get_by_id.return_value = user

        # Mock evaluation
        self.service.evaluate_booking_for_no_show = AsyncMock()
        mock_evaluation = Mock()
        mock_evaluation.fee_amount = 25.0
        self.service.evaluate_booking_for_no_show.return_value = mock_evaluation

        # Execute
        result = await self.service.mark_booking_no_show(
            booking_id=booking.id,
            marked_by_id=user.id,
            reason=NoShowReason.CLIENT_NO_SHOW,
            reason_notes="Did not show up"
        )

        # Verify
        assert result.marked_no_show_at is not None
        assert result.marked_no_show_by_id == user.id
        assert result.no_show_fee_amount == 25.0
        assert "client_no_show: Did not show up" in result.no_show_reason
        assert result.status == BookingStatus.NO_SHOW

        self.booking_repository.update.assert_called_once_with(booking)

    @pytest.mark.asyncio
    async def test_mark_booking_no_show_already_marked(self):
        """Test marking already marked no-show."""
        booking = self.create_mock_booking(
            marked_no_show_at=datetime.utcnow()
        )
        self.booking_repository.get_by_id.return_value = booking

        with pytest.raises(ValueError, match="already marked as no-show"):
            await self.service.mark_booking_no_show(
                booking.id, 1, NoShowReason.CLIENT_NO_SHOW
            )

    @pytest.mark.asyncio
    async def test_mark_booking_no_show_user_not_found(self):
        """Test marking with non-existent user."""
        booking = self.create_mock_booking()
        self.booking_repository.get_by_id.return_value = booking
        self.user_repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="User not found: 999"):
            await self.service.mark_booking_no_show(
                booking.id, 999, NoShowReason.CLIENT_NO_SHOW
            )

    @pytest.mark.asyncio
    async def test_mark_booking_no_show_manual_fee(self):
        """Test marking with manual fee override."""
        booking = self.create_mock_booking()
        user = self.create_mock_user()

        self.booking_repository.get_by_id.return_value = booking
        self.user_repository.get_by_id.return_value = user

        result = await self.service.mark_booking_no_show(
            booking_id=booking.id,
            marked_by_id=user.id,
            reason=NoShowReason.CLIENT_NO_SHOW,
            manual_fee_amount=40.0
        )

        assert result.no_show_fee_amount == 40.0

    @pytest.mark.asyncio
    async def test_auto_detect_no_shows_success(self):
        """Test successful auto-detection of no-shows."""
        # Setup bookings
        booking1 = self.create_mock_booking(
            booking_id=1,
            scheduled_at=datetime.utcnow() - timedelta(minutes=30)
        )
        booking2 = self.create_mock_booking(
            booking_id=2,
            scheduled_at=datetime.utcnow() - timedelta(minutes=10)
        )

        self.booking_repository.find_by_criteria.return_value = [booking1, booking2]

        # Mock evaluations
        self.service.evaluate_booking_for_no_show = AsyncMock()

        # booking1 should be marked
        mock_eval1 = Mock()
        mock_eval1.should_mark_no_show = True
        mock_eval1.reason = NoShowReason.CLIENT_NO_SHOW
        mock_eval1.fee_amount = 25.0

        # booking2 should not be marked
        mock_eval2 = Mock()
        mock_eval2.should_mark_no_show = False
        mock_eval2.minutes_late = 10

        self.service.evaluate_booking_for_no_show.side_effect = [mock_eval1, mock_eval2]

        # Mock marking
        self.service.mark_booking_no_show = AsyncMock()
        marked_booking = Mock()
        marked_booking.marked_no_show_at = datetime.utcnow()
        self.service.mark_booking_no_show.return_value = marked_booking

        # Execute
        results = await self.service.auto_detect_no_shows(time_window_hours=24)

        # Verify
        assert len(results) == 2

        # First booking should be marked
        assert results[0]["booking_id"] == 1
        assert results[0]["action"] == "marked_no_show"
        assert results[0]["reason"] == "client_no_show"
        assert results[0]["fee_amount"] == 25.0

        # Second booking should have no action
        assert results[1]["booking_id"] == 2
        assert results[1]["action"] == "no_action"
        assert results[1]["minutes_late"] == 10

    @pytest.mark.asyncio
    async def test_dispute_no_show_success(self):
        """Test successful no-show dispute."""
        booking = self.create_mock_booking(
            marked_no_show_at=datetime.utcnow() - timedelta(hours=1)
        )
        user = self.create_mock_user()

        self.booking_repository.get_by_id.return_value = booking
        self.user_repository.get_by_id.return_value = user

        result = await self.service.dispute_no_show(
            booking_id=booking.id,
            disputed_by_id=user.id,
            dispute_reason="I was there on time"
        )

        assert result == booking

    @pytest.mark.asyncio
    async def test_dispute_no_show_not_marked(self):
        """Test disputing booking not marked as no-show."""
        booking = self.create_mock_booking(marked_no_show_at=None)
        self.booking_repository.get_by_id.return_value = booking

        with pytest.raises(ValueError, match="not marked as no-show"):
            await self.service.dispute_no_show(
                booking.id, 1, "I was there"
            )

    @pytest.mark.asyncio
    async def test_dispute_no_show_expired_window(self):
        """Test disputing after window expires."""
        # Marked 2 days ago (beyond 24 hour window)
        booking = self.create_mock_booking(
            marked_no_show_at=datetime.utcnow() - timedelta(days=2)
        )
        user = self.create_mock_user()

        self.booking_repository.get_by_id.return_value = booking
        self.user_repository.get_by_id.return_value = user

        with pytest.raises(ValueError, match="Dispute window expired"):
            await self.service.dispute_no_show(
                booking.id, user.id, "I was there"
            )

    @pytest.mark.asyncio
    async def test_can_dispute_no_show_success(self):
        """Test checking dispute eligibility."""
        booking = self.create_mock_booking(
            client_id=123,
            marked_no_show_at=datetime.utcnow() - timedelta(hours=1)
        )
        self.booking_repository.get_by_id.return_value = booking

        result = await self.service.can_dispute_no_show(booking.id, 123)

        assert result["can_dispute"] is True
        assert "deadline" in result
        assert "hours_remaining" in result

    @pytest.mark.asyncio
    async def test_can_dispute_no_show_wrong_client(self):
        """Test checking dispute with wrong client."""
        booking = self.create_mock_booking(
            client_id=123,
            marked_no_show_at=datetime.utcnow()
        )
        self.booking_repository.get_by_id.return_value = booking

        result = await self.service.can_dispute_no_show(booking.id, 456)

        assert result["can_dispute"] is False
        assert result["reason"] == "not_booking_client"

    @pytest.mark.asyncio
    async def test_get_no_show_statistics(self):
        """Test getting no-show statistics."""
        # Setup bookings
        booking1 = self.create_mock_booking(booking_id=1)  # Normal booking

        booking2 = self.create_mock_booking(
            booking_id=2,
            marked_no_show_at=datetime.utcnow()
        )
        booking2.no_show_fee_amount = 25.0
        booking2.no_show_reason = "client_no_show"

        booking3 = self.create_mock_booking(
            booking_id=3,
            marked_no_show_at=datetime.utcnow()
        )
        booking3.no_show_fee_amount = 30.0
        booking3.no_show_reason = "professional_no_show"

        all_bookings = [booking1, booking2, booking3]

        self.booking_repository.find_by_criteria.return_value = all_bookings

        stats = await self.service.get_no_show_statistics()

        assert stats["totals"]["bookings"] == 3
        assert stats["totals"]["no_shows"] == 2
        assert stats["totals"]["no_show_rate"] == 66.67
        assert stats["financial"]["total_fees_charged"] == 55.0
        assert stats["financial"]["average_fee"] == 27.5
        assert stats["reasons"]["client_no_show"] == 1
        assert stats["reasons"]["professional_no_show"] == 1
