"""
Booking notification integration service.

This service integrates the notification system with booking events,
automatically sending notifications when bookings are created, updated,
cancelled, or completed.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.db.repositories.professional import ProfessionalRepository
from backend.app.db.repositories.service import ServiceRepository
from backend.app.services.notifications import NotificationService
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.notifications import NotificationEventType, NotificationPriority


logger = logging.getLogger(__name__)


class BookingNotificationService:
    """Service for handling booking-related notifications."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the booking notification service.

        Args:
            session: Database session
        """
        self.session = session
        self.notification_service = NotificationService(session)
        self.booking_repo = BookingRepository(session)
        self.user_repo = UserRepository(session)
        self.professional_repo = ProfessionalRepository(session)
        self.service_repo = ServiceRepository(session)

    async def notify_booking_created(
        self,
        booking_id: int,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send booking confirmation notifications.

        Args:
            booking_id: ID of the created booking
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get booking with related data
            booking = await self._get_booking_with_relations(booking_id)
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            # Prepare context data
            context = await self._prepare_booking_context(booking)

            # Send notification to client
            client_result = await self.notification_service.send_notification(
                user_id=booking.client_id,
                event_type=NotificationEventType.BOOKING_CONFIRMED.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"booking_{booking_id}"
            )

            # Send notification to professional
            professional_context = context.copy()
            professional_context.update({
                "client_name": booking.client.full_name,
                "client_phone": booking.client.phone or "Não informado",
                "is_new_client": await self._is_new_client(booking.client_id, booking.professional_id)
            })

            professional_result = await self.notification_service.send_notification(
                user_id=booking.professional.user_id,
                event_type=NotificationEventType.NEW_BOOKING.value,
                context_data=professional_context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"booking_{booking_id}_pro"
            )

            logger.info(f"Booking confirmation notifications sent for booking {booking_id}")

            return {
                "booking_id": booking_id,
                "client_notifications": client_result["notifications_queued"],
                "professional_notifications": professional_result["notifications_queued"],
                "total_notifications": client_result["notifications_queued"] + professional_result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send booking creation notifications for booking {booking_id}: {str(e)}")
            raise

    async def notify_booking_cancelled(
        self,
        booking_id: int,
        cancellation_reason: Optional[str] = None,
        refund_amount: Optional[float] = None,
        cancellation_fee: Optional[float] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send booking cancellation notifications.

        Args:
            booking_id: ID of the cancelled booking
            cancellation_reason: Reason for cancellation
            refund_amount: Amount being refunded
            cancellation_fee: Cancellation fee charged
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get booking with related data
            booking = await self._get_booking_with_relations(booking_id)
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            # Prepare context data
            context = await self._prepare_booking_context(booking)
            context.update({
                "cancellation_reason": cancellation_reason or "Não informado",
                "refund_amount": f"{refund_amount:.2f}" if refund_amount else "0.00",
                "cancellation_fee": f"{cancellation_fee:.2f}" if cancellation_fee else "0.00",
                "has_refund": refund_amount is not None and refund_amount > 0,
                "has_fee": cancellation_fee is not None and cancellation_fee > 0
            })

            # Send notification to client
            client_result = await self.notification_service.send_notification(
                user_id=booking.client_id,
                event_type=NotificationEventType.BOOKING_CANCELLED.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"booking_{booking_id}_cancelled"
            )

            # Send notification to professional
            professional_context = context.copy()
            professional_context.update({
                "client_name": booking.client.full_name,
                "client_phone": booking.client.phone or "Não informado"
            })

            professional_result = await self.notification_service.send_notification(
                user_id=booking.professional.user_id,
                event_type=NotificationEventType.CANCELLATION_NOTICE.value,
                context_data=professional_context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"booking_{booking_id}_cancelled_pro"
            )

            logger.info(f"Booking cancellation notifications sent for booking {booking_id}")

            return {
                "booking_id": booking_id,
                "client_notifications": client_result["notifications_queued"],
                "professional_notifications": professional_result["notifications_queued"],
                "total_notifications": client_result["notifications_queued"] + professional_result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send booking cancellation notifications for booking {booking_id}: {str(e)}")
            raise

    async def notify_booking_rescheduled(
        self,
        booking_id: int,
        old_date: datetime,
        old_time: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send booking reschedule notifications.

        Args:
            booking_id: ID of the rescheduled booking
            old_date: Previous booking date
            old_time: Previous booking time
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get booking with related data
            booking = await self._get_booking_with_relations(booking_id)
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            # Prepare context data
            context = await self._prepare_booking_context(booking)
            context.update({
                "old_appointment_date": old_date.strftime("%d/%m/%Y"),
                "old_appointment_time": old_time,
                "reschedule_reason": "Reagendamento solicitado"
            })

            # Send notification to client
            client_result = await self.notification_service.send_notification(
                user_id=booking.client_id,
                event_type=NotificationEventType.BOOKING_RESCHEDULED.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"booking_{booking_id}_rescheduled"
            )

            # Send notification to professional
            professional_context = context.copy()
            professional_context.update({
                "client_name": booking.client.full_name,
                "client_phone": booking.client.phone or "Não informado"
            })

            professional_result = await self.notification_service.send_notification(
                user_id=booking.professional.user_id,
                event_type=NotificationEventType.CANCELLATION_NOTICE.value,  # Reuse cancellation notice for reschedule
                context_data=professional_context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"booking_{booking_id}_rescheduled_pro"
            )

            logger.info(f"Booking reschedule notifications sent for booking {booking_id}")

            return {
                "booking_id": booking_id,
                "client_notifications": client_result["notifications_queued"],
                "professional_notifications": professional_result["notifications_queued"],
                "total_notifications": client_result["notifications_queued"] + professional_result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send booking reschedule notifications for booking {booking_id}: {str(e)}")
            raise

    async def notify_booking_completed(
        self,
        booking_id: int,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send booking completion notifications.

        Args:
            booking_id: ID of the completed booking
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get booking with related data
            booking = await self._get_booking_with_relations(booking_id)
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            # Prepare context data
            context = await self._prepare_booking_context(booking)
            context.update({
                "completion_time": datetime.now().strftime("%H:%M"),
                "review_url": f"{context.get('app_url', '')}/reviews/create/{booking_id}"
            })

            # Send notification to client
            result = await self.notification_service.send_notification(
                user_id=booking.client_id,
                event_type=NotificationEventType.BOOKING_COMPLETED.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"booking_{booking_id}_completed"
            )

            logger.info(f"Booking completion notification sent for booking {booking_id}")

            return {
                "booking_id": booking_id,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send booking completion notification for booking {booking_id}: {str(e)}")
            raise

    async def notify_no_show_detected(
        self,
        booking_id: int,
        no_show_reason: str,
        fee_charged: Optional[float] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send no-show detection notifications.

        Args:
            booking_id: ID of the no-show booking
            no_show_reason: Reason for no-show detection
            fee_charged: Fee charged for no-show
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get booking with related data
            booking = await self._get_booking_with_relations(booking_id)
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            # Prepare context data
            context = await self._prepare_booking_context(booking)
            context.update({
                "no_show_reason": no_show_reason,
                "fee_charged": f"{fee_charged:.2f}" if fee_charged else "0.00",
                "has_fee": fee_charged is not None and fee_charged > 0,
                "detection_time": datetime.now().strftime("%H:%M")
            })

            # Send notification to client
            result = await self.notification_service.send_notification(
                user_id=booking.client_id,
                event_type=NotificationEventType.NO_SHOW_DETECTED.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"booking_{booking_id}_no_show"
            )

            logger.info(f"No-show detection notification sent for booking {booking_id}")

            return {
                "booking_id": booking_id,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send no-show notification for booking {booking_id}: {str(e)}")
            raise

    async def schedule_booking_reminders(
        self,
        booking_id: int,
        reminder_times: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Schedule booking reminder notifications.

        Args:
            booking_id: ID of the booking
            reminder_times: List of minutes before appointment to send reminders
                          Default: [1440, 120, 30] (24h, 2h, 30min)

        Returns:
            Dictionary with scheduled reminders
        """
        try:
            if reminder_times is None:
                reminder_times = [1440, 120, 30]  # 24h, 2h, 30min

            # Get booking with related data
            booking = await self._get_booking_with_relations(booking_id)
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            # Prepare context data
            context = await self._prepare_booking_context(booking)

            scheduled_reminders = []

            for minutes_before in reminder_times:
                # Calculate reminder time
                reminder_time = booking.scheduled_at - timedelta(minutes=minutes_before)

                # Skip if reminder time is in the past
                if reminder_time <= datetime.now():
                    continue

                # Determine reminder period text
                if minutes_before >= 1440:  # 24+ hours
                    hours = minutes_before // 60
                    reminder_period = f"em {hours} horas" if hours > 1 else "amanhã"
                elif minutes_before >= 60:  # 1+ hours
                    hours = minutes_before // 60
                    reminder_period = f"em {hours} horas" if hours > 1 else "em 1 hora"
                else:  # Less than 1 hour
                    reminder_period = f"em {minutes_before} minutos"

                # Update context with reminder-specific data
                reminder_context = context.copy()
                reminder_context.update({
                    "reminder_period": reminder_period,
                    "minutes_until_appointment": minutes_before
                })

                # Schedule reminder notification
                result = await self.notification_service.send_notification(
                    user_id=booking.client_id,
                    event_type=NotificationEventType.BOOKING_REMINDER.value,
                    context_data=reminder_context,
                    priority=NotificationPriority.NORMAL.value,
                    scheduled_at=reminder_time,
                    correlation_id=f"booking_{booking_id}_reminder_{minutes_before}min"
                )

                scheduled_reminders.append({
                    "minutes_before": minutes_before,
                    "reminder_time": reminder_time.isoformat(),
                    "notifications_queued": result["notifications_queued"]
                })

            logger.info(f"Scheduled {len(scheduled_reminders)} reminders for booking {booking_id}")

            return {
                "booking_id": booking_id,
                "scheduled_reminders": scheduled_reminders,
                "total_reminders": len(scheduled_reminders)
            }

        except Exception as e:
            logger.error(f"Failed to schedule reminders for booking {booking_id}: {str(e)}")
            raise

    async def _get_booking_with_relations(self, booking_id: int) -> Optional[Booking]:
        """Get booking with all related data needed for notifications."""
        return await self.booking_repo.get_by_id_with_relations(booking_id)

    async def _prepare_booking_context(self, booking: Booking) -> Dict[str, Any]:
        """
        Prepare context data for booking notifications.

        Args:
            booking: Booking instance with relations loaded

        Returns:
            Dictionary with context data for template rendering
        """
        # Format dates and times
        appointment_date = booking.scheduled_at.strftime("%d/%m/%Y")
        appointment_time = booking.scheduled_at.strftime("%H:%M")

        # Get unit information
        unit_name = booking.professional.unit.name if booking.professional.unit else "Unidade não informada"
        unit_address = booking.professional.unit.address if booking.professional.unit else "Endereço não informado"

        return {
            "user_name": booking.client.full_name,
            "salon_name": booking.professional.unit.salon.name if booking.professional.unit and booking.professional.unit.salon else "eSalão",
            "service_name": booking.service.name,
            "service_price": f"{booking.service_price:.2f}",
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "professional_name": booking.professional.user.full_name,
            "unit_name": unit_name,
            "unit_address": unit_address,
            "booking_id": str(booking.id),
            "cancellation_hours": "24",  # Default cancellation policy
            "app_url": "https://esalao.app",  # Should come from config
            "contact_phone": "(11) 99999-9999"  # Should come from config
        }

    async def _is_new_client(self, client_id: int, professional_id: int) -> bool:
        """
        Check if this is a new client for the professional.

        Args:
            client_id: ID of the client
            professional_id: ID of the professional

        Returns:
            True if this is the client's first booking with this professional
        """
        previous_bookings = await self.booking_repo.get_client_bookings_with_professional(
            client_id=client_id,
            professional_id=professional_id,
            limit=1
        )
        return len(previous_bookings) <= 1  # Current booking would be the first
