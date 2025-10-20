"""
Waitlist notification integration service.

This service integrates the notification system with waitlist events,
automatically sending notifications when slots become available,
waitlist positions change, or waitlist entries expire.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.user import UserRepository
from backend.app.db.repositories.service import ServiceRepository
from backend.app.db.repositories.professional import ProfessionalRepository
from backend.app.services.notifications import NotificationService
from backend.app.db.models.notifications import NotificationEventType, NotificationPriority


logger = logging.getLogger(__name__)


class WaitlistNotificationService:
    """Service for handling waitlist-related notifications."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the waitlist notification service.

        Args:
            session: Database session
        """
        self.session = session
        self.notification_service = NotificationService(session)
        self.user_repo = UserRepository(session)
        self.service_repo = ServiceRepository(session)
        self.professional_repo = ProfessionalRepository(session)

    async def notify_slot_available(
        self,
        user_id: int,
        waitlist_id: int,
        service_id: int,
        professional_id: int,
        available_slot: datetime,
        expiry_time: datetime,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send slot available notification to waitlist user.

        Args:
            user_id: ID of the user on the waitlist
            waitlist_id: ID of the waitlist entry
            service_id: ID of the service
            professional_id: ID of the professional
            available_slot: Available appointment time
            expiry_time: When the slot offer expires
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get related data
            user = await self.user_repo.get_by_id(user_id)
            service = await self.service_repo.get_by_id(service_id)
            professional = await self.professional_repo.get_by_id_with_user(professional_id)

            if not all([user, service, professional]):
                raise ValueError("Required data not found for waitlist notification")

            # Prepare context data
            context = await self._prepare_slot_available_context(
                user=user,
                service=service,
                professional=professional,
                available_slot=available_slot,
                expiry_time=expiry_time,
                waitlist_id=waitlist_id
            )

            # Send notification with high priority (time-sensitive)
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.WAITLIST_SLOT_AVAILABLE.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"waitlist_slot_{waitlist_id}_{user_id}"
            )

            logger.info(f"Slot available notification sent to user {user_id} for waitlist {waitlist_id}")

            return {
                "user_id": user_id,
                "waitlist_id": waitlist_id,
                "available_slot": available_slot.isoformat(),
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send slot available notification for user {user_id}: {str(e)}")
            raise

    async def notify_waitlist_position_update(
        self,
        user_id: int,
        waitlist_id: int,
        new_position: int,
        estimated_wait_time: Optional[timedelta] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send waitlist position update notification.

        Args:
            user_id: ID of the user on the waitlist
            waitlist_id: ID of the waitlist entry
            new_position: New position in the waitlist
            estimated_wait_time: Estimated time until slot becomes available
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Only notify for significant position changes (top 5 or moved up significantly)
            if new_position > 5:
                return {"user_id": user_id, "notifications_queued": 0}

            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # TODO: Get waitlist details from waitlist service
            # waitlist_service = WaitlistService(self.session)
            # waitlist_entry = await waitlist_service.get_waitlist_entry(waitlist_id)

            # Prepare context data
            context = await self._prepare_position_update_context(
                user=user,
                waitlist_id=waitlist_id,
                new_position=new_position,
                estimated_wait_time=estimated_wait_time
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.WAITLIST_POSITION_UPDATE.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"waitlist_position_{waitlist_id}_{new_position}"
            )

            logger.info(f"Waitlist position update notification sent to user {user_id}: position {new_position}")

            return {
                "user_id": user_id,
                "waitlist_id": waitlist_id,
                "new_position": new_position,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send waitlist position notification for user {user_id}: {str(e)}")
            raise

    async def notify_waitlist_expiry_warning(
        self,
        user_id: int,
        waitlist_id: int,
        expiry_date: datetime,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send waitlist expiry warning notification.

        Args:
            user_id: ID of the user on the waitlist
            waitlist_id: ID of the waitlist entry
            expiry_date: When the waitlist entry expires
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # TODO: Get waitlist details from waitlist service
            # waitlist_service = WaitlistService(self.session)
            # waitlist_entry = await waitlist_service.get_waitlist_entry(waitlist_id)

            # Prepare context data
            context = await self._prepare_expiry_warning_context(
                user=user,
                waitlist_id=waitlist_id,
                expiry_date=expiry_date
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.WAITLIST_EXPIRY_WARNING.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"waitlist_expiry_{waitlist_id}"
            )

            logger.info(f"Waitlist expiry warning sent to user {user_id} for waitlist {waitlist_id}")

            return {
                "user_id": user_id,
                "waitlist_id": waitlist_id,
                "expiry_date": expiry_date.isoformat(),
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send waitlist expiry warning for user {user_id}: {str(e)}")
            raise

    async def notify_waitlist_expired(
        self,
        user_id: int,
        waitlist_id: int,
        service_id: int,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send waitlist expired notification.

        Args:
            user_id: ID of the user whose waitlist expired
            waitlist_id: ID of the expired waitlist entry
            service_id: ID of the service
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get related data
            user = await self.user_repo.get_by_id(user_id)
            service = await self.service_repo.get_by_id(service_id)

            if not all([user, service]):
                raise ValueError("Required data not found for waitlist expiry notification")

            # Prepare context data
            context = await self._prepare_expired_context(
                user=user,
                service=service,
                waitlist_id=waitlist_id
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.WAITLIST_EXPIRED.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"waitlist_expired_{waitlist_id}"
            )

            logger.info(f"Waitlist expired notification sent to user {user_id} for waitlist {waitlist_id}")

            return {
                "user_id": user_id,
                "waitlist_id": waitlist_id,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send waitlist expired notification for user {user_id}: {str(e)}")
            raise

    async def notify_waitlist_batch_slots_available(
        self,
        notifications: List[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send batch notifications for multiple slot availability.

        Args:
            notifications: List of notification data dictionaries
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with batch notification results
        """
        try:
            total_queued = 0
            successful_notifications = []
            failed_notifications = []

            for notification_data in notifications:
                try:
                    result = await self.notify_slot_available(
                        user_id=notification_data["user_id"],
                        waitlist_id=notification_data["waitlist_id"],
                        service_id=notification_data["service_id"],
                        professional_id=notification_data["professional_id"],
                        available_slot=notification_data["available_slot"],
                        expiry_time=notification_data["expiry_time"],
                        correlation_id=f"{correlation_id}_batch_{notification_data['waitlist_id']}" if correlation_id else None
                    )

                    total_queued += result["notifications_queued"]
                    successful_notifications.append({
                        "user_id": notification_data["user_id"],
                        "waitlist_id": notification_data["waitlist_id"]
                    })

                except Exception as e:
                    logger.error(f"Failed to send batch notification for waitlist {notification_data.get('waitlist_id')}: {str(e)}")
                    failed_notifications.append({
                        "user_id": notification_data.get("user_id"),
                        "waitlist_id": notification_data.get("waitlist_id"),
                        "error": str(e)
                    })

            logger.info(f"Batch waitlist notifications processed: {len(successful_notifications)} successful, {len(failed_notifications)} failed")

            return {
                "total_notifications": len(notifications),
                "successful_count": len(successful_notifications),
                "failed_count": len(failed_notifications),
                "total_queued": total_queued,
                "successful_notifications": successful_notifications,
                "failed_notifications": failed_notifications
            }

        except Exception as e:
            logger.error(f"Failed to process batch waitlist notifications: {str(e)}")
            raise

    async def _prepare_slot_available_context(
        self,
        user,
        service,
        professional,
        available_slot: datetime,
        expiry_time: datetime,
        waitlist_id: int
    ) -> Dict[str, Any]:
        """Prepare context data for slot available notifications."""
        minutes_to_expiry = int((expiry_time - datetime.now()).total_seconds() / 60)

        context = {
            "user_name": user.full_name,
            "service_name": service.name,
            "professional_name": professional.user.full_name,
            "available_date": available_slot.strftime("%d/%m/%Y"),
            "available_time": available_slot.strftime("%H:%M"),
            "expiry_date": expiry_time.strftime("%d/%m/%Y"),
            "expiry_time": expiry_time.strftime("%H:%M"),
            "minutes_to_expiry": str(max(0, minutes_to_expiry)),
            "booking_url": f"https://esalao.app/book/waitlist/{waitlist_id}",  # Should come from config
            "app_url": "https://esalao.app",  # Should come from config
        }

        return context

    async def _prepare_position_update_context(
        self,
        user,
        waitlist_id: int,
        new_position: int,
        estimated_wait_time: Optional[timedelta]
    ) -> Dict[str, Any]:
        """Prepare context data for position update notifications."""
        context = {
            "user_name": user.full_name,
            "new_position": str(new_position),
            "position_text": "primeiro" if new_position == 1 else f"{new_position}º",
            "app_url": "https://esalao.app",  # Should come from config
        }

        if estimated_wait_time:
            if estimated_wait_time.days > 0:
                context["estimated_wait"] = f"{estimated_wait_time.days} dias"
            else:
                hours = estimated_wait_time.seconds // 3600
                context["estimated_wait"] = f"{hours} horas" if hours > 0 else "algumas horas"
        else:
            context["estimated_wait"] = "em breve"

        return context

    async def _prepare_expiry_warning_context(
        self,
        user,
        waitlist_id: int,
        expiry_date: datetime
    ) -> Dict[str, Any]:
        """Prepare context data for expiry warning notifications."""
        days_until_expiry = (expiry_date - datetime.now()).days

        context = {
            "user_name": user.full_name,
            "expiry_date": expiry_date.strftime("%d/%m/%Y"),
            "days_until_expiry": str(max(0, days_until_expiry)),
            "app_url": "https://esalao.app",  # Should come from config
        }

        return context

    async def _prepare_expired_context(
        self,
        user,
        service,
        waitlist_id: int
    ) -> Dict[str, Any]:
        """Prepare context data for expired waitlist notifications."""
        context = {
            "user_name": user.full_name,
            "service_name": service.name,
            "new_booking_url": f"https://esalao.app/book/{service.id}",  # Should come from config
            "app_url": "https://esalao.app",  # Should come from config
        }

        return context
