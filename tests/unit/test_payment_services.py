"""
Unit tests for payment services.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from backend.app.domain.payments.logging_service import PaymentLogger
from backend.app.domain.payments.services.webhook_service import WebhookService
from backend.app.domain.payments.services.reconciliation_service import ReconciliationService
from backend.app.domain.payments.provider import (
    PaymentMethod,
    PaymentStatus,
    PaymentRequest,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    WebhookEvent,
    PaymentProviderError,
)
from backend.app.db.models.payment import Payment, Refund
from backend.app.db.models.payment_log import PaymentLog


class TestPaymentLoggingService:
    """Test payment logging service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.service = PaymentLogger(self.mock_session)

    def test_log_payment_created(self):
        """Test logging payment creation."""
        payment = Payment(
            id=1,
            provider_payment_id="pay_123",
            provider_name="mock",
            amount=Decimal("100.00"),
            currency="BRL",
            method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.PENDING,
            description="Test payment",
        )

        self.service.log_payment_created(payment)

        # Verify log entry was created
        self.mock_session.add.assert_called_once()
        log_entry = self.mock_session.add.call_args[0][0]

        assert isinstance(log_entry, PaymentLog)
        assert log_entry.payment_id == 1
        assert log_entry.action == "payment_created"
        assert log_entry.status == PaymentStatus.PENDING
        assert log_entry.amount == Decimal("100.00")
        assert "payment_created" in log_entry.details

        self.mock_session.commit.assert_called_once()

    def test_log_payment_status_changed(self):
        """Test logging payment status change."""
        old_status = PaymentStatus.PENDING
        new_status = PaymentStatus.COMPLETED

        self.service.log_payment_status_changed(1, old_status, new_status)

        # Verify log entry was created
        self.mock_session.add.assert_called_once()
        log_entry = self.mock_session.add.call_args[0][0]

        assert isinstance(log_entry, PaymentLog)
        assert log_entry.payment_id == 1
        assert log_entry.action == "status_changed"
        assert log_entry.status == new_status
        assert log_entry.details["old_status"] == old_status
        assert log_entry.details["new_status"] == new_status

        self.mock_session.commit.assert_called_once()

    def test_log_refund_created(self):
        """Test logging refund creation."""
        refund = Refund(
            id=1,
            provider_refund_id="ref_123",
            payment_id=1,
            amount=Decimal("50.00"),
            currency="BRL",
            status="processing",
            reason="Customer request",
        )

        self.service.log_refund_created(refund)

        # Verify log entry was created
        self.mock_session.add.assert_called_once()
        log_entry = self.mock_session.add.call_args[0][0]

        assert isinstance(log_entry, PaymentLog)
        assert log_entry.payment_id == 1
        assert log_entry.refund_id == 1
        assert log_entry.action == "refund_created"
        assert log_entry.amount == Decimal("50.00")
        assert "refund_created" in log_entry.details

        self.mock_session.commit.assert_called_once()

    def test_log_webhook_received(self):
        """Test logging webhook receipt."""
        webhook_data = {
            "event": "payment.completed",
            "payment_id": "pay_123",
            "timestamp": "2023-01-01T12:00:00Z",
        }

        self.service.log_webhook_received("stripe", "evt_123", webhook_data)

        # Verify log entry was created
        self.mock_session.add.assert_called_once()
        log_entry = self.mock_session.add.call_args[0][0]

        assert isinstance(log_entry, PaymentLog)
        assert log_entry.action == "webhook_received"
        assert log_entry.details["provider"] == "stripe"
        assert log_entry.details["event_id"] == "evt_123"
        assert log_entry.details["webhook_data"] == webhook_data

        self.mock_session.commit.assert_called_once()

    def test_log_payment_action_with_metadata(self):
        """Test logging payment action with metadata."""
        metadata = {"user_id": "123", "admin_action": True}

        self.service.log_payment_action(
            payment_id=1,
            action="manual_capture",
            status=PaymentStatus.COMPLETED,
            amount=Decimal("100.00"),
            details={"capture_method": "manual"},
            metadata=metadata,
        )

        # Verify log entry was created
        self.mock_session.add.assert_called_once()
        log_entry = self.mock_session.add.call_args[0][0]

        assert isinstance(log_entry, PaymentLog)
        assert log_entry.payment_id == 1
        assert log_entry.action == "manual_capture"
        assert log_entry.status == PaymentStatus.COMPLETED
        assert log_entry.amount == Decimal("100.00")
        assert log_entry.details == {"capture_method": "manual"}
        assert log_entry.metadata == metadata

        self.mock_session.commit.assert_called_once()


class TestWebhookService:
    """Test webhook service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = AsyncMock()
        self.mock_provider_factory = Mock()
        self.mock_logging_service = Mock()

        self.service = WebhookService(
            self.mock_session,
            self.mock_provider_factory,
            self.mock_logging_service,
        )

    @pytest.mark.asyncio
    async def test_process_webhook_success(self):
        """Test successful webhook processing."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.validate_webhook_signature.return_value = True

        webhook_event = WebhookEvent(
            event_type="payment.completed",
            payment_id="pay_123",
            data={"status": "completed"},
            timestamp=datetime.now(),
        )
        mock_provider.process_webhook_event.return_value = webhook_event

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Mock database queries
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.status = PaymentStatus.PENDING

        self.mock_session.execute.return_value.scalar_one_or_none.return_value = mock_payment

        # Mock webhook event query (not exists)
        self.mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_payment,  # Payment query
            None,  # Webhook event query (not exists)
        ]

        # Process webhook
        payload = b'{"event": "payment.completed"}'
        signature = "valid_signature"

        result = await self.service.process_webhook("stripe", payload, signature)

        assert result is True

        # Verify provider was called
        mock_provider.validate_webhook_signature.assert_called_once_with(payload, signature)
        mock_provider.process_webhook_event.assert_called_once()

        # Verify payment status was updated
        assert mock_payment.status == PaymentStatus.COMPLETED

        # Verify webhook event was saved
        self.mock_session.add.assert_called()
        self.mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_webhook_invalid_signature(self):
        """Test webhook processing with invalid signature."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.validate_webhook_signature.return_value = False

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Process webhook
        payload = b'{"event": "payment.completed"}'
        signature = "invalid_signature"

        result = await self.service.process_webhook("stripe", payload, signature)

        assert result is False

        # Verify provider was called
        mock_provider.validate_webhook_signature.assert_called_once_with(payload, signature)

        # Verify no further processing occurred
        mock_provider.process_webhook_event.assert_not_called()
        self.mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_webhook_duplicate_event(self):
        """Test webhook processing with duplicate event."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.validate_webhook_signature.return_value = True

        webhook_event = WebhookEvent(
            event_type="payment.completed",
            payment_id="pay_123",
            data={"status": "completed"},
            timestamp=datetime.now(),
        )
        mock_provider.process_webhook_event.return_value = webhook_event

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Mock database queries
        mock_payment = Mock()
        mock_payment.id = 1

        mock_existing_event = Mock()  # Existing webhook event

        self.mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_payment,  # Payment query
            mock_existing_event,  # Webhook event query (exists)
        ]

        # Process webhook
        payload = b'{"event": "payment.completed"}'
        signature = "valid_signature"

        result = await self.service.process_webhook("stripe", payload, signature)

        assert result is True  # Already processed, but still success

        # Verify no new webhook event was saved
        self.mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_webhook_payment_not_found(self):
        """Test webhook processing when payment is not found."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.validate_webhook_signature.return_value = True

        webhook_event = WebhookEvent(
            event_type="payment.completed",
            payment_id="pay_nonexistent",
            data={"status": "completed"},
            timestamp=datetime.now(),
        )
        mock_provider.process_webhook_event.return_value = webhook_event

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Mock database queries (payment not found)
        self.mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Process webhook
        payload = b'{"event": "payment.completed"}'
        signature = "valid_signature"

        result = await self.service.process_webhook("stripe", payload, signature)

        assert result is False

        # Verify logging was called for error
        self.mock_logging_service.log_webhook_received.assert_called()


class TestReconciliationService:
    """Test reconciliation service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = AsyncMock()
        self.mock_provider_factory = Mock()
        self.mock_logging_service = Mock()

        self.service = ReconciliationService(
            self.mock_session,
            self.mock_provider_factory,
            self.mock_logging_service,
        )

    @pytest.mark.asyncio
    async def test_reconcile_payment_status_mismatch(self):
        """Test reconciling payment with status mismatch."""
        # Mock payment in database
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.provider_payment_id = "pay_123"
        mock_payment.status = PaymentStatus.PENDING

        # Mock provider response
        mock_provider = Mock()
        provider_response = PaymentResponse(
            payment_id="pay_123",
            status=PaymentStatus.COMPLETED,
            amount=Decimal("100.00"),
            currency="BRL",
        )
        mock_provider.get_payment_status.return_value = provider_response

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Reconcile payment
        result = await self.service.reconcile_payment(mock_payment)

        assert result is True

        # Verify status was updated
        assert mock_payment.status == PaymentStatus.COMPLETED

        # Verify logging
        self.mock_logging_service.log_payment_status_changed.assert_called_once_with(
            1, PaymentStatus.PENDING, PaymentStatus.COMPLETED
        )

        # Verify database commit
        self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconcile_payment_status_match(self):
        """Test reconciling payment with matching status."""
        # Mock payment in database
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.provider_payment_id = "pay_123"
        mock_payment.status = PaymentStatus.COMPLETED

        # Mock provider response
        mock_provider = Mock()
        provider_response = PaymentResponse(
            payment_id="pay_123",
            status=PaymentStatus.COMPLETED,
            amount=Decimal("100.00"),
            currency="BRL",
        )
        mock_provider.get_payment_status.return_value = provider_response

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Reconcile payment
        result = await self.service.reconcile_payment(mock_payment)

        assert result is False  # No update needed

        # Verify no logging or database updates
        self.mock_logging_service.log_payment_status_changed.assert_not_called()
        self.mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_payment_provider_error(self):
        """Test reconciling payment when provider returns error."""
        # Mock payment in database
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.provider_payment_id = "pay_123"
        mock_payment.provider_name = "stripe"

        # Mock provider error
        mock_provider = Mock()
        mock_provider.get_payment_status.side_effect = PaymentProviderError("Payment not found")

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Reconcile payment
        result = await self.service.reconcile_payment(mock_payment)

        assert result is False

        # Verify no updates occurred
        self.mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_pending_payments(self):
        """Test reconciling all pending payments."""
        # Mock pending payments
        mock_payment1 = Mock()
        mock_payment1.id = 1
        mock_payment1.provider_payment_id = "pay_123"
        mock_payment1.provider_name = "mock"
        mock_payment1.status = PaymentStatus.PENDING

        mock_payment2 = Mock()
        mock_payment2.id = 2
        mock_payment2.provider_payment_id = "pay_456"
        mock_payment2.provider_name = "stripe"
        mock_payment2.status = PaymentStatus.PROCESSING

        # Mock database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_payment1, mock_payment2]
        self.mock_session.execute.return_value = mock_result

        # Mock provider responses
        mock_provider = Mock()
        provider_response1 = PaymentResponse(
            payment_id="pay_123",
            status=PaymentStatus.COMPLETED,
            amount=Decimal("100.00"),
            currency="BRL",
        )
        provider_response2 = PaymentResponse(
            payment_id="pay_456",
            status=PaymentStatus.FAILED,
            amount=Decimal("50.00"),
            currency="BRL",
        )
        mock_provider.get_payment_status.side_effect = [provider_response1, provider_response2]

        self.mock_provider_factory.get_provider.return_value = mock_provider

        # Reconcile pending payments
        result = await self.service.reconcile_pending_payments()

        assert result["total_checked"] == 2
        assert result["updated"] == 2
        assert result["errors"] == 0

        # Verify status updates
        assert mock_payment1.status == PaymentStatus.COMPLETED
        assert mock_payment2.status == PaymentStatus.FAILED

        # Verify logging calls
        assert self.mock_logging_service.log_payment_status_changed.call_count == 2
