"""
Mock Payment Provider

This provider simulates payment processing for development and testing.
It provides configurable responses and doesn't make real payment calls.
"""

import asyncio
import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any

from ..provider import (
    PaymentProvider,
    PaymentMethod,
    PaymentStatus,
    PaymentRequest,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    WebhookEvent,
    PaymentProviderError,
)


class MockPaymentProvider(PaymentProvider):
    """
    Mock payment provider for development and testing.

    This provider simulates payment processing without making real API calls.
    It can be configured to simulate different scenarios (success, failure, etc.)
    """

    def __init__(
        self,
        secret_key: str = "mock_secret_key",
        simulate_delays: bool = True,
        default_success_rate: float = 0.95,
        **kwargs
    ):
        """
        Initialize mock provider.

        Args:
            secret_key: Secret key for webhook validation
            simulate_delays: Whether to simulate network delays
            default_success_rate: Probability of payment success (0.0 to 1.0)
        """
        self.secret_key = secret_key
        self.simulate_delays = simulate_delays
        self.default_success_rate = default_success_rate

        # In-memory storage for testing
        self._payments: Dict[str, PaymentResponse] = {}
        self._refunds: Dict[str, RefundResponse] = {}

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def supported_methods(self) -> list[PaymentMethod]:
        return [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.PIX,
            PaymentMethod.BANK_SLIP,
        ]

    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Create a mock payment."""
        if self.simulate_delays:
            await asyncio.sleep(0.1)  # Simulate network delay

        # Generate mock payment ID
        payment_id = f"mock_pay_{uuid.uuid4().hex[:16]}"

        # Simulate payment processing based on amount
        # Amounts ending in .00 succeed, .99 fail, others random
        if request.amount % 1 == 0:
            status = PaymentStatus.SUCCEEDED
        elif str(request.amount).endswith('.99'):
            status = PaymentStatus.FAILED
        else:
            import random
            status = PaymentStatus.SUCCEEDED if random.random() < self.default_success_rate else PaymentStatus.FAILED

        now = datetime.now(timezone.utc)

        # Generate payment URL for PIX
        payment_url = None
        if request.payment_method == PaymentMethod.PIX and status == PaymentStatus.SUCCEEDED:
            payment_url = f"https://mock-pix.example.com/qr/{payment_id}"

        response = PaymentResponse(
            provider_payment_id=payment_id,
            status=status,
            amount=request.amount,
            currency=request.currency,
            payment_method=request.payment_method,
            created_at=now,
            updated_at=now,
            payment_url=payment_url,
            provider_data={
                "mock_provider": True,
                "customer_id": request.customer_id,
                "description": request.description,
                "metadata": request.metadata,
            }
        )

        # Store for later retrieval
        self._payments[payment_id] = response

        return response

    async def get_payment_status(self, provider_payment_id: str) -> PaymentResponse:
        """Get mock payment status."""
        if self.simulate_delays:
            await asyncio.sleep(0.05)

        if provider_payment_id not in self._payments:
            raise PaymentProviderError(
                f"Payment {provider_payment_id} not found",
                provider_error_code="payment_not_found"
            )

        payment = self._payments[provider_payment_id]

        # Simulate status changes for pending payments
        if payment.status == PaymentStatus.PENDING:
            import random
            if random.random() < 0.3:  # 30% chance to complete
                payment.status = PaymentStatus.SUCCEEDED if random.random() < 0.9 else PaymentStatus.FAILED
                payment.updated_at = datetime.now(timezone.utc)

        return payment

    async def cancel_payment(self, provider_payment_id: str) -> PaymentResponse:
        """Cancel a mock payment."""
        if self.simulate_delays:
            await asyncio.sleep(0.05)

        if provider_payment_id not in self._payments:
            raise PaymentProviderError(
                f"Payment {provider_payment_id} not found",
                provider_error_code="payment_not_found"
            )

        payment = self._payments[provider_payment_id]

        if payment.status not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            raise PaymentProviderError(
                f"Cannot cancel payment with status {payment.status.value}",
                provider_error_code="invalid_status"
            )

        payment.status = PaymentStatus.CANCELED
        payment.updated_at = datetime.now(timezone.utc)

        return payment

    async def create_refund(self, request: RefundRequest) -> RefundResponse:
        """Create a mock refund."""
        if self.simulate_delays:
            await asyncio.sleep(0.1)

        if request.provider_payment_id not in self._payments:
            raise PaymentProviderError(
                f"Payment {request.provider_payment_id} not found",
                provider_error_code="payment_not_found"
            )

        payment = self._payments[request.provider_payment_id]

        if payment.status != PaymentStatus.SUCCEEDED:
            raise PaymentProviderError(
                f"Cannot refund payment with status {payment.status.value}",
                provider_error_code="invalid_status"
            )

        # Calculate refund amount
        refund_amount = request.amount or payment.amount
        if refund_amount > payment.amount:
            raise PaymentProviderError(
                "Refund amount cannot exceed payment amount",
                provider_error_code="invalid_amount"
            )

        # Generate mock refund ID
        refund_id = f"mock_ref_{uuid.uuid4().hex[:16]}"

        now = datetime.now(timezone.utc)

        response = RefundResponse(
            provider_refund_id=refund_id,
            provider_payment_id=request.provider_payment_id,
            status=PaymentStatus.SUCCEEDED,  # Mock refunds always succeed
            amount=refund_amount,
            currency=payment.currency,
            created_at=now,
            provider_data={
                "mock_provider": True,
                "reason": request.reason,
                "metadata": request.metadata,
            }
        )

        # Update payment status
        if refund_amount == payment.amount:
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PARTIALLY_REFUNDED
        payment.updated_at = now

        # Store refund
        self._refunds[refund_id] = response

        return response

    async def get_refund_status(self, provider_refund_id: str) -> RefundResponse:
        """Get mock refund status."""
        if self.simulate_delays:
            await asyncio.sleep(0.05)

        if provider_refund_id not in self._refunds:
            raise PaymentProviderError(
                f"Refund {provider_refund_id} not found",
                provider_error_code="refund_not_found"
            )

        return self._refunds[provider_refund_id]

    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate mock webhook signature."""
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, f"sha256={expected_signature}")

    def parse_webhook(self, payload: Dict[str, Any]) -> WebhookEvent:
        """Parse mock webhook payload."""
        try:
            event_type = payload.get("type", "payment.updated")
            payment_data = payload.get("data", {})

            return WebhookEvent(
                provider_event_id=payload.get("id", f"evt_{uuid.uuid4().hex[:16]}"),
                event_type=event_type,
                provider_payment_id=payment_data.get("id", ""),
                status=PaymentStatus(payment_data.get("status", "pending")),
                timestamp=datetime.fromisoformat(
                    payload.get("created", datetime.now(timezone.utc).isoformat())
                ),
                provider_data=payload
            )
        except (KeyError, ValueError, TypeError) as e:
            raise PaymentProviderError(
                f"Invalid webhook payload: {e}",
                provider_error_code="invalid_webhook"
            )

    def configure_scenario(
        self,
        payment_id: str,
        status: PaymentStatus,
        delay_seconds: float = 0
    ):
        """
        Configure a specific scenario for testing.

        Args:
            payment_id: Payment ID to configure
            status: Status to set
            delay_seconds: Delay before applying status
        """
        async def _apply_delayed_status():
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            if payment_id in self._payments:
                self._payments[payment_id].status = status
                self._payments[payment_id].updated_at = datetime.now(timezone.utc)

        # Schedule the status change
        asyncio.create_task(_apply_delayed_status())

    def reset_state(self):
        """Reset all stored payments and refunds."""
        self._payments.clear()
        self._refunds.clear()
