"""
Notification service for sending various types of notifications.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.app.domain.notifications.templates import (
    NotificationTemplate,
    NotificationContext,
    NotificationType,
    NotificationPriority,
    NotificationTemplateRegistry,
)


logger = logging.getLogger(__name__)


@dataclass
class NotificationRequest:
    """Request to send a notification."""

    template_name: str
    context: NotificationContext
    types: List[NotificationType]
    priority: Optional[NotificationPriority] = None
    send_immediately: bool = True
    scheduled_time: Optional[datetime] = None
    correlation_id: Optional[str] = None


@dataclass
class NotificationResult:
    """Result of notification sending operation."""

    notification_id: str
    status: str  # sent, failed, queued, scheduled
    types_sent: List[NotificationType]
    types_failed: List[NotificationType]
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def get_channel_type(self) -> NotificationType:
        """Get the notification type this channel handles."""
        pass

    @abstractmethod
    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: NotificationContext,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Send notification through this channel.

        Args:
            recipient: Recipient identifier (email, phone, etc.)
            subject: Notification subject/title
            body: Notification body content
            context: Full notification context
            correlation_id: Request correlation ID

        Returns:
            True if sent successfully, False otherwise
        """
        pass


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel."""

    def get_channel_type(self) -> NotificationType:
        return NotificationType.EMAIL

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: NotificationContext,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Send email notification."""
        try:
            # TODO: Integrate with actual email service (SendGrid, AWS SES, etc.)
            logger.info(f"Sending email to {recipient}: {subject}")
            logger.debug(f"Email body: {body}")

            # Simulate email sending
            # In real implementation, this would call email service API

            return True

        except Exception as exc:
            logger.error(f"Failed to send email to {recipient}: {exc}")
            return False


class SMSNotificationChannel(NotificationChannel):
    """SMS notification channel."""

    def get_channel_type(self) -> NotificationType:
        return NotificationType.SMS

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: NotificationContext,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Send SMS notification."""
        try:
            # TODO: Integrate with SMS service (Twilio, AWS SNS, etc.)
            logger.info(f"Sending SMS to {recipient}: {subject}")

            # For SMS, we typically send a shorter version
            sms_body = f"{subject}\n\n{body[:150]}..." if len(body) > 150 else f"{subject}\n\n{body}"
            logger.debug(f"SMS body: {sms_body}")

            # Simulate SMS sending
            # In real implementation, this would call SMS service API

            return True

        except Exception as exc:
            logger.error(f"Failed to send SMS to {recipient}: {exc}")
            return False


class PushNotificationChannel(NotificationChannel):
    """Push notification channel."""

    def get_channel_type(self) -> NotificationType:
        return NotificationType.PUSH

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: NotificationContext,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Send push notification."""
        try:
            # TODO: Integrate with push notification service (Firebase, OneSignal, etc.)
            logger.info(f"Sending push notification to {recipient}: {subject}")

            # For push notifications, we send a shorter body
            push_body = body[:100] + "..." if len(body) > 100 else body
            logger.debug(f"Push body: {push_body}")

            # Simulate push notification sending
            # In real implementation, this would call push service API

            return True

        except Exception as exc:
            logger.error(f"Failed to send push notification to {recipient}: {exc}")
            return False


class InAppNotificationChannel(NotificationChannel):
    """In-app notification channel."""

    def get_channel_type(self) -> NotificationType:
        return NotificationType.IN_APP

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: NotificationContext,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Send in-app notification."""
        try:
            # TODO: Store in database for in-app display
            logger.info(f"Creating in-app notification for {recipient}: {subject}")
            logger.debug(f"In-app body: {body}")

            # In real implementation, this would:
            # 1. Store notification in database
            # 2. Send real-time update via WebSocket
            # 3. Update notification badge counts

            return True

        except Exception as exc:
            logger.error(f"Failed to create in-app notification for {recipient}: {exc}")
            return False


class NotificationService:
    """Service for sending notifications through various channels."""

    def __init__(self):
        self.channels: Dict[NotificationType, NotificationChannel] = {
            NotificationType.EMAIL: EmailNotificationChannel(),
            NotificationType.SMS: SMSNotificationChannel(),
            NotificationType.PUSH: PushNotificationChannel(),
            NotificationType.IN_APP: InAppNotificationChannel(),
        }

    def send_notification(self, request: NotificationRequest) -> NotificationResult:
        """
        Send notification using specified template and channels.

        Args:
            request: Notification request

        Returns:
            Notification result with status and details
        """
        notification_id = f"notif_{datetime.utcnow().timestamp()}"

        try:
            # Get template
            template = NotificationTemplateRegistry.get_template(request.template_name)

            # Generate content
            subject = template.get_subject(request.context)
            body = template.get_body(request.context)

            # Determine priority
            priority = request.priority or template.get_priority()

            # Filter supported types
            supported_types = template.get_supported_types()
            types_to_send = [t for t in request.types if t in supported_types]

            if not types_to_send:
                return NotificationResult(
                    notification_id=notification_id,
                    status="failed",
                    types_sent=[],
                    types_failed=request.types,
                    error_message="No supported notification types",
                )

            # Send through each channel
            types_sent = []
            types_failed = []

            for notification_type in types_to_send:
                channel = self.channels.get(notification_type)
                if not channel:
                    types_failed.append(notification_type)
                    continue

                # Determine recipient based on type
                recipient = self._get_recipient_for_type(
                    notification_type,
                    request.context
                )

                if not recipient:
                    types_failed.append(notification_type)
                    continue

                # Send notification
                success = channel.send(
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    context=request.context,
                    correlation_id=request.correlation_id,
                )

                if success:
                    types_sent.append(notification_type)
                else:
                    types_failed.append(notification_type)

            # Determine overall status
            if types_sent and not types_failed:
                status = "sent"
            elif types_sent and types_failed:
                status = "partial"
            else:
                status = "failed"

            return NotificationResult(
                notification_id=notification_id,
                status=status,
                types_sent=types_sent,
                types_failed=types_failed,
                sent_at=datetime.utcnow(),
            )

        except Exception as exc:
            logger.error(f"Failed to send notification: {exc}")
            return NotificationResult(
                notification_id=notification_id,
                status="failed",
                types_sent=[],
                types_failed=request.types,
                error_message=str(exc),
            )

    def _get_recipient_for_type(
        self,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> Optional[str]:
        """Get recipient identifier for notification type."""
        if notification_type == NotificationType.EMAIL:
            return context.user_email
        elif notification_type == NotificationType.SMS:
            return context.user_phone
        elif notification_type in [NotificationType.PUSH, NotificationType.IN_APP]:
            # For push and in-app, we use email as user identifier
            return context.user_email
        return None

    def register_channel(
        self,
        notification_type: NotificationType,
        channel: NotificationChannel,
    ) -> None:
        """Register a custom notification channel."""
        self.channels[notification_type] = channel

    def test_notification(
        self,
        notification_type: NotificationType,
        recipient: str,
    ) -> bool:
        """Test a notification channel."""
        channel = self.channels.get(notification_type)
        if not channel:
            return False

        # Create test context
        context = NotificationContext(
            user_name="Teste",
            user_email="teste@exemplo.com",
            salon_name="Salão Teste",
        )

        return channel.send(
            recipient=recipient,
            subject="Teste de Notificação",
            body="Esta é uma notificação de teste do sistema eSalão.",
            context=context,
            correlation_id="test",
        )


# Global notification service instance
notification_service = NotificationService()


def send_payment_confirmation(
    context: NotificationContext,
    correlation_id: Optional[str] = None,
) -> NotificationResult:
    """Send payment confirmation notification."""
    request = NotificationRequest(
        template_name="payment_confirmation",
        context=context,
        types=[NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP],
        correlation_id=correlation_id,
    )
    return notification_service.send_notification(request)


def send_payment_failed(
    context: NotificationContext,
    correlation_id: Optional[str] = None,
) -> NotificationResult:
    """Send payment failed notification."""
    request = NotificationRequest(
        template_name="payment_failed",
        context=context,
        types=[NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH, NotificationType.IN_APP],
        correlation_id=correlation_id,
    )
    return notification_service.send_notification(request)


def send_refund_confirmation(
    context: NotificationContext,
    correlation_id: Optional[str] = None,
) -> NotificationResult:
    """Send refund confirmation notification."""
    request = NotificationRequest(
        template_name="refund_confirmation",
        context=context,
        types=[NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP],
        correlation_id=correlation_id,
    )
    return notification_service.send_notification(request)


def send_booking_reminder(
    context: NotificationContext,
    correlation_id: Optional[str] = None,
) -> NotificationResult:
    """Send booking reminder notification."""
    request = NotificationRequest(
        template_name="booking_reminder",
        context=context,
        types=[NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH],
        correlation_id=correlation_id,
    )
    return notification_service.send_notification(request)
