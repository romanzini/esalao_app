"""
Celery tasks for payment processing.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from celery import current_task
from sqlalchemy.orm import Session

from backend.app.core.celery.app import celery_app, PaymentTask
from backend.app.db.session import get_sync_db
from backend.app.db.models.payment import Payment, PaymentStatus, Refund, RefundStatus
from backend.app.db.models.payment_log import PaymentLogType
from backend.app.domain.payments.logging_service import get_payment_logger
from backend.app.domain.payments.providers.factory import get_payment_provider


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=PaymentTask, name="payment.process_webhook")
def process_payment_webhook(
    self,
    provider: str,
    webhook_data: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process payment webhook events asynchronously.

    Args:
        provider: Payment provider name
        webhook_data: Webhook payload data
        correlation_id: Request correlation ID

    Returns:
        Processing result with status and details
    """
    task_id = current_task.request.id
    start_time = datetime.utcnow()

    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Log webhook processing start
            payment_logger.log_webhook_received(
                provider=provider,
                event_type=webhook_data.get("type", "unknown"),
                webhook_data=webhook_data,
                correlation_id=correlation_id,
            )

            # Get payment provider instance
            payment_provider = get_payment_provider(provider)

            # Extract payment information from webhook
            provider_transaction_id = webhook_data.get("id") or webhook_data.get("transaction_id")
            event_type = webhook_data.get("type") or webhook_data.get("event_type")

            if not provider_transaction_id:
                raise ValueError("No transaction ID found in webhook data")

            # Find associated payment
            payment = db.query(Payment).filter(
                Payment.provider_transaction_id == provider_transaction_id
            ).first()

            if not payment:
                logger.warning(f"Payment not found for transaction {provider_transaction_id}")
                return {"status": "ignored", "reason": "payment_not_found"}

            # Process based on event type
            old_status = payment.status

            if event_type in ["payment.succeeded", "charge.succeeded", "payment_intent.succeeded"]:
                payment.status = PaymentStatus.COMPLETED
                payment.updated_at = datetime.utcnow()

                # Log status change
                payment_logger.log_payment_updated(
                    payment=payment,
                    old_status=old_status,
                    new_status=payment.status,
                    correlation_id=correlation_id,
                )

                # Schedule payment confirmation notification
                send_payment_confirmation.delay(
                    payment_id=payment.id,
                    correlation_id=correlation_id,
                )

            elif event_type in ["payment.failed", "charge.failed", "payment_intent.payment_failed"]:
                payment.status = PaymentStatus.FAILED
                payment.updated_at = datetime.utcnow()

                # Log status change
                payment_logger.log_payment_updated(
                    payment=payment,
                    old_status=old_status,
                    new_status=payment.status,
                    correlation_id=correlation_id,
                )

                # Schedule payment failure notification
                send_payment_failed_notification.delay(
                    payment_id=payment.id,
                    correlation_id=correlation_id,
                )

            elif event_type in ["payment.canceled", "charge.dispute.created"]:
                payment.status = PaymentStatus.CANCELLED
                payment.updated_at = datetime.utcnow()

                payment_logger.log_payment_updated(
                    payment=payment,
                    old_status=old_status,
                    new_status=payment.status,
                    correlation_id=correlation_id,
                )

            db.commit()

            # Calculate processing time
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Log successful processing
            payment_logger.log_webhook_processed(
                provider=provider,
                event_type=event_type,
                payment_id=payment.id,
                correlation_id=correlation_id,
                processing_time_ms=processing_time,
            )

            return {
                "status": "processed",
                "payment_id": payment.id,
                "old_status": old_status,
                "new_status": payment.status,
                "processing_time_ms": processing_time,
            }

        except Exception as exc:
            db.rollback()

            # Log error
            payment_logger.log_provider_error(
                provider=provider,
                operation="process_webhook",
                error=exc,
                correlation_id=correlation_id,
                retry_count=self.request.retries,
            )

            # Retry logic
            if self.request.retries < self.max_retries:
                # Exponential backoff: 60s, 120s, 240s
                retry_delay = 60 * (2 ** self.request.retries)
                raise self.retry(countdown=retry_delay, exc=exc)

            raise


@celery_app.task(bind=True, base=PaymentTask, name="payment.sync_payment_status")
def sync_payment_status(
    self,
    payment_id: int,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synchronize payment status with provider.

    Args:
        payment_id: Payment ID to sync
        correlation_id: Request correlation ID

    Returns:
        Sync result with status details
    """
    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get payment
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            # Get provider
            payment_provider = get_payment_provider(payment.provider)

            # Get current status from provider
            provider_status = payment_provider.get_payment_status(
                payment.provider_transaction_id
            )

            old_status = payment.status

            # Update status if changed
            if provider_status.status != payment.status:
                payment.status = provider_status.status
                payment.updated_at = datetime.utcnow()

                payment_logger.log_payment_updated(
                    payment=payment,
                    old_status=old_status,
                    new_status=payment.status,
                    correlation_id=correlation_id,
                    context={"sync_source": "provider_api"},
                )

                db.commit()

            return {
                "status": "synced",
                "payment_id": payment_id,
                "old_status": old_status,
                "new_status": payment.status,
                "changed": old_status != payment.status,
            }

        except Exception as exc:
            # Log error and retry
            payment_logger.log_provider_error(
                provider=payment.provider if 'payment' in locals() else "unknown",
                operation="sync_payment_status",
                error=exc,
                payment_id=payment_id,
                correlation_id=correlation_id,
                retry_count=self.request.retries,
            )

            if self.request.retries < self.max_retries:
                retry_delay = 120 * (2 ** self.request.retries)  # 2, 4, 8 minutes
                raise self.retry(countdown=retry_delay, exc=exc)

            raise


@celery_app.task(bind=True, base=PaymentTask, name="payment.process_refund")
def process_refund(
    self,
    refund_id: int,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process refund request with payment provider.

    Args:
        refund_id: Refund ID to process
        correlation_id: Request correlation ID

    Returns:
        Processing result with refund status
    """
    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get refund and payment
            refund = db.query(Refund).filter(Refund.id == refund_id).first()
            if not refund:
                raise ValueError(f"Refund {refund_id} not found")

            payment = refund.payment
            if not payment:
                raise ValueError(f"Payment not found for refund {refund_id}")

            # Get provider
            payment_provider = get_payment_provider(payment.provider)

            # Create refund with provider
            refund_request = {
                "payment_id": payment.provider_transaction_id,
                "amount": refund.amount,
                "reason": refund.reason,
                "metadata": {"refund_id": refund.external_id},
            }

            provider_response = payment_provider.create_refund(refund_request)

            # Update refund with provider response
            refund.provider_refund_id = provider_response.get("refund_id")
            refund.status = RefundStatus.PROCESSING
            refund.updated_at = datetime.utcnow()

            payment_logger.log_refund_created(
                refund=refund,
                correlation_id=correlation_id,
                context={"provider_response": provider_response},
            )

            db.commit()

            return {
                "status": "processing",
                "refund_id": refund_id,
                "provider_refund_id": refund.provider_refund_id,
            }

        except Exception as exc:
            db.rollback()

            # Update refund status to failed
            if 'refund' in locals():
                refund.status = RefundStatus.FAILED
                refund.updated_at = datetime.utcnow()
                db.commit()

            payment_logger.log_provider_error(
                provider=payment.provider if 'payment' in locals() else "unknown",
                operation="process_refund",
                error=exc,
                refund_id=refund_id,
                correlation_id=correlation_id,
                retry_count=self.request.retries,
            )

            if self.request.retries < self.max_retries:
                retry_delay = 180 * (2 ** self.request.retries)  # 3, 6, 12 minutes
                raise self.retry(countdown=retry_delay, exc=exc)

            raise


@celery_app.task(bind=True, base=PaymentTask, name="payment.cleanup_expired_payments")
def cleanup_expired_payments(
    self,
    hours_old: int = 24,
) -> Dict[str, Any]:
    """
    Clean up expired pending payments.

    Args:
        hours_old: Number of hours after which pending payments expire

    Returns:
        Cleanup result with counts
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)

    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Find expired pending payments
            expired_payments = db.query(Payment).filter(
                Payment.status == PaymentStatus.PENDING,
                Payment.created_at < cutoff_time,
            ).all()

            expired_count = 0

            for payment in expired_payments:
                old_status = payment.status
                payment.status = PaymentStatus.EXPIRED
                payment.updated_at = datetime.utcnow()

                payment_logger.log_payment_updated(
                    payment=payment,
                    old_status=old_status,
                    new_status=payment.status,
                    context={"cleanup_reason": "expired"},
                )

                expired_count += 1

            db.commit()

            return {
                "status": "completed",
                "expired_count": expired_count,
                "cutoff_time": cutoff_time.isoformat(),
            }

        except Exception as exc:
            db.rollback()

            payment_logger.log_exception(
                exception=exc,
                context="cleanup_expired_payments",
            )

            raise


# Import notification tasks to avoid circular imports
from backend.app.core.celery.tasks.notification_tasks import (
    send_payment_confirmation,
    send_payment_failed_notification,
)
