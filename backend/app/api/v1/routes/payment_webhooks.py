"""
Payment webhook routes for handling payment provider notifications.

This module provides endpoints for payment providers to notify about
payment status changes, which trigger appropriate user notifications.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.services.payment_notifications import PaymentNotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payment-webhooks"])


class WebhookResponse(BaseModel):
    """Response model for webhook endpoints."""

    status: str
    payment_id: int
    message: Optional[str] = None


class PaymentFailureWebhook(BaseModel):
    """Request model for payment failure webhook."""

    failure_reason: Optional[str] = Field(None, max_length=500)
    error_code: Optional[str] = Field(None, max_length=50)
    provider_message: Optional[str] = Field(None, max_length=1000)


class RefundWebhook(BaseModel):
    """Request model for refund webhook."""

    refund_amount: Decimal = Field(..., gt=0)
    refund_reason: Optional[str] = Field(None, max_length=500)
    provider_refund_id: Optional[str] = Field(None, max_length=100)


@router.post(
    "/{payment_id}/webhook/confirmed",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment confirmation webhook",
    description="Webhook endpoint for payment provider confirmations",
)
async def payment_confirmed_webhook(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Handle payment confirmation webhook.

    This endpoint is called by payment providers when a payment
    is confirmed. It updates the payment status and sends notifications.

    Args:
        payment_id: ID of the confirmed payment
        db: Database session

    Returns:
        Webhook response indicating success or failure
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payment = await payment_service.confirm_payment(payment_id)

        # Send payment confirmation notification
        try:
            notification_service = PaymentNotificationService(db)
            result = await notification_service.notify_payment_received(
                payment_id=payment_id,
                correlation_id=f"webhook_confirmed_{payment_id}"
            )

            logger.info(f"Payment confirmation webhook processed for payment {payment_id}")

            return WebhookResponse(
                status="success",
                payment_id=payment_id,
                message=f"Notifications queued: {result.get('notifications_queued', 0)}"
            )

        except Exception as e:
            # Log notification error but don't fail the webhook
            logger.error(f"Failed to send payment confirmation notification for payment {payment_id}: {str(e)}")

            return WebhookResponse(
                status="partial_success",
                payment_id=payment_id,
                message="Payment confirmed but notification failed"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Webhook processing failed for payment {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post(
    "/{payment_id}/webhook/failed",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment failure webhook",
    description="Webhook endpoint for payment provider failures",
)
async def payment_failed_webhook(
    payment_id: int,
    failure_data: PaymentFailureWebhook,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Handle payment failure webhook.

    This endpoint is called by payment providers when a payment
    fails. It updates the payment status and sends notifications.

    Args:
        payment_id: ID of the failed payment
        failure_data: Failure details from the provider
        db: Database session

    Returns:
        Webhook response indicating success or failure
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payment = await payment_service.fail_payment(
        #     payment_id,
        #     failure_data.failure_reason,
        #     failure_data.error_code
        # )

        # Send payment failure notification
        try:
            notification_service = PaymentNotificationService(db)
            result = await notification_service.notify_payment_failed(
                payment_id=payment_id,
                failure_reason=failure_data.failure_reason,
                correlation_id=f"webhook_failed_{payment_id}"
            )

            logger.info(f"Payment failure webhook processed for payment {payment_id}")

            return WebhookResponse(
                status="success",
                payment_id=payment_id,
                message=f"Notifications queued: {result.get('notifications_queued', 0)}"
            )

        except Exception as e:
            # Log notification error but don't fail the webhook
            logger.error(f"Failed to send payment failure notification for payment {payment_id}: {str(e)}")

            return WebhookResponse(
                status="partial_success",
                payment_id=payment_id,
                message="Payment failure recorded but notification failed"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Webhook processing failed for payment {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post(
    "/{payment_id}/webhook/refund",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Refund processed webhook",
    description="Webhook endpoint for refund confirmations",
)
async def refund_processed_webhook(
    payment_id: int,
    refund_data: RefundWebhook,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Handle refund processed webhook.

    This endpoint is called by payment providers when a refund
    is processed. It updates the payment status and sends notifications.

    Args:
        payment_id: ID of the payment being refunded
        refund_data: Refund details from the provider
        db: Database session

    Returns:
        Webhook response indicating success or failure
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payment = await payment_service.record_refund(
        #     payment_id,
        #     refund_data.refund_amount,
        #     refund_data.refund_reason,
        #     refund_data.provider_refund_id
        # )

        # Send refund notification
        try:
            notification_service = PaymentNotificationService(db)
            result = await notification_service.notify_refund_processed(
                payment_id=payment_id,
                refund_amount=refund_data.refund_amount,
                refund_reason=refund_data.refund_reason,
                correlation_id=f"webhook_refund_{payment_id}"
            )

            logger.info(f"Refund webhook processed for payment {payment_id}")

            return WebhookResponse(
                status="success",
                payment_id=payment_id,
                message=f"Notifications queued: {result.get('notifications_queued', 0)}"
            )

        except Exception as e:
            # Log notification error but don't fail the webhook
            logger.error(f"Failed to send refund notification for payment {payment_id}: {str(e)}")

            return WebhookResponse(
                status="partial_success",
                payment_id=payment_id,
                message="Refund recorded but notification failed"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Webhook processing failed for payment {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post(
    "/{payment_id}/webhook/pending",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment pending webhook",
    description="Webhook endpoint for payment pending notifications",
)
async def payment_pending_webhook(
    payment_id: int,
    payment_method: str,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Handle payment pending webhook.

    This endpoint is called by payment providers when a payment
    is pending (e.g., bank slip generated, PIX code created).

    Args:
        payment_id: ID of the pending payment
        payment_method: Payment method used
        db: Database session

    Returns:
        Webhook response indicating success or failure
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payment = await payment_service.set_payment_pending(payment_id, payment_method)

        # Send payment pending notification
        try:
            notification_service = PaymentNotificationService(db)
            result = await notification_service.notify_payment_pending(
                payment_id=payment_id,
                payment_method=payment_method,
                correlation_id=f"webhook_pending_{payment_id}"
            )

            logger.info(f"Payment pending webhook processed for payment {payment_id}")

            return WebhookResponse(
                status="success",
                payment_id=payment_id,
                message=f"Notifications queued: {result.get('notifications_queued', 0)}"
            )

        except Exception as e:
            # Log notification error but don't fail the webhook
            logger.error(f"Failed to send payment pending notification for payment {payment_id}: {str(e)}")

            return WebhookResponse(
                status="partial_success",
                payment_id=payment_id,
                message="Payment status updated but notification failed"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Webhook processing failed for payment {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
