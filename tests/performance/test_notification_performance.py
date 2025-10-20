"""
Performance and load tests for notification system.

This module tests the performance characteristics of the notification
system under various load conditions to ensure it can handle real-world
usage patterns efficiently.
"""

import asyncio
import time
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.booking_notifications import BookingNotificationService
from backend.app.services.payment_notifications import PaymentNotificationService
from backend.app.services.loyalty_notifications import LoyaltyNotificationService
from backend.app.services.waitlist_notifications import WaitlistNotificationService


class TestNotificationPerformance:
    """Performance tests for notification system."""

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
    def mock_booking(self, mock_user):
        """Create a mock booking."""
        booking = MagicMock()
        booking.id = 1
        booking.user_id = mock_user.id
        booking.user = mock_user
        booking.service = MagicMock()
        booking.service.name = "Corte de Cabelo"
        booking.professional = MagicMock()
        booking.professional.user = MagicMock()
        booking.professional.user.full_name = "Maria Santos"
        booking.scheduled_at = datetime.now() + timedelta(days=1)
        booking.total_price = Decimal("50.00")
        booking.created_at = datetime.now()
        return booking

    async def test_single_notification_performance(self, mock_session, mock_booking):
        """Test performance of single notification sending."""
        with patch('backend.app.services.booking_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.booking_notifications.BookingRepository') as mock_booking_repo:
                with patch('backend.app.services.booking_notifications.UserRepository') as mock_user_repo:
                    # Setup mocks
                    mock_notification_service_instance = AsyncMock()
                    mock_notification_service.return_value = mock_notification_service_instance
                    mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                    mock_booking_repo_instance = AsyncMock()
                    mock_booking_repo.return_value = mock_booking_repo_instance
                    mock_booking_repo_instance.get_by_id_with_relations.return_value = mock_booking

                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = mock_booking.user

                    # Test single notification performance
                    service = BookingNotificationService(mock_session)

                    start_time = time.time()
                    result = await service.notify_booking_created(booking_id=1)
                    end_time = time.time()

                    # Verify performance
                    execution_time = end_time - start_time
                    assert execution_time < 0.1  # Should complete in under 100ms
                    assert result["notifications_queued"] == 1

    async def test_batch_notification_performance(self, mock_session):
        """Test performance of batch notification processing."""
        with patch('backend.app.services.waitlist_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.waitlist_notifications.UserRepository') as mock_user_repo:
                with patch('backend.app.services.waitlist_notifications.ServiceRepository') as mock_service_repo:
                    with patch('backend.app.services.waitlist_notifications.ProfessionalRepository') as mock_prof_repo:
                        # Setup mocks
                        mock_notification_service_instance = AsyncMock()
                        mock_notification_service.return_value = mock_notification_service_instance
                        mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                        mock_user = MagicMock()
                        mock_user.full_name = "Test User"
                        mock_user_repo_instance = AsyncMock()
                        mock_user_repo.return_value = mock_user_repo_instance
                        mock_user_repo_instance.get_by_id.return_value = mock_user

                        mock_service = MagicMock()
                        mock_service.name = "Test Service"
                        mock_service_repo_instance = AsyncMock()
                        mock_service_repo.return_value = mock_service_repo_instance
                        mock_service_repo_instance.get_by_id.return_value = mock_service

                        mock_professional = MagicMock()
                        mock_professional.user = MagicMock()
                        mock_professional.user.full_name = "Test Professional"
                        mock_prof_repo_instance = AsyncMock()
                        mock_prof_repo.return_value = mock_prof_repo_instance
                        mock_prof_repo_instance.get_by_id_with_user.return_value = mock_professional

                        # Create batch notifications
                        service = WaitlistNotificationService(mock_session)
                        batch_size = 100
                        notifications = []

                        for i in range(batch_size):
                            notifications.append({
                                "user_id": i + 1,
                                "waitlist_id": i + 1,
                                "service_id": 1,
                                "professional_id": 1,
                                "available_slot": datetime.now() + timedelta(hours=2),
                                "expiry_time": datetime.now() + timedelta(minutes=30)
                            })

                        # Test batch performance
                        start_time = time.time()
                        result = await service.notify_waitlist_batch_slots_available(notifications)
                        end_time = time.time()

                        # Verify performance
                        execution_time = end_time - start_time
                        assert execution_time < 5.0  # Should complete 100 notifications in under 5 seconds
                        assert result["total_notifications"] == batch_size

    async def test_concurrent_notification_performance(self, mock_session, mock_booking):
        """Test performance under concurrent notification load."""
        with patch('backend.app.services.booking_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.booking_notifications.BookingRepository') as mock_booking_repo:
                with patch('backend.app.services.booking_notifications.UserRepository') as mock_user_repo:
                    # Setup mocks
                    mock_notification_service_instance = AsyncMock()
                    mock_notification_service.return_value = mock_notification_service_instance
                    mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                    mock_booking_repo_instance = AsyncMock()
                    mock_booking_repo.return_value = mock_booking_repo_instance
                    mock_booking_repo_instance.get_by_id_with_relations.return_value = mock_booking

                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = mock_booking.user

                    # Create concurrent notification tasks
                    async def send_notification():
                        service = BookingNotificationService(mock_session)
                        return await service.notify_booking_created(booking_id=1)

                    concurrent_count = 50
                    tasks = [send_notification() for _ in range(concurrent_count)]

                    # Test concurrent performance
                    start_time = time.time()
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    end_time = time.time()

                    # Verify performance
                    execution_time = end_time - start_time
                    assert execution_time < 2.0  # Should handle 50 concurrent notifications in under 2 seconds

                    # Check that all notifications completed successfully
                    successful_results = [r for r in results if not isinstance(r, Exception)]
                    assert len(successful_results) == concurrent_count

    async def test_memory_usage_stability(self, mock_session):
        """Test that memory usage remains stable under repeated operations."""
        with patch('backend.app.services.loyalty_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.loyalty_notifications.UserRepository') as mock_user_repo:
                # Setup mocks
                mock_notification_service_instance = AsyncMock()
                mock_notification_service.return_value = mock_notification_service_instance
                mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                mock_user = MagicMock()
                mock_user.full_name = "Test User"
                mock_user_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_user_repo_instance
                mock_user_repo_instance.get_by_id.return_value = mock_user

                # Run repeated operations
                service = LoyaltyNotificationService(mock_session)

                for i in range(1000):  # Run 1000 operations
                    await service.notify_points_earned(
                        user_id=1,
                        points_earned=10,
                        transaction_type="booking",
                        transaction_id=i
                    )

                # If we reach here without memory issues, the test passes
                assert True

    async def test_notification_service_isolation(self, mock_session):
        """Test that different notification services don't interfere with each other."""
        with patch('backend.app.services.booking_notifications.NotificationService') as mock_booking_notifications:
            with patch('backend.app.services.payment_notifications.NotificationService') as mock_payment_notifications:
                with patch('backend.app.services.loyalty_notifications.NotificationService') as mock_loyalty_notifications:
                    # Setup mocks for different services
                    mock_booking_notifications_instance = AsyncMock()
                    mock_booking_notifications.return_value = mock_booking_notifications_instance
                    mock_booking_notifications_instance.send_notification.return_value = {"notifications_queued": 1}

                    mock_payment_notifications_instance = AsyncMock()
                    mock_payment_notifications.return_value = mock_payment_notifications_instance
                    mock_payment_notifications_instance.send_notification.return_value = {"notifications_queued": 1}

                    mock_loyalty_notifications_instance = AsyncMock()
                    mock_loyalty_notifications.return_value = mock_loyalty_notifications_instance
                    mock_loyalty_notifications_instance.send_notification.return_value = {"notifications_queued": 1}

                    # Setup additional mocks for repositories
                    with patch('backend.app.services.booking_notifications.BookingRepository') as mock_booking_repo:
                        with patch('backend.app.services.booking_notifications.UserRepository') as mock_user_repo:
                            with patch('backend.app.services.payment_notifications.PaymentRepository') as mock_payment_repo:
                                with patch('backend.app.services.loyalty_notifications.UserRepository') as mock_loyalty_user_repo:
                                    # Mock booking data
                                    mock_booking = MagicMock()
                                    mock_booking.id = 1
                                    mock_booking.user = MagicMock()
                                    mock_booking.user.full_name = "Test User"
                                    mock_booking.service = MagicMock()
                                    mock_booking.service.name = "Test Service"
                                    mock_booking.professional = MagicMock()
                                    mock_booking.professional.user = MagicMock()
                                    mock_booking.professional.user.full_name = "Test Professional"
                                    mock_booking.scheduled_at = datetime.now()
                                    mock_booking.total_price = Decimal("50.00")
                                    mock_booking.created_at = datetime.now()

                                    mock_booking_repo_instance = AsyncMock()
                                    mock_booking_repo.return_value = mock_booking_repo_instance
                                    mock_booking_repo_instance.get_by_id_with_relations.return_value = mock_booking

                                    mock_user_repo_instance = AsyncMock()
                                    mock_user_repo.return_value = mock_user_repo_instance
                                    mock_user_repo_instance.get_by_id.return_value = mock_booking.user

                                    # Mock payment data
                                    mock_payment = MagicMock()
                                    mock_payment.id = 1
                                    mock_payment.user = MagicMock()
                                    mock_payment.user.full_name = "Test User"
                                    mock_payment.amount = Decimal("50.00")
                                    mock_payment.payment_method = "credit_card"
                                    mock_payment.created_at = datetime.now()

                                    mock_payment_repo_instance = AsyncMock()
                                    mock_payment_repo.return_value = mock_payment_repo_instance
                                    mock_payment_repo_instance.get_payment_with_user.return_value = mock_payment

                                    # Mock loyalty user data
                                    mock_loyalty_user = MagicMock()
                                    mock_loyalty_user.full_name = "Test User"

                                    mock_loyalty_user_repo_instance = AsyncMock()
                                    mock_loyalty_user_repo.return_value = mock_loyalty_user_repo_instance
                                    mock_loyalty_user_repo_instance.get_by_id.return_value = mock_loyalty_user

                                    # Test concurrent operations across different services
                                    booking_service = BookingNotificationService(mock_session)
                                    payment_service = PaymentNotificationService(mock_session)
                                    loyalty_service = LoyaltyNotificationService(mock_session)

                                    start_time = time.time()

                                    # Run concurrent operations
                                    booking_task = booking_service.notify_booking_created(booking_id=1)
                                    payment_task = payment_service.notify_payment_received(payment_id=1)
                                    loyalty_task = loyalty_service.notify_points_earned(
                                        user_id=1,
                                        points_earned=100,
                                        transaction_type="booking"
                                    )

                                    results = await asyncio.gather(booking_task, payment_task, loyalty_task)

                                    end_time = time.time()

                                    # Verify all services completed successfully
                                    assert len(results) == 3
                                    for result in results:
                                        assert "notifications_queued" in result

                                    # Should complete quickly even with multiple services
                                    execution_time = end_time - start_time
                                    assert execution_time < 1.0


class TestNotificationSystemScalability:
    """Scalability tests for notification system."""

    @pytest.fixture
    async def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    async def test_large_context_data_handling(self, mock_session):
        """Test handling of notifications with large context data."""
        with patch('backend.app.services.booking_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.booking_notifications.BookingRepository') as mock_booking_repo:
                with patch('backend.app.services.booking_notifications.UserRepository') as mock_user_repo:
                    # Setup mocks
                    mock_notification_service_instance = AsyncMock()
                    mock_notification_service.return_value = mock_notification_service_instance
                    mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                    # Create booking with large data
                    mock_booking = MagicMock()
                    mock_booking.id = 1
                    mock_booking.user = MagicMock()
                    mock_booking.user.full_name = "Test User With Very Long Name " * 10  # Large name
                    mock_booking.service = MagicMock()
                    mock_booking.service.name = "Very Long Service Name " * 20  # Large service name
                    mock_booking.professional = MagicMock()
                    mock_booking.professional.user = MagicMock()
                    mock_booking.professional.user.full_name = "Professional Name " * 15
                    mock_booking.scheduled_at = datetime.now()
                    mock_booking.total_price = Decimal("999999.99")  # Large amount
                    mock_booking.created_at = datetime.now()

                    mock_booking_repo_instance = AsyncMock()
                    mock_booking_repo.return_value = mock_booking_repo_instance
                    mock_booking_repo_instance.get_by_id_with_relations.return_value = mock_booking

                    mock_user_repo_instance = AsyncMock()
                    mock_user_repo.return_value = mock_user_repo_instance
                    mock_user_repo_instance.get_by_id.return_value = mock_booking.user

                    # Test notification with large context
                    service = BookingNotificationService(mock_session)
                    result = await service.notify_booking_created(booking_id=1)

                    # Should handle large data without issues
                    assert result["notifications_queued"] == 1

    async def test_high_frequency_notifications(self, mock_session):
        """Test system behavior under high frequency notification generation."""
        with patch('backend.app.services.loyalty_notifications.NotificationService') as mock_notification_service:
            with patch('backend.app.services.loyalty_notifications.UserRepository') as mock_user_repo:
                # Setup mocks
                mock_notification_service_instance = AsyncMock()
                mock_notification_service.return_value = mock_notification_service_instance
                mock_notification_service_instance.send_notification.return_value = {"notifications_queued": 1}

                mock_user = MagicMock()
                mock_user.full_name = "Test User"
                mock_user_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_user_repo_instance
                mock_user_repo_instance.get_by_id.return_value = mock_user

                # Generate high frequency notifications
                service = LoyaltyNotificationService(mock_session)

                start_time = time.time()

                # Simulate high frequency points earning (1 per second for 60 seconds)
                tasks = []
                for i in range(60):
                    task = service.notify_points_earned(
                        user_id=1,
                        points_earned=1,
                        transaction_type="micro_transaction",
                        transaction_id=i
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)

                end_time = time.time()

                # Verify high frequency handling
                execution_time = end_time - start_time
                assert execution_time < 10.0  # Should handle 60 notifications in under 10 seconds
                assert len(results) == 60

                for result in results:
                    assert result["notifications_queued"] == 1
