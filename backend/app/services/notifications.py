"""
Advanced notification service for the eSalão application.

This service handles notification delivery across multiple channels,
template rendering, preference management, and delivery tracking.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from jinja2 import Template, Environment, DictLoader
import json

from backend.app.db.repositories.notifications import NotificationRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.db.models.notifications import (
    NotificationChannel, NotificationEventType, NotificationPriority,
    NotificationStatus, NotificationQueue, NotificationTemplate
)
from backend.app.db.models.user import User
from backend.app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError

logger = logging.getLogger(__name__)


class NotificationChannelHandler:
    """Base class for notification channel handlers."""

    def __init__(self, channel: NotificationChannel):
        self.channel = channel

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send notification through this channel."""
        raise NotImplementedError("Subclasses must implement send method")

    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format for this channel."""
        raise NotImplementedError("Subclasses must implement validate_recipient method")


class EmailHandler(NotificationChannelHandler):
    """Email notification handler."""

    def __init__(self):
        super().__init__(NotificationChannel.EMAIL)

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email notification."""
        # TODO: Integrate with actual email service (SendGrid, AWS SES, etc.)
        logger.info(f"Sending email to {recipient}: {subject}")

        # Simulate email sending
        await asyncio.sleep(0.1)

        return {
            "external_id": f"email_{datetime.now().timestamp()}",
            "status": "sent",
            "provider_response": {
                "message": "Email sent successfully",
                "recipient": recipient,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate email address format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, recipient))


class SMSHandler(NotificationChannelHandler):
    """SMS notification handler."""

    def __init__(self):
        super().__init__(NotificationChannel.SMS)

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send SMS notification."""
        # TODO: Integrate with SMS service (Twilio, AWS SNS, etc.)
        logger.info(f"Sending SMS to {recipient}: {body[:50]}...")

        # Simulate SMS sending
        await asyncio.sleep(0.1)

        return {
            "external_id": f"sms_{datetime.now().timestamp()}",
            "status": "sent",
            "provider_response": {
                "message": "SMS sent successfully",
                "recipient": recipient,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate phone number format."""
        import re
        # Simple phone validation - can be enhanced
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(phone_pattern, recipient.replace(' ', '').replace('-', '')))


class PushHandler(NotificationChannelHandler):
    """Push notification handler."""

    def __init__(self):
        super().__init__(NotificationChannel.PUSH)

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send push notification."""
        # TODO: Integrate with push service (Firebase, Apple Push, etc.)
        logger.info(f"Sending push to {recipient}: {subject}")

        # Simulate push sending
        await asyncio.sleep(0.1)

        return {
            "external_id": f"push_{datetime.now().timestamp()}",
            "status": "sent",
            "provider_response": {
                "message": "Push notification sent successfully",
                "device_token": recipient,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate device token format."""
        # Simple validation - device tokens are usually 64+ character hex strings
        return len(recipient) >= 64 and all(c in '0123456789abcdefABCDEF' for c in recipient)


class InAppHandler(NotificationChannelHandler):
    """In-app notification handler."""

    def __init__(self):
        super().__init__(NotificationChannel.IN_APP)

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send in-app notification."""
        # For in-app notifications, we just store them in the database
        # The frontend will poll or use websockets to fetch them
        logger.info(f"Creating in-app notification for user {recipient}: {subject}")

        return {
            "external_id": f"inapp_{datetime.now().timestamp()}",
            "status": "delivered",  # In-app notifications are immediately "delivered"
            "provider_response": {
                "message": "In-app notification created successfully",
                "user_id": recipient,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate user ID format."""
        try:
            int(recipient)
            return True
        except ValueError:
            return False


class WhatsAppHandler(NotificationChannelHandler):
    """WhatsApp notification handler."""

    def __init__(self):
        super().__init__(NotificationChannel.WHATSAPP)

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send WhatsApp notification."""
        # TODO: Integrate with WhatsApp Business API
        logger.info(f"Sending WhatsApp to {recipient}: {body[:50]}...")

        # Simulate WhatsApp sending
        await asyncio.sleep(0.1)

        return {
            "external_id": f"whatsapp_{datetime.now().timestamp()}",
            "status": "sent",
            "provider_response": {
                "message": "WhatsApp sent successfully",
                "recipient": recipient,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate WhatsApp number format (same as phone)."""
        return SMSHandler().validate_recipient(recipient)


class NotificationService:
    """Advanced notification service with multi-channel support."""

    def __init__(
        self,
        notification_repo: NotificationRepository,
        user_repo: UserRepository
    ):
        self.notification_repo = notification_repo
        self.user_repo = user_repo

        # Initialize channel handlers
        self.handlers = {
            NotificationChannel.EMAIL: EmailHandler(),
            NotificationChannel.SMS: SMSHandler(),
            NotificationChannel.PUSH: PushHandler(),
            NotificationChannel.IN_APP: InAppHandler(),
            NotificationChannel.WHATSAPP: WhatsAppHandler(),
        }

        # Jinja2 environment for template rendering
        self.jinja_env = Environment(
            loader=DictLoader({}),
            autoescape=True
        )

    # ==================== Template Management ====================

    async def create_template(
        self,
        name: str,
        event_type: NotificationEventType,
        channel: NotificationChannel,
        subject_template: Optional[str],
        body_template: str,
        variables: Dict[str, str],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        locale: str = "pt_BR"
    ) -> NotificationTemplate:
        """Create a new notification template."""
        # Validate template syntax
        try:
            if subject_template:
                Template(subject_template)
            Template(body_template)
        except Exception as e:
            raise ValidationError(f"Invalid template syntax: {str(e)}")

        return await self.notification_repo.create_template(
            name=name,
            event_type=event_type,
            channel=channel,
            subject=subject_template,
            body_template=body_template,
            variables=variables,
            priority=priority,
            locale=locale
        )

    async def render_template(
        self,
        template: NotificationTemplate,
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Render notification template with context data."""
        try:
            rendered = {}

            if template.subject:
                subject_template = Template(template.subject)
                rendered["subject"] = subject_template.render(**context)

            body_template = Template(template.body_template)
            rendered["body"] = body_template.render(**context)

            return rendered
        except Exception as e:
            raise ValidationError(f"Template rendering failed: {str(e)}")

    # ==================== Preference Management ====================

    async def setup_user_preferences(self, user_id: int) -> List:
        """Set up default notification preferences for a new user."""
        return await self.notification_repo.setup_default_preferences(user_id)

    async def update_user_preference(
        self,
        user_id: int,
        event_type: NotificationEventType,
        channel: NotificationChannel,
        enabled: bool,
        advance_minutes: Optional[int] = None,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None
    ):
        """Update a user's notification preference."""
        # Validate quiet hours format
        if quiet_hours_start and not self._validate_time_format(quiet_hours_start):
            raise ValidationError("Invalid quiet_hours_start format. Use HH:MM")
        if quiet_hours_end and not self._validate_time_format(quiet_hours_end):
            raise ValidationError("Invalid quiet_hours_end format. Use HH:MM")

        return await self.notification_repo.set_user_preference(
            user_id=user_id,
            event_type=event_type,
            channel=channel,
            enabled=enabled,
            advance_minutes=advance_minutes,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end
        )

    def _validate_time_format(self, time_str: str) -> bool:
        """Validate HH:MM time format."""
        try:
            hour, minute = time_str.split(':')
            return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59
        except (ValueError, IndexError):
            return False

    async def get_user_preferences(
        self,
        user_id: int,
        event_type: Optional[NotificationEventType] = None
    ):
        """Get user notification preferences."""
        return await self.notification_repo.get_user_preferences(
            user_id=user_id,
            event_type=event_type
        )

    # ==================== Notification Sending ====================

    async def send_notification(
        self,
        user_id: int,
        event_type: NotificationEventType,
        context_data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        scheduled_at: Optional[datetime] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send notification to user across specified or preferred channels."""
        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # Determine channels to use
        if channels is None:
            channels = await self.notification_repo.get_enabled_channels_for_user(
                user_id, event_type
            )

        if not channels:
            logger.info(f"No enabled channels for user {user_id} and event {event_type}")
            return {"message": "No enabled channels", "notifications_queued": 0}

        # Queue notifications for each channel
        queued_notifications = []
        for channel in channels:
            try:
                notification = await self._queue_notification_for_channel(
                    user=user,
                    event_type=event_type,
                    channel=channel,
                    context_data=context_data,
                    priority=priority,
                    scheduled_at=scheduled_at,
                    correlation_id=correlation_id
                )
                queued_notifications.append(notification)
            except Exception as e:
                logger.error(f"Failed to queue notification for channel {channel}: {str(e)}")
                continue

        # If immediate sending is requested and no scheduling
        if not scheduled_at or scheduled_at <= datetime.now(timezone.utc):
            asyncio.create_task(self._process_immediate_notifications(queued_notifications))

        return {
            "message": "Notifications queued successfully",
            "notifications_queued": len(queued_notifications),
            "channels": [n.channel for n in queued_notifications]
        }

    async def _queue_notification_for_channel(
        self,
        user: User,
        event_type: NotificationEventType,
        channel: NotificationChannel,
        context_data: Dict[str, Any],
        priority: NotificationPriority,
        scheduled_at: Optional[datetime],
        correlation_id: Optional[str]
    ) -> NotificationQueue:
        """Queue a notification for a specific channel."""
        # Get template for this event type and channel
        template = await self.notification_repo.get_template(
            event_type=event_type,
            channel=channel,
            locale="pt_BR"  # TODO: Get from user preferences
        )

        if not template:
            raise NotFoundError(f"No template found for {event_type} on {channel}")

        # Prepare context with user data
        full_context = {
            **context_data,
            "user_name": user.full_name,
            "user_email": user.email,
            "user_phone": user.phone,
            "salon_name": "eSalão",  # TODO: Get from config
        }

        # Render template
        rendered = await self.render_template(template, full_context)

        # Queue notification
        return await self.notification_repo.queue_notification(
            user_id=user.id,
            template_id=template.id,
            channel=channel,
            context_data=full_context,
            subject=rendered.get("subject"),
            body=rendered["body"],
            priority=priority,
            scheduled_at=scheduled_at,
            correlation_id=correlation_id
        )

    async def _process_immediate_notifications(
        self,
        notifications: List[NotificationQueue]
    ) -> None:
        """Process notifications for immediate delivery."""
        for notification in notifications:
            try:
                await self._deliver_notification(notification)
            except Exception as e:
                logger.error(f"Failed to deliver notification {notification.id}: {str(e)}")

    async def _deliver_notification(self, notification: NotificationQueue) -> None:
        """Deliver a single notification."""
        handler = self.handlers.get(notification.channel)
        if not handler:
            raise BusinessLogicError(f"No handler for channel {notification.channel}")

        # Get recipient address
        recipient = await self._get_recipient_address(notification.user, notification.channel)
        if not recipient:
            await self.notification_repo.update_notification_status(
                notification.id,
                NotificationStatus.FAILED,
                error_message=f"No {notification.channel} address for user"
            )
            return

        # Validate recipient
        if not handler.validate_recipient(recipient):
            await self.notification_repo.update_notification_status(
                notification.id,
                NotificationStatus.FAILED,
                error_message=f"Invalid recipient format for {notification.channel}"
            )
            return

        try:
            # Send notification
            result = await handler.send(
                recipient=recipient,
                subject=notification.subject,
                body=notification.body,
                context=notification.context_data
            )

            # Update status
            await self.notification_repo.update_notification_status(
                notification.id,
                NotificationStatus.SENT,
                external_id=result.get("external_id"),
                sent_at=datetime.now(timezone.utc)
            )

            # Log delivery
            await self.notification_repo.log_notification(
                queue_id=notification.id,
                user_id=notification.user_id,
                channel=notification.channel,
                event_type=notification.template.event_type,
                status=NotificationStatus.SENT,
                subject=notification.subject,
                external_id=result.get("external_id"),
                provider_response=result.get("provider_response"),
                correlation_id=notification.correlation_id
            )

        except Exception as e:
            # Handle delivery failure
            await self.notification_repo.update_notification_status(
                notification.id,
                NotificationStatus.FAILED,
                error_message=str(e),
                increment_retry=True
            )

            # Log failure
            await self.notification_repo.log_notification(
                queue_id=notification.id,
                user_id=notification.user_id,
                channel=notification.channel,
                event_type=notification.template.event_type,
                status=NotificationStatus.FAILED,
                subject=notification.subject,
                error_message=str(e),
                correlation_id=notification.correlation_id
            )

    async def _get_recipient_address(
        self,
        user: User,
        channel: NotificationChannel
    ) -> Optional[str]:
        """Get recipient address for the specified channel."""
        if channel == NotificationChannel.EMAIL:
            return user.email
        elif channel == NotificationChannel.SMS or channel == NotificationChannel.WHATSAPP:
            return user.phone
        elif channel == NotificationChannel.IN_APP:
            return str(user.id)
        elif channel == NotificationChannel.PUSH:
            # TODO: Get device token from user device registrations
            return None  # Not implemented yet
        else:
            return None

    # ==================== Notification Processing ====================

    async def process_pending_notifications(self, limit: int = 100) -> Dict[str, int]:
        """Process pending notifications for delivery."""
        notifications = await self.notification_repo.get_pending_notifications(limit=limit)

        processed = 0
        failed = 0

        for notification in notifications:
            try:
                await self._deliver_notification(notification)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process notification {notification.id}: {str(e)}")
                failed += 1

        return {"processed": processed, "failed": failed}

    async def process_retry_notifications(self, limit: int = 50) -> Dict[str, int]:
        """Process notifications that need retry."""
        notifications = await self.notification_repo.get_notifications_for_retry(limit=limit)

        retried = 0
        failed = 0

        for notification in notifications:
            try:
                await self._deliver_notification(notification)
                retried += 1
            except Exception as e:
                logger.error(f"Failed to retry notification {notification.id}: {str(e)}")
                failed += 1

        return {"retried": retried, "failed": failed}

    # ==================== Event-Specific Helpers ====================

    async def send_booking_confirmation(
        self,
        user_id: int,
        booking_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send booking confirmation notification."""
        return await self.send_notification(
            user_id=user_id,
            event_type=NotificationEventType.BOOKING_CONFIRMED,
            context_data=booking_data,
            priority=NotificationPriority.HIGH,
            correlation_id=f"booking_{booking_data.get('booking_id')}"
        )

    async def send_booking_reminder(
        self,
        user_id: int,
        booking_data: Dict[str, Any],
        reminder_time: datetime
    ) -> Dict[str, Any]:
        """Send booking reminder notification."""
        return await self.send_notification(
            user_id=user_id,
            event_type=NotificationEventType.BOOKING_REMINDER,
            context_data=booking_data,
            priority=NotificationPriority.HIGH,
            scheduled_at=reminder_time,
            correlation_id=f"booking_reminder_{booking_data.get('booking_id')}"
        )

    async def send_payment_confirmation(
        self,
        user_id: int,
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send payment confirmation notification."""
        return await self.send_notification(
            user_id=user_id,
            event_type=NotificationEventType.PAYMENT_RECEIVED,
            context_data=payment_data,
            priority=NotificationPriority.NORMAL,
            correlation_id=f"payment_{payment_data.get('payment_id')}"
        )

    async def send_loyalty_points_earned(
        self,
        user_id: int,
        points_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send loyalty points earned notification."""
        return await self.send_notification(
            user_id=user_id,
            event_type=NotificationEventType.POINTS_EARNED,
            context_data=points_data,
            priority=NotificationPriority.LOW,
            correlation_id=f"loyalty_points_{points_data.get('transaction_id')}"
        )

    async def send_tier_upgrade(
        self,
        user_id: int,
        tier_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send loyalty tier upgrade notification."""
        return await self.send_notification(
            user_id=user_id,
            event_type=NotificationEventType.TIER_UPGRADED,
            context_data=tier_data,
            priority=NotificationPriority.HIGH,
            correlation_id=f"tier_upgrade_{user_id}"
        )

    async def send_waitlist_slot_available(
        self,
        user_id: int,
        slot_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send waitlist slot available notification."""
        return await self.send_notification(
            user_id=user_id,
            event_type=NotificationEventType.SLOT_AVAILABLE,
            context_data=slot_data,
            priority=NotificationPriority.URGENT,
            correlation_id=f"waitlist_slot_{slot_data.get('waitlist_id')}"
        )

    # ==================== Administrative Functions ====================

    async def cancel_notifications_by_correlation(
        self,
        correlation_id: str,
        reason: str = "Cancelled by user"
    ) -> int:
        """Cancel pending notifications by correlation ID."""
        return await self.notification_repo.cancel_notifications(
            correlation_id=correlation_id,
            reason=reason
        )

    async def get_notification_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification delivery statistics."""
        return await self.notification_repo.get_notification_statistics(
            start_date=start_date,
            end_date=end_date
        )

    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old notification data."""
        return await self.notification_repo.cleanup_old_notifications(
            days_to_keep=days_to_keep
        )
