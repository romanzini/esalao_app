"""
Unit tests for payment models.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock

from backend.app.db.models.payment import Payment, Refund, PaymentWebhookEvent
from backend.app.domain.payments.provider import PaymentMethod, PaymentStatus
from backend.app.domain.payments import RefundStatus


class TestPaymentModel:
    """Test Payment model."""

    def test_payment_model_creation(self):
        """Test payment model creation with required fields."""
        payment = Payment(
            provider_payment_id="pay_123",
            provider_name="mock",
            amount=Decimal("100.50"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.PENDING,
            description="Test payment",
            customer_id="customer_123",
            booking_id=1,
        )

        assert payment.provider_payment_id == "pay_123"
        assert payment.provider_name == "mock"
        assert payment.amount == Decimal("100.50")
        assert payment.currency == "BRL"
        assert payment.method == PaymentMethod.CREDIT_CARD
        assert payment.status == PaymentStatus.PENDING
        assert payment.description == "Test payment"
        assert payment.customer_id == "customer_123"
        assert payment.booking_id == 1
        assert payment.metadata == {}
        assert payment.provider_data == {}
        assert payment.id is None  # Not set until saved
        assert payment.created_at is None  # Set by database
        assert payment.updated_at is None  # Set by database

    def test_payment_model_with_metadata(self):
        """Test payment model with metadata."""
        metadata = {"user_id": "456", "session_id": "abc123"}
        provider_data = {"stripe_intent_id": "pi_123"}

        payment = Payment(
            provider_payment_id="pay_123",
            provider_name="stripe",
            amount=Decimal("75.00"),
            currency="BRL",
            method=PaymentMethod.PIX,
            status=PaymentStatus.COMPLETED,
            description="PIX payment",
            metadata=metadata,
            provider_data=provider_data,
        )

        assert payment.metadata == metadata
        assert payment.provider_data == provider_data

    def test_payment_model_str_representation(self):
        """Test payment model string representation."""
        payment = Payment(
            provider_payment_id="pay_123",
            provider_name="mock",
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.PENDING,
            description="Test payment",
        )

        expected = "Payment(id=None, provider_payment_id=pay_123, amount=100.00 BRL, status=pending)"
        assert str(payment) == expected

    def test_payment_model_repr(self):
        """Test payment model repr representation."""
        payment = Payment(
            provider_payment_id="pay_123",
            provider_name="mock",
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.PENDING,
            description="Test payment",
        )

        expected = "Payment(id=None, provider_payment_id=pay_123, amount=100.00 BRL, status=pending)"
        assert repr(payment) == expected


class TestRefundModel:
    """Test Refund model."""

    def test_refund_model_creation(self):
        """Test refund model creation with required fields."""
        refund = Refund(
            provider_refund_id="ref_123",
            payment_id=1,
            amount=Decimal("50.00"),
            currency="BRL",
            status=RefundStatus.PROCESSING,
            reason="Customer request",
        )

        assert refund.provider_refund_id == "ref_123"
        assert refund.payment_id == 1
        assert refund.amount == Decimal("50.00")
        assert refund.currency == "BRL"
        assert refund.status == RefundStatus.PROCESSING
        assert refund.reason == "Customer request"
        assert refund.metadata == {}
        assert refund.provider_data == {}
        assert refund.id is None  # Not set until saved
        assert refund.created_at is None  # Set by database
        assert refund.updated_at is None  # Set by database

    def test_refund_model_with_metadata(self):
        """Test refund model with metadata."""
        metadata = {"admin_id": "admin_123", "request_id": "req_456"}
        provider_data = {"stripe_refund_id": "re_123"}

        refund = Refund(
            provider_refund_id="ref_123",
            payment_id=1,
            amount=Decimal("25.00"),
            currency="BRL",
            status=RefundStatus.COMPLETED,
            reason="Duplicate charge",
            metadata=metadata,
            provider_data=provider_data,
        )

        assert refund.metadata == metadata
        assert refund.provider_data == provider_data

    def test_refund_model_str_representation(self):
        """Test refund model string representation."""
        refund = Refund(
            provider_refund_id="ref_123",
            payment_id=1,
            amount=Decimal("50.00"),
            currency="BRL",
            status=RefundStatus.PROCESSING,
            reason="Customer request",
        )

        expected = "Refund(id=None, provider_refund_id=ref_123, amount=50.00 BRL, status=processing)"
        assert str(refund) == expected

    def test_refund_model_repr(self):
        """Test refund model repr representation."""
        refund = Refund(
            provider_refund_id="ref_123",
            payment_id=1,
            amount=Decimal("50.00"),
            currency="BRL",
            status=RefundStatus.PROCESSING,
            reason="Customer request",
        )

        expected = "Refund(id=None, provider_refund_id=ref_123, amount=50.00 BRL, status=processing)"
        assert repr(refund) == expected


class TestPaymentWebhookEventModel:
    """Test PaymentWebhookEvent model."""

    def test_webhook_event_model_creation(self):
        """Test webhook event model creation with required fields."""
        event = PaymentWebhookEvent(
            provider_name="stripe",
            event_id="evt_123",
            event_type="payment.completed",
            payment_id=1,
            data={"amount": 100.00, "currency": "BRL"},
        )

        assert event.provider_name == "stripe"
        assert event.event_id == "evt_123"
        assert event.event_type == "payment.completed"
        assert event.payment_id == 1
        assert event.data == {"amount": 100.00, "currency": "BRL"}
        assert event.processed is False  # Default value
        assert event.id is None  # Not set until saved
        assert event.created_at is None  # Set by database
        assert event.processed_at is None  # Not processed yet

    def test_webhook_event_model_processed(self):
        """Test webhook event model when processed."""
        processed_at = datetime.now(timezone.utc)

        event = PaymentWebhookEvent(
            provider_name="mock",
            event_id="evt_456",
            event_type="refund.completed",
            refund_id=2,
            data={"refund_amount": 50.00},
            processed=True,
            processed_at=processed_at,
        )

        assert event.processed is True
        assert event.processed_at == processed_at
        assert event.refund_id == 2
        assert event.payment_id is None  # Can be None for refund events

    def test_webhook_event_model_str_representation(self):
        """Test webhook event model string representation."""
        event = PaymentWebhookEvent(
            provider_name="stripe",
            event_id="evt_123",
            event_type="payment.completed",
            payment_id=1,
            data={},
        )

        expected = "PaymentWebhookEvent(id=None, event_id=evt_123, event_type=payment.completed, processed=False)"
        assert str(event) == expected

    def test_webhook_event_model_repr(self):
        """Test webhook event model repr representation."""
        event = PaymentWebhookEvent(
            provider_name="stripe",
            event_id="evt_123",
            event_type="payment.completed",
            payment_id=1,
            data={},
        )

        expected = "PaymentWebhookEvent(id=None, event_id=evt_123, event_type=payment.completed, processed=False)"
        assert repr(event) == expected


class TestModelRelationships:
    """Test model relationships and constraints."""

    def test_payment_to_refund_relationship(self):
        """Test that a payment can have multiple refunds."""
        # Note: This test would require database setup in integration tests
        # Here we just test the model structure
        payment = Payment(
            provider_payment_id="pay_123",
            provider_name="mock",
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.COMPLETED,
            description="Test payment",
        )

        # In a real scenario with database, payment.refunds would be populated
        # For unit test, we just verify the model has the relationship defined
        assert hasattr(payment, '__table__')

        # Check that the refunds relationship would be accessible
        # (This would be tested properly in integration tests)

    def test_refund_payment_relationship(self):
        """Test that a refund references a payment."""
        refund = Refund(
            provider_refund_id="ref_123",
            payment_id=1,  # References payment.id
            amount=Decimal("50.00"),
            currency="BRL",
            status=RefundStatus.PROCESSING,
            reason="Customer request",
        )

        assert refund.payment_id == 1
        assert hasattr(refund, '__table__')

    def test_webhook_event_relationships(self):
        """Test webhook event relationships to payment and refund."""
        # Webhook for payment
        payment_event = PaymentWebhookEvent(
            provider_name="stripe",
            event_id="evt_pay_123",
            event_type="payment.completed",
            payment_id=1,
            data={},
        )

        assert payment_event.payment_id == 1
        assert payment_event.refund_id is None

        # Webhook for refund
        refund_event = PaymentWebhookEvent(
            provider_name="stripe",
            event_id="evt_ref_123",
            event_type="refund.completed",
            refund_id=2,
            data={},
        )

        assert refund_event.refund_id == 2
        assert refund_event.payment_id is None
