"""
Celery tasks for notification processing.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from celery import current_task
from sqlalchemy.orm import Session

from backend.app.core.celery.app import celery_app, PaymentTask
from backend.app.db.session import get_sync_db
from backend.app.db.models.payment import Payment, Refund
from backend.app.db.models.booking import Booking
from backend.app.db.models.user import User
from backend.app.domain.payments.logging_service import get_payment_logger
from backend.app.domain.notifications import (
    NotificationContext,
    notification_service,
    NotificationRequest,
    NotificationType,
)


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=PaymentTask, name="notification.send_payment_confirmation")
def send_payment_confirmation(
    self,
    payment_id: int,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send payment confirmation notification to user.

    Args:
        payment_id: Payment ID
        correlation_id: Request correlation ID

    Returns:
        Notification sending result
    """
    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get payment with related data
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            user = payment.user
            booking = payment.booking

            if not user:
                raise ValueError(f"User not found for payment {payment_id}")

            # Prepare notification context
            context = NotificationContext(
                user_name=user.name,
                user_email=user.email,
                user_phone=getattr(user, 'phone', None),
                salon_name="eSalão",  # TODO: Get from booking/salon
                payment_id=payment.external_id,
                amount=float(payment.amount),
                currency="BRL",
                payment_method=payment.method,
                booking_id=booking.external_id if booking else None,
                service_name=booking.service.name if booking and booking.service else None,
                professional_name=booking.professional.name if booking and booking.professional else None,
                booking_date=booking.start_time if booking else None,
                booking_time=booking.start_time.strftime("%H:%M") if booking else None,
            )

            # Send notification using service
            request = NotificationRequest(
                template_name="payment_confirmation",
                context=context,
                types=[NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP],
                correlation_id=correlation_id,
            )

            result = notification_service.send_notification(request)

            # Log notification attempt
            payment_logger.log(
                log_type="notification_sent",
                message=f"Payment confirmation notification sent to {user.email}",
                level="INFO",
                payment_id=payment_id,
                user_id=user.id,
                booking_id=booking.id if booking else None,
                correlation_id=correlation_id,
                request_data={
                    "notification_id": result.notification_id,
                    "status": result.status,
                    "types_sent": [t.value for t in result.types_sent],
                },
            )

            # TODO: Remove after integrating with actual notification service
            logger.info(f"Payment confirmation notification sent for payment {payment_id}")

            return {
                "status": result.status,
                "notification_id": result.notification_id,
                "payment_id": payment_id,
                "user_email": user.email,
                "notification_type": "payment_confirmation",
                "types_sent": [t.value for t in result.types_sent],
                "types_failed": [t.value for t in result.types_failed],
            }

        except Exception as exc:
            payment_logger.log_provider_error(
                provider="notification_service",
                operation="send_payment_confirmation",
                error=exc,
                payment_id=payment_id,
                correlation_id=correlation_id,
                retry_count=self.request.retries,
            )

            if self.request.retries < self.max_retries:
                retry_delay = 30 * (2 ** self.request.retries)  # 30s, 60s, 120s
                raise self.retry(countdown=retry_delay, exc=exc)

            raise


@celery_app.task(bind=True, base=PaymentTask, name="notification.send_payment_failed")
def send_payment_failed_notification(
    self,
    payment_id: int,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send payment failure notification to user.

    Args:
        payment_id: Payment ID
        correlation_id: Request correlation ID

    Returns:
        Notification sending result
    """
    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get payment with related data
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            user = payment.user
            booking = payment.booking

            if not user:
                raise ValueError(f"User not found for payment {payment_id}")

            # Prepare notification context
            context = NotificationContext(
                user_name=user.name,
                user_email=user.email,
                user_phone=getattr(user, 'phone', None),
                salon_name="eSalão",
                payment_id=payment.external_id,
                amount=float(payment.amount),
                currency="BRL",
                payment_method=payment.method,
                booking_id=booking.external_id if booking else None,
                service_name=booking.service.name if booking and booking.service else None,
            )

            # Send notification using service
            request = NotificationRequest(
                template_name="payment_failed",
                context=context,
                types=[NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH, NotificationType.IN_APP],
                correlation_id=correlation_id,
            )

            result = notification_service.send_notification(request)

            # Log notification attempt
            payment_logger.log(
                log_type="notification_sent",
                message=f"Payment failure notification sent to {user.email}",
                level="WARNING",
                payment_id=payment_id,
                user_id=user.id,
                booking_id=booking.id if booking else None,
                correlation_id=correlation_id,
                request_data={
                    "notification_id": result.notification_id,
                    "status": result.status,
                    "types_sent": [t.value for t in result.types_sent],
                },
            )

            # TODO: Remove after integrating with actual notification service
            logger.warning(f"Payment failure notification sent for payment {payment_id}")

            return {
                "status": result.status,
                "notification_id": result.notification_id,
                "payment_id": payment_id,
                "user_email": user.email,
                "notification_type": "payment_failed",
                "types_sent": [t.value for t in result.types_sent],
                "types_failed": [t.value for t in result.types_failed],
            }

        except Exception as exc:
            payment_logger.log_provider_error(
                provider="notification_service",
                operation="send_payment_failed",
                error=exc,
                payment_id=payment_id,
                correlation_id=correlation_id,
                retry_count=self.request.retries,
            )

            if self.request.retries < self.max_retries:
                retry_delay = 30 * (2 ** self.request.retries)
                raise self.retry(countdown=retry_delay, exc=exc)

            raise


@celery_app.task(bind=True, base=PaymentTask, name="notification.send_refund_confirmation")
def send_refund_confirmation(
    self,
    refund_id: int,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send refund confirmation notification to user.

    Args:
        refund_id: Refund ID
        correlation_id: Request correlation ID

    Returns:
        Notification sending result
    """
    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get refund with related data
            refund = db.query(Refund).filter(Refund.id == refund_id).first()
            if not refund:
                raise ValueError(f"Refund {refund_id} not found")

            payment = refund.payment
            user = payment.user if payment else None
            booking = payment.booking if payment else None

            if not user:
                raise ValueError(f"User not found for refund {refund_id}")

            # Prepare notification context
            context = NotificationContext(
                user_name=user.name,
                user_email=user.email,
                user_phone=getattr(user, 'phone', None),
                salon_name="eSalão",
                refund_id=refund.external_id,
                payment_id=payment.external_id if payment else None,
                refund_amount=float(refund.amount),
                currency="BRL",
                refund_reason=refund.reason,
                booking_id=booking.external_id if booking else None,
            )

            # Send notification using service
            request = NotificationRequest(
                template_name="refund_confirmation",
                context=context,
                types=[NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP],
                correlation_id=correlation_id,
            )

            result = notification_service.send_notification(request)

            # Log notification attempt
            payment_logger.log(
                log_type="notification_sent",
                message=f"Refund confirmation notification sent to {user.email}",
                level="INFO",
                payment_id=payment.id if payment else None,
                refund_id=refund_id,
                user_id=user.id,
                booking_id=booking.id if booking else None,
                correlation_id=correlation_id,
                request_data={
                    "notification_id": result.notification_id,
                    "status": result.status,
                    "types_sent": [t.value for t in result.types_sent],
                },
            )

            # TODO: Remove after integrating with actual notification service
            logger.info(f"Refund confirmation notification sent for refund {refund_id}")

            return {
                "status": result.status,
                "notification_id": result.notification_id,
                "refund_id": refund_id,
                "user_email": user.email,
                "notification_type": "refund_confirmation",
                "types_sent": [t.value for t in result.types_sent],
                "types_failed": [t.value for t in result.types_failed],
            }

        except Exception as exc:
            payment_logger.log_provider_error(
                provider="notification_service",
                operation="send_refund_confirmation",
                error=exc,
                refund_id=refund_id,
                correlation_id=correlation_id,
                retry_count=self.request.retries,
            )

            if self.request.retries < self.max_retries:
                retry_delay = 30 * (2 ** self.request.retries)
                raise self.retry(countdown=retry_delay, exc=exc)

            raise


@celery_app.task(bind=True, base=PaymentTask, name="notification.send_booking_reminder")
def send_booking_reminder(
    self,
    booking_id: int,
    hours_before: int = 24,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send booking reminder notification to user.

    Args:
        booking_id: Booking ID
        hours_before: Hours before booking to send reminder
        correlation_id: Request correlation ID

    Returns:
        Notification sending result
    """
    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get booking with related data
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            user = booking.user
            if not user:
                raise ValueError(f"User not found for booking {booking_id}")

            # Prepare notification data
            notification_data = {
                "user_email": user.email,
                "user_name": user.name,
                "booking_id": booking.external_id,
                "service_name": booking.service.name if booking.service else "Service",
                "professional_name": booking.professional.name if booking.professional else "Professional",
                "booking_date": booking.start_time.isoformat(),
                "booking_time": booking.start_time.strftime("%H:%M"),
                "salon_name": booking.salon.name if booking.salon else "Salon",
                "salon_address": booking.salon.address if booking.salon else "Address TBD",
                "hours_before": hours_before,
            }

            # Log notification attempt
            payment_logger.log(
                log_type="notification_sent",
                message=f"Booking reminder sent to {user.email} for booking {booking.external_id}",
                level="INFO",
                booking_id=booking_id,
                user_id=user.id,
                correlation_id=correlation_id,
                request_data=notification_data,
            )

            # TODO: Integrate with actual notification service
            logger.info(f"Booking reminder sent for booking {booking_id}")

            return {
                "status": "sent",
                "booking_id": booking_id,
                "user_email": user.email,
                "notification_type": "booking_reminder",
                "hours_before": hours_before,
            }

        except Exception as exc:
            payment_logger.log_provider_error(
                provider="notification_service",
                operation="send_booking_reminder",
                error=exc,
                booking_id=booking_id,
                correlation_id=correlation_id,
                retry_count=self.request.retries,
            )

            if self.request.retries < self.max_retries:
                retry_delay = 30 * (2 ** self.request.retries)
                raise self.retry(countdown=retry_delay, exc=exc)

            raise
