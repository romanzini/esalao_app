"""
Integration tests for notification system with business workflows.

This module tests the integration of the notification system with
booking, payment, loyalty, and waitlist workflows to ensure
notifications are properly triggered and delivered.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.booking_notifications import BookingNotificationService
from backend.app.services.payment_notifications import PaymentNotificationService
from backend.app.services.loyalty_notifications import LoyaltyNotificationService
from backend.app.services.waitlist_notifications import WaitlistNotificationService
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.payment import Payment, PaymentStatus
from backend.app.db.models.user import User
from backend.app.db.models.service import Service
from backend.app.db.models.professional import Professional


class TestNotificationIntegration:
    """Test suite for notification system integration."""

    @pytest.fixture
    async def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = 1
        user.full_name = "João Silva"
        user.email = "joao@example.com"
        user.phone = "+5511999999999"
        return user

    @pytest.fixture
    def mock_service(self):
        """Create a mock service."""
        service = MagicMock()
        service.id = 1
        service.name = "Corte de Cabelo"
        service.duration_minutes = 60
        service.price = Decimal("50.00")
        return service

    @pytest.fixture
    def mock_professional(self):
        """Create a mock professional."""
        professional = MagicMock()
        professional.id = 1
        professional.user = MagicMock()
        professional.user.full_name = "Maria Santos"
        return professional

    @pytest.fixture
    def mock_booking(self, mock_user, mock_service, mock_professional):
        """Create a mock booking."""
        booking = MagicMock()
        booking.id = 1
        booking.user_id = mock_user.id
        booking.user = mock_user
        booking.service = mock_service
        booking.professional = mock_professional
        booking.scheduled_at = datetime.now() + timedelta(days=1)
        booking.status = BookingStatus.CONFIRMED
        booking.total_price = Decimal("50.00")
        booking.created_at = datetime.now()
        return booking

    @pytest.fixture
    def mock_payment(self, mock_user):
        """Create a mock payment."""
        payment = MagicMock()
        payment.id = 1
        payment.user_id = mock_user.id
        payment.user = mock_user
        payment.amount = Decimal("50.00")
        payment.payment_method = "credit_card"
        payment.status = PaymentStatus.CONFIRMED
        payment.created_at = datetime.now()
        payment.booking_id = 1
        payment.provider_payment_id = "PAY123456"
        return payment

    async def test_booking_notification_integration(self, mock_session, mock_booking):
        """Test booking notification integration."""
        with patch('backend.app.services.booking_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.booking_notifications.BookingRepository') as mock_booking_repo:
                with patch('backend.app.services.booking_notifications.UserRepository') as mock_user_repo:
                    # Setup mocks
                    mock_notification_service_instance = AsyncMock()
                    mock_notification_service.return_value = mock_notification_service_instance
                    mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 3}

                    mock_booking_repo_instance = AsyncMock()
                    mock_booking_repo.return_value = mock_booking_repo_instance
                    mock_booking_repo_instance.get_by_id_with_relations.return_value = mock_booking

                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = mock_booking.user

                    # Test booking creation notification
                    service = BookingNotificationService(mock_session)
                    result = await service.notify_booking_created(
                        booking_id=1,
                        include_reminders=True
                    )

                    # Verify notification was sent
                    assert result["booking_id"] == 1
                    assert result["notifications_queued"] == 3
                    mock_notification_service_instance.send_notification.assert_called()

    async def test_payment_notification_integration(self, mock_session, mock_payment):
        """Test payment notification integration."""
        with patch('backend.app.services.payment_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.payment_notifications.PaymentRepository') as mock_payment_repo:
                with patch('backend.app.services.payment_notifications.UserRepository') as mock_user_repo:
                    # Setup mocks
                    mock_notification_service_instance = AsyncMock()
                    mock_notification_service.return_value = mock_notification_service_instance
                    mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                    mock_payment_repo_instance = AsyncMock()
                    mock_payment_repo.return_value = mock_payment_repo_instance
                    mock_payment_repo_instance.get_payment_with_user.return_value = mock_payment

                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = mock_payment.user

                    # Test payment confirmation notification
                    service = PaymentNotificationService(mock_session)
                    result = await service.notify_payment_received(payment_id=1)

                    # Verify notification was sent
                    assert result["payment_id"] == 1
                    assert result["notifications_queued"] == 1
                    mock_notification_service_instance.send_notification.assert_called()

    async def test_loyalty_notification_integration(self, mock_session, mock_user):
        """Test loyalty notification integration."""
        with patch('backend.app.services.loyalty_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.loyalty_notifications.UserRepository') as mock_user_repo:
                # Setup mocks
                mock_notification_service_instance = AsyncMock()
                mock_notification_service.return_value = mock_notification_service_instance
                mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                mock_user_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_user_repo_instance
                mock_user_repo_instance.get_by_id.return_value = mock_user

                # Test points earned notification
                service = LoyaltyNotificationService(mock_session)
                result = await service.notify_points_earned(
                    user_id=1,
                    points_earned=100,
                    transaction_type="booking",
                    transaction_id=1
                )

                # Verify notification was sent
                assert result["user_id"] == 1
                assert result["points_earned"] == 100
                assert result["notifications_queued"] == 1
                mock_notification_service_instance.send_notification.assert_called()

    async def test_waitlist_notification_integration(self, mock_session, mock_user, mock_service, mock_professional):
        """Test waitlist notification integration."""
        with patch('backend.app.services.waitlist_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.waitlist_notifications.UserRepository') as mock_user_repo:
                with patch('backend.app.services.waitlist_notifications.ServiceRepository') as mock_service_repo:
                    with patch('backend.app.services.waitlist_notifications.ProfessionalRepository') as mock_prof_repo:
                        # Setup mocks
                        mock_notification_service_instance = AsyncMock()
                        mock_notification_service.return_value = mock_notification_service_instance
                        mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                        mock_user_repo_instance = AsyncMock()
                        mock_user_repo.return_value = mock_user_repo_instance
                        mock_user_repo_instance.get_by_id.return_value = mock_user

                        mock_service_repo_instance = AsyncMock()
                        mock_service_repo.return_value = mock_service_repo_instance
                        mock_service_repo_instance.get_by_id.return_value = mock_service

                        mock_prof_repo_instance = AsyncMock()
                        mock_prof_repo.return_value = mock_prof_repo_instance
                        mock_prof_repo_instance.get_by_id_with_user.return_value = mock_professional

                        # Test slot available notification
                        service = WaitlistNotificationService(mock_session)
                        available_slot = datetime.now() + timedelta(hours=2)
                        expiry_time = datetime.now() + timedelta(minutes=30)

                        result = await service.notify_slot_available(
                            user_id=1,
                            waitlist_id=1,
                            service_id=1,
                            professional_id=1,
                            available_slot=available_slot,
                            expiry_time=expiry_time
                        )

                        # Verify notification was sent
                        assert result["user_id"] == 1
                        assert result["waitlist_id"] == 1
                        assert result["notifications_queued"] == 1
                        mock_notification_service_instance.send_notification.assert_called()

    async def test_booking_cancellation_with_notifications(self, mock_session, mock_booking):
        """Test booking cancellation triggers appropriate notifications."""
        with patch('backend.app.services.booking_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.booking_notifications.BookingRepository') as mock_booking_repo:
                with patch('backend.app.services.booking_notifications.UserRepository') as mock_user_repo:
                    # Setup mocks
                    mock_notification_service_instance = AsyncMock()
                    mock_notification_service.return_value = mock_notification_service_instance
                    mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 2}

                    mock_booking_repo_instance = AsyncMock()
                    mock_booking_repo.return_value = mock_booking_repo_instance
                    mock_booking_repo_instance.get_by_id_with_relations.return_value = mock_booking

                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = mock_booking.user

                    # Test booking cancellation notification
                    service = BookingNotificationService(mock_session)
                    result = await service.notify_booking_cancelled(
                        booking_id=1,
                        cancellation_reason="Cliente solicitou"
                    )

                    # Verify notification was sent
                    assert result["booking_id"] == 1
                    assert result["notifications_queued"] == 2
                    mock_notification_service_instance.send_notification.assert_called()

    async def test_payment_failure_with_notifications(self, mock_session, mock_payment):
        """Test payment failure triggers appropriate notifications."""
        with patch('backend.app.services.payment_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.payment_notifications.PaymentRepository') as mock_payment_repo:
                with patch('backend.app.services.payment_notifications.UserRepository') as mock_user_repo:
                    # Setup mocks
                    mock_payment.status = PaymentStatus.FAILED

                    mock_notification_service_instance = AsyncMock()
                    mock_notification_service.return_value = mock_notification_service_instance
                    mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                    mock_payment_repo_instance = AsyncMock()
                    mock_payment_repo.return_value = mock_payment_repo_instance
                    mock_payment_repo_instance.get_payment_with_user.return_value = mock_payment

                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = mock_payment.user

                    # Test payment failure notification
                    service = PaymentNotificationService(mock_session)
                    result = await service.notify_payment_failed(
                        payment_id=1,
                        failure_reason="Cartão negado"
                    )

                    # Verify notification was sent
                    assert result["payment_id"] == 1
                    assert result["notifications_queued"] == 1
                    mock_notification_service_instance.send_notification.assert_called()

    async def test_tier_upgrade_notification(self, mock_session, mock_user):
        """Test loyalty tier upgrade notification."""
        with patch('backend.app.services.loyalty_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.loyalty_notifications.UserRepository') as mock_user_repo:
                # Setup mocks
                mock_notification_service_instance = AsyncMock()
                mock_notification_service.return_value = mock_notification_service_instance
                mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                mock_user_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_user_repo_instance
                mock_user_repo_instance.get_by_id.return_value = mock_user

                # Test tier upgrade notification
                service = LoyaltyNotificationService(mock_session)
                result = await service.notify_tier_upgrade(
                    user_id=1,
                    old_tier="bronze",
                    new_tier="silver",
                    new_benefits=["Desconto de 10%", "Prioridade na agenda"]
                )

                # Verify notification was sent
                assert result["user_id"] == 1
                assert result["old_tier"] == "bronze"
                assert result["new_tier"] == "silver"
                assert result["notifications_queued"] == 1
                mock_notification_service_instance.send_notification.assert_called()

    async def test_batch_waitlist_notifications(self, mock_session, mock_user, mock_service, mock_professional):
        """Test batch waitlist notifications."""
        with patch('backend.app.services.waitlist_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.waitlist_notifications.UserRepository') as mock_user_repo:
                with patch('backend.app.services.waitlist_notifications.ServiceRepository') as mock_service_repo:
                    with patch('backend.app.services.waitlist_notifications.ProfessionalRepository') as mock_prof_repo:
                        # Setup mocks
                        mock_notification_service_instance = AsyncMock()
                        mock_notification_service.return_value = mock_notification_service_instance
                        mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                        mock_user_repo_instance = AsyncMock()
                        mock_user_repo.return_value = mock_user_repo_instance
                        mock_user_repo_instance.get_by_id.return_value = mock_user

                        mock_service_repo_instance = AsyncMock()
                        mock_service_repo.return_value = mock_service_repo_instance
                        mock_service_repo_instance.get_by_id.return_value = mock_service

                        mock_prof_repo_instance = AsyncMock()
                        mock_prof_repo.return_value = mock_prof_repo_instance
                        mock_prof_repo_instance.get_by_id_with_user.return_value = mock_professional

                        # Test batch notifications
                        service = WaitlistNotificationService(mock_session)
                        notifications = [
                            {
                                "user_id": 1,
                                "waitlist_id": 1,
                                "service_id": 1,
                                "professional_id": 1,
                                "available_slot": datetime.now() + timedelta(hours=2),
                                "expiry_time": datetime.now() + timedelta(minutes=30)
                            },
                            {
                                "user_id": 2,
                                "waitlist_id": 2,
                                "service_id": 1,
                                "professional_id": 1,
                                "available_slot": datetime.now() + timedelta(hours=3),
                                "expiry_time": datetime.now() + timedelta(minutes=30)
                            }
                        ]

                        result = await service.notify_waitlist_batch_slots_available(notifications)

                        # Verify batch notification results
                        assert result["total_notifications"] == 2
                        assert result["successful_count"] >= 0
                        assert result["total_queued"] >= 0


class TestNotificationErrorHandling:
    """Test error handling in notification integrations."""

    @pytest.fixture
    async def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    async def test_booking_notification_handles_missing_booking(self, mock_session):
        """Test booking notification handles missing booking gracefully."""
        with patch('backend.app.services.booking_notifications.BookingRepository') as mock_booking_repo:
            mock_booking_repo_instance = AsyncMock()
            mock_booking_repo.return_value = mock_booking_repo_instance
            mock_booking_repo_instance.get_by_id_with_relations.return_value = None

            service = BookingNotificationService(mock_session)

            with pytest.raises(ValueError, match="Booking 999 not found"):
                await service.notify_booking_created(booking_id=999)

    async def test_payment_notification_handles_missing_payment(self, mock_session):
        """Test payment notification handles missing payment gracefully."""
        with patch('backend.app.services.payment_notifications.PaymentRepository') as mock_payment_repo:
            mock_payment_repo_instance = AsyncMock()
            mock_payment_repo.return_value = mock_payment_repo_instance
            mock_payment_repo_instance.get_payment_with_user.return_value = None

            service = PaymentNotificationService(mock_session)

            with pytest.raises(ValueError, match="Payment 999 not found"):
                await service.notify_payment_received(payment_id=999)

    async def test_loyalty_notification_handles_missing_user(self, mock_session):
        """Test loyalty notification handles missing user gracefully."""
        with patch('backend.app.services.loyalty_notifications.UserRepository') as mock_user_repo:
            mock_user_repo_instance = AsyncMock()
            mock_user_repo.return_value = mock_user_repo_instance
            mock_user_repo_instance.get_by_id.return_value = None

            service = LoyaltyNotificationService(mock_session)

            with pytest.raises(ValueError, match="User 999 not found"):
                await service.notify_points_earned(
                    user_id=999,
                    points_earned=100,
                    transaction_type="booking"
                )

    async def test_waitlist_notification_handles_missing_data(self, mock_session):
        """Test waitlist notification handles missing related data gracefully."""
        with patch('backend.app.services.waitlist_notifications.UserRepository') as mock_user_repo:
            with patch('backend.app.services.waitlist_notifications.ServiceRepository') as mock_service_repo:
                with patch('backend.app.services.waitlist_notifications.ProfessionalRepository') as mock_prof_repo:
                    # Setup mocks to return None
                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = None

                    mock_service_repo_instance = AsyncMock()
                    mock_service_repo.return_value = mock_service_repo_instance
                    mock_service_repo_instance.get_by_id.return_value = None

                    mock_prof_repo_instance = AsyncMock()
                    mock_prof_repo.return_value = mock_prof_repo_instance
                    mock_prof_repo_instance.get_by_id_with_user.return_value = None

                    service = WaitlistNotificationService(mock_session)

                    with pytest.raises(ValueError, match="Required data not found"):
                        await service.notify_slot_available(
                            user_id=999,
                            waitlist_id=1,
                            service_id=999,
                            professional_id=999,
                            available_slot=datetime.now() + timedelta(hours=2),
                            expiry_time=datetime.now() + timedelta(minutes=30)
                        )
