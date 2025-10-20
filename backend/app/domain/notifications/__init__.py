"""
Notification system for payment and booking events.
"""

from backend.app.domain.notifications.templates import (
    NotificationContext,
    NotificationType,
    NotificationPriority,
    NotificationTemplateRegistry,
    get_payment_confirmation_template,
    get_payment_failed_template,
    get_refund_confirmation_template,
    get_booking_reminder_template,
    get_booking_cancelled_template,
    get_welcome_template,
)

from backend.app.domain.notifications.service import (
    NotificationService,
    NotificationRequest,
    NotificationResult,
    notification_service,
    send_payment_confirmation,
    send_payment_failed,
    send_refund_confirmation,
    send_booking_reminder,
)

__all__ = [
    # Templates
    "NotificationContext",
    "NotificationType",
    "NotificationPriority",
    "NotificationTemplateRegistry",
    "get_payment_confirmation_template",
    "get_payment_failed_template",
    "get_refund_confirmation_template",
    "get_booking_reminder_template",
    "get_booking_cancelled_template",
    "get_welcome_template",

    # Service
    "NotificationService",
    "NotificationRequest",
    "NotificationResult",
    "notification_service",
    "send_payment_confirmation",
    "send_payment_failed",
    "send_refund_confirmation",
    "send_booking_reminder",
]
