"""
Webhook Service for idempotent payment webhook processing.

This service handles incoming webhooks from payment providers,
ensuring idempotent processing and proper event handling.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from backend.app.db.models.payment import (
    Payment,
    PaymentWebhookEvent,
    PaymentStatus as ModelPaymentStatus
)
from backend.app.domain.payments import (
    PaymentProvider,
    PaymentStatus,
    WebhookEvent,
    PaymentProviderError,
)
from backend.app.domain.payments.providers import (
    MockPaymentProvider,
    StripePaymentProvider,
)

logger = logging.getLogger(__name__)


class WebhookProcessingResult:
    """Result of webhook processing."""

    def __init__(
        self,
        event_id: str,
        processed: bool,
        payment_id: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        self.event_id = event_id
        self.processed = processed
        self.payment_id = payment_id
        self.error_message = error_message


class WebhookService:
    """
    Service for processing payment webhooks idempotently.

    This service ensures that webhook events are processed exactly once,
    even if the same event is received multiple times.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._providers: Dict[str, PaymentProvider] = {}

    def register_provider(self, name: str, provider: PaymentProvider):
        """Register a payment provider for webhook processing."""
        self._providers[name] = provider

    async def process_stripe_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> WebhookProcessingResult:
        """
        Process Stripe webhook with idempotent handling.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            WebhookProcessingResult with processing information
        """
        provider = self._get_provider("stripe")
        if not provider:
            raise PaymentProviderError("Stripe provider not configured")

        # Validate webhook signature
        if not provider.validate_webhook(payload, signature):
            raise PaymentProviderError("Invalid webhook signature")

        # Parse webhook data
        try:
            webhook_data = json.loads(payload.decode('utf-8'))
            webhook_event = provider.parse_webhook(webhook_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise PaymentProviderError(f"Invalid webhook payload: {e}")

        return await self._process_webhook_event(
            provider_name="stripe",
            webhook_event=webhook_event,
            raw_payload=payload.decode('utf-8'),
            headers={"stripe-signature": signature}
        )

    async def process_pagarme_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> WebhookProcessingResult:
        """
        Process PagarMe webhook with idempotent handling.

        Args:
            payload: Raw webhook payload
            signature: PagarMe signature header

        Returns:
            WebhookProcessingResult with processing information
        """
        provider = self._get_provider("pagarme")
        if not provider:
            raise PaymentProviderError("PagarMe provider not configured")

        # Validate webhook signature
        if not provider.validate_webhook(payload, signature):
            raise PaymentProviderError("Invalid webhook signature")

        # Parse webhook data
        try:
            webhook_data = json.loads(payload.decode('utf-8'))
            webhook_event = provider.parse_webhook(webhook_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise PaymentProviderError(f"Invalid webhook payload: {e}")

        return await self._process_webhook_event(
            provider_name="pagarme",
            webhook_event=webhook_event,
            raw_payload=payload.decode('utf-8'),
            headers={"x-hub-signature": signature}
        )

    async def process_mock_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> WebhookProcessingResult:
        """
        Process mock webhook for testing.

        Args:
            payload: Raw webhook payload
            signature: Mock signature header

        Returns:
            WebhookProcessingResult with processing information
        """
        provider = self._get_provider("mock")
        if not provider:
            # Create default mock provider for testing
            provider = MockPaymentProvider()

        # Parse webhook data
        try:
            webhook_data = json.loads(payload.decode('utf-8'))
            webhook_event = provider.parse_webhook(webhook_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise PaymentProviderError(f"Invalid webhook payload: {e}")

        return await self._process_webhook_event(
            provider_name="mock",
            webhook_event=webhook_event,
            raw_payload=payload.decode('utf-8'),
            headers={"x-mock-signature": signature}
        )

    async def _process_webhook_event(
        self,
        provider_name: str,
        webhook_event: WebhookEvent,
        raw_payload: str,
        headers: Dict[str, str]
    ) -> WebhookProcessingResult:
        """
        Process webhook event with idempotent handling.

        This method ensures that each webhook event is processed exactly once
        by using the provider_event_id as a unique constraint.
        """
        try:
            # Check if this event has already been processed
            existing_event = await self._get_existing_webhook_event(
                provider_name=provider_name,
                provider_event_id=webhook_event.provider_event_id
            )

            if existing_event:
                if existing_event.processed:
                    logger.info(
                        f"Webhook event {webhook_event.provider_event_id} "
                        f"already processed successfully"
                    )
                    return WebhookProcessingResult(
                        event_id=webhook_event.provider_event_id,
                        processed=True,
                        payment_id=existing_event.payment_id
                    )
                else:
                    # Retry processing failed event
                    return await self._retry_webhook_processing(
                        existing_event, webhook_event
                    )

            # Create new webhook event record
            webhook_record = PaymentWebhookEvent(
                provider_name=provider_name,
                provider_event_id=webhook_event.provider_event_id,
                event_type=webhook_event.event_type,
                event_data=webhook_event.provider_data,
                raw_payload=raw_payload,
                headers=headers,
                processed=False,
                processing_attempts=1
            )

            # Find related payment
            payment = await self._find_payment_by_provider_id(
                provider_name=provider_name,
                provider_payment_id=webhook_event.provider_payment_id
            )

            if payment:
                webhook_record.payment_id = payment.id

                # Update payment status
                await self._update_payment_status(payment, webhook_event)

                # Mark webhook as processed
                webhook_record.mark_processed()

                self.db.add(webhook_record)
                await self.db.commit()

                logger.info(
                    f"Webhook event {webhook_event.provider_event_id} "
                    f"processed successfully for payment {payment.id}"
                )

                return WebhookProcessingResult(
                    event_id=webhook_event.provider_event_id,
                    processed=True,
                    payment_id=payment.id
                )
            else:
                # Payment not found - log but don't fail
                error_msg = f"Payment not found for provider_payment_id: {webhook_event.provider_payment_id}"
                webhook_record.mark_failed(error_msg)

                self.db.add(webhook_record)
                await self.db.commit()

                logger.warning(error_msg)

                return WebhookProcessingResult(
                    event_id=webhook_event.provider_event_id,
                    processed=False,
                    error_message=error_msg
                )

        except IntegrityError:
            # Race condition - another process already created this event
            await self.db.rollback()

            existing_event = await self._get_existing_webhook_event(
                provider_name=provider_name,
                provider_event_id=webhook_event.provider_event_id
            )

            if existing_event and existing_event.processed:
                return WebhookProcessingResult(
                    event_id=webhook_event.provider_event_id,
                    processed=True,
                    payment_id=existing_event.payment_id
                )
            else:
                return WebhookProcessingResult(
                    event_id=webhook_event.provider_event_id,
                    processed=False,
                    error_message="Race condition during processing"
                )

        except Exception as e:
            await self.db.rollback()
            error_msg = f"Webhook processing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return WebhookProcessingResult(
                event_id=webhook_event.provider_event_id,
                processed=False,
                error_message=error_msg
            )

    async def _get_existing_webhook_event(
        self,
        provider_name: str,
        provider_event_id: str
    ) -> Optional[PaymentWebhookEvent]:
        """Get existing webhook event if it exists."""
        result = await self.db.execute(
            select(PaymentWebhookEvent).where(
                and_(
                    PaymentWebhookEvent.provider_name == provider_name,
                    PaymentWebhookEvent.provider_event_id == provider_event_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def _find_payment_by_provider_id(
        self,
        provider_name: str,
        provider_payment_id: str
    ) -> Optional[Payment]:
        """Find payment by provider payment ID."""
        result = await self.db.execute(
            select(Payment).where(
                and_(
                    Payment.provider_name == provider_name,
                    Payment.provider_payment_id == provider_payment_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def _update_payment_status(
        self,
        payment: Payment,
        webhook_event: WebhookEvent
    ):
        """Update payment status based on webhook event."""
        old_status = payment.status
        new_status = webhook_event.status.value

        # Only update if status has changed
        if old_status != new_status:
            payment.status = new_status
            payment.update_status_timestamps()
            payment.last_webhook_at = webhook_event.timestamp
            payment.webhook_events_count += 1

            logger.info(
                f"Payment {payment.id} status updated from {old_status} to {new_status}"
            )

    async def _retry_webhook_processing(
        self,
        existing_event: PaymentWebhookEvent,
        webhook_event: WebhookEvent
    ) -> WebhookProcessingResult:
        """Retry processing a failed webhook event."""
        try:
            existing_event.processing_attempts += 1

            if existing_event.payment_id:
                payment = await self.db.get(Payment, existing_event.payment_id)
                if payment:
                    await self._update_payment_status(payment, webhook_event)
                    existing_event.mark_processed()

                    await self.db.commit()

                    return WebhookProcessingResult(
                        event_id=webhook_event.provider_event_id,
                        processed=True,
                        payment_id=payment.id
                    )

            error_msg = "Payment not found during retry"
            existing_event.mark_failed(error_msg)
            await self.db.commit()

            return WebhookProcessingResult(
                event_id=webhook_event.provider_event_id,
                processed=False,
                error_message=error_msg
            )

        except Exception as e:
            await self.db.rollback()
            error_msg = f"Webhook retry failed: {str(e)}"
            existing_event.mark_failed(error_msg)
            await self.db.commit()

            return WebhookProcessingResult(
                event_id=webhook_event.provider_event_id,
                processed=False,
                error_message=error_msg
            )

    def _get_provider(self, name: str) -> Optional[PaymentProvider]:
        """Get payment provider by name."""
        return self._providers.get(name)

    async def get_system_status(self) -> Dict[str, Any]:
        """Get webhook system status and statistics."""
        # Get recent webhook events statistics
        from sqlalchemy import func, text

        # Count total events
        total_count = await self.db.scalar(
            select(func.count(PaymentWebhookEvent.id))
        )

        # Count processed events
        processed_count = await self.db.scalar(
            select(func.count(PaymentWebhookEvent.id)).where(
                PaymentWebhookEvent.processed == True
            )
        )

        # Count events in last 24 hours
        last_24h_count = await self.db.scalar(
            select(func.count(PaymentWebhookEvent.id)).where(
                PaymentWebhookEvent.created_at >= text("NOW() - INTERVAL '24 hours'")
            )
        )

        return {
            "status": "operational",
            "registered_providers": list(self._providers.keys()),
            "webhook_endpoints": {
                "stripe": "/v1/webhooks/payments/stripe",
                "pagarme": "/v1/webhooks/payments/pagarme",
                "mock": "/v1/webhooks/payments/mock"
            },
            "recent_events": {
                "total": total_count or 0,
                "processed": processed_count or 0,
                "failed": (total_count or 0) - (processed_count or 0),
                "last_24h": last_24h_count or 0
            }
        }
