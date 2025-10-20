"""
Unit tests for payment provider interface and implementations.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

from backend.app.domain.payments.provider import (
    PaymentProvider,
    PaymentMethod,
    PaymentStatus,
    PaymentRequest,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    WebhookEvent,
    PaymentProviderError,
    PaymentProviderUnavailableError,
    PaymentProviderConfigurationError,
)
from backend.app.domain.payments.providers.mock import MockPaymentProvider
from backend.app.domain.payments.providers.stripe import StripePaymentProvider


class TestPaymentProvider:
    """Test abstract payment provider interface."""

    def test_payment_provider_is_abstract(self):
        """Test that PaymentProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PaymentProvider()


class TestPaymentMethod:
    """Test payment method enum."""

    def test_payment_method_values(self):
        """Test all payment method values are defined."""
        assert PaymentMethod.CREDIT_CARD == "credit_card"
        assert PaymentMethod.DEBIT_CARD == "debit_card"
        assert PaymentMethod.PIX == "pix"
        assert PaymentMethod.BANK_SLIP == "bank_slip"


class TestPaymentStatus:
    """Test payment status enum."""

    def test_payment_status_values(self):
        """Test all payment status values are defined."""
        assert PaymentStatus.PENDING == "pending"
        assert PaymentStatus.PROCESSING == "processing"
        assert PaymentStatus.COMPLETED == "completed"
        assert PaymentStatus.FAILED == "failed"
        assert PaymentStatus.CANCELLED == "cancelled"
        assert PaymentStatus.EXPIRED == "expired"


class TestPaymentRequest:
    """Test payment request dataclass."""

    def test_payment_request_creation(self):
        """Test payment request creation with required fields."""
        request = PaymentRequest(
            amount=Decimal("100.50"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
        )

        assert request.amount == Decimal("100.50")
        assert request.currency == "BRL"
        assert request.method == PaymentMethod.CREDIT_CARD
        assert request.description == "Test payment"
        assert request.customer_id is None
        assert request.metadata == {}

    def test_payment_request_with_optional_fields(self):
        """Test payment request with all fields."""
        metadata = {"booking_id": "123", "user_id": "456"}

        request = PaymentRequest(
            amount=Decimal("50.00"),
            currency="BRL",
            method=PaymentMethod.PIX,
            description="PIX payment",
            customer_id="customer_123",
            metadata=metadata,
        )

        assert request.customer_id == "customer_123"
        assert request.metadata == metadata


class TestPaymentResponse:
    """Test payment response dataclass."""

    def test_payment_response_creation(self):
        """Test payment response creation."""
        response = PaymentResponse(
            payment_id="pay_123",
            status=PaymentStatus.PENDING,
            amount=Decimal("100.00"),
            currency="BRL",
        )

        assert response.payment_id == "pay_123"
        assert response.status == PaymentStatus.PENDING
        assert response.amount == Decimal("100.00")
        assert response.currency == "BRL"
        assert response.provider_data is None


class TestMockPaymentProvider:
    """Test mock payment provider implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = MockPaymentProvider()

    def test_provider_name(self):
        """Test provider name."""
        assert self.provider.provider_name == "mock"

    def test_create_payment_success(self):
        """Test successful payment creation."""
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
        )

        response = self.provider.create_payment(request)

        assert response.payment_id.startswith("mock_pay_")
        assert response.status == PaymentStatus.PENDING
        assert response.amount == Decimal("100.00")
        assert response.currency == "BRL"
        assert "created_at" in response.provider_data

    def test_create_payment_with_failure_scenario(self):
        """Test payment creation with failure scenario."""
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
            metadata={"scenario": "payment_failed"},
        )

        response = self.provider.create_payment(request)

        assert response.status == PaymentStatus.FAILED

    def test_create_payment_with_network_error_scenario(self):
        """Test payment creation with network error scenario."""
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
            metadata={"scenario": "network_error"},
        )

        with pytest.raises(PaymentProviderUnavailableError):
            self.provider.create_payment(request)

    def test_get_payment_status(self):
        """Test getting payment status."""
        # Create a payment first
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
        )

        payment_response = self.provider.create_payment(request)
        payment_id = payment_response.payment_id

        # Get status
        status_response = self.provider.get_payment_status(payment_id)

        assert status_response.payment_id == payment_id
        assert status_response.status == PaymentStatus.PENDING
        assert status_response.amount == Decimal("100.00")

    def test_get_payment_status_not_found(self):
        """Test getting status for non-existent payment."""
        with pytest.raises(PaymentProviderError, match="Payment not found"):
            self.provider.get_payment_status("non_existent_payment")

    def test_cancel_payment(self):
        """Test payment cancellation."""
        # Create a payment first
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
        )

        payment_response = self.provider.create_payment(request)
        payment_id = payment_response.payment_id

        # Cancel payment
        cancel_response = self.provider.cancel_payment(payment_id)

        assert cancel_response.payment_id == payment_id
        assert cancel_response.status == PaymentStatus.CANCELLED

    def test_cancel_completed_payment(self):
        """Test cancelling a completed payment should fail."""
        # Create a completed payment
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
            metadata={"scenario": "payment_completed"},
        )

        payment_response = self.provider.create_payment(request)
        payment_id = payment_response.payment_id

        # Try to cancel
        with pytest.raises(PaymentProviderError, match="Cannot cancel completed payment"):
            self.provider.cancel_payment(payment_id)

    def test_create_refund(self):
        """Test refund creation."""
        # Create a completed payment first
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
            metadata={"scenario": "payment_completed"},
        )

        payment_response = self.provider.create_payment(request)
        payment_id = payment_response.payment_id

        # Create refund
        refund_request = RefundRequest(
            payment_id=payment_id,
            amount=Decimal("50.00"),
            reason="Customer request",
        )

        refund_response = self.provider.create_refund(refund_request)

        assert refund_response.refund_id.startswith("mock_ref_")
        assert refund_response.payment_id == payment_id
        assert refund_response.amount == Decimal("50.00")
        assert refund_response.status == "processing"

    def test_create_refund_for_pending_payment(self):
        """Test refund creation for pending payment should fail."""
        # Create a pending payment
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
        )

        payment_response = self.provider.create_payment(request)
        payment_id = payment_response.payment_id

        # Try to create refund
        refund_request = RefundRequest(
            payment_id=payment_id,
            amount=Decimal("50.00"),
            reason="Customer request",
        )

        with pytest.raises(PaymentProviderError, match="Cannot refund pending payment"):
            self.provider.create_refund(refund_request)

    def test_validate_webhook_signature_valid(self):
        """Test webhook signature validation with valid signature."""
        payload = b'{"event": "payment.completed"}'
        signature = "mock_signature_123"

        result = self.provider.validate_webhook_signature(payload, signature)
        assert result is True

    def test_validate_webhook_signature_invalid(self):
        """Test webhook signature validation with invalid signature."""
        payload = b'{"event": "payment.completed"}'
        signature = "invalid_signature"

        result = self.provider.validate_webhook_signature(payload, signature)
        assert result is False

    def test_process_webhook_event(self):
        """Test webhook event processing."""
        webhook_data = {
            "event": "payment.completed",
            "payment_id": "mock_pay_123",
            "timestamp": "2023-01-01T12:00:00Z",
        }

        event = self.provider.process_webhook_event(webhook_data)

        assert isinstance(event, WebhookEvent)
        assert event.event_type == "payment.completed"
        assert event.payment_id == "mock_pay_123"
        assert event.data == webhook_data


class TestStripePaymentProvider:
    """Test Stripe payment provider implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = StripePaymentProvider()

    def test_provider_name(self):
        """Test provider name."""
        assert self.provider.get_provider_name() == "stripe"

    def test_create_payment_not_implemented(self):
        """Test that Stripe provider methods are not implemented yet."""
        request = PaymentRequest(
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            description="Test payment",
        )

        with pytest.raises(NotImplementedError):
            self.provider.create_payment(request)

    def test_get_payment_status_not_implemented(self):
        """Test that get_payment_status is not implemented."""
        with pytest.raises(NotImplementedError):
            self.provider.get_payment_status("payment_123")

    def test_cancel_payment_not_implemented(self):
        """Test that cancel_payment is not implemented."""
        with pytest.raises(NotImplementedError):
            self.provider.cancel_payment("payment_123")

    def test_create_refund_not_implemented(self):
        """Test that create_refund is not implemented."""
        refund_request = RefundRequest(
            payment_id="payment_123",
            amount=Decimal("50.00"),
            reason="Test refund",
        )

        with pytest.raises(NotImplementedError):
            self.provider.create_refund(refund_request)

    def test_validate_webhook_signature_not_implemented(self):
        """Test that validate_webhook_signature is not implemented."""
        with pytest.raises(NotImplementedError):
            self.provider.validate_webhook_signature(b"payload", "signature")

    def test_process_webhook_event_not_implemented(self):
        """Test that process_webhook_event is not implemented."""
        with pytest.raises(NotImplementedError):
            self.provider.process_webhook_event({})
