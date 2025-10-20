"""
Unit tests for payment endpoints.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

from backend.app.main import app
from backend.app.domain.payments.provider import (
    PaymentMethod,
    PaymentStatus,
    PaymentRequest,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    PaymentProviderError,
)


class TestPaymentEndpoints:
    """Test payment endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch('backend.app.api.v1.routes.payments.get_db_session')
    @patch('backend.app.api.v1.routes.payments.PaymentProviderFactory')
    @patch('backend.app.api.v1.routes.payments.PaymentLoggingService')
    def test_create_payment_success(self, mock_logging, mock_factory, mock_get_db):
        """Test successful payment creation."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock provider
        mock_provider = Mock()
        provider_response = PaymentResponse(
            payment_id="pay_123",
            status=PaymentStatus.PENDING,
            amount=Decimal("100.00"),
            currency="BRL",
            provider_data={"created_at": "2023-01-01T12:00:00Z"}
        )
        mock_provider.create_payment.return_value = provider_response
        mock_factory.get_provider.return_value = mock_provider

        # Mock payment save
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # Test data
        payment_data = {
            "amount": "100.00",
            "currency": "BRL",
            "method": "credit_card",
            "description": "Test payment",
            "customer_id": "customer_123",
            "booking_id": 1,
            "metadata": {"user_id": "456"}
        }

        # Execute request
        response = self.client.post("/api/v1/payments/", json=payment_data)

        assert response.status_code == status.HTTP_201_CREATED

        response_data = response.json()
        assert response_data["provider_payment_id"] == "pay_123"
        assert response_data["status"] == "pending"
        assert response_data["amount"] == "100.00"
        assert response_data["currency"] == "BRL"
        assert response_data["method"] == "credit_card"

        # Verify provider was called
        mock_provider.create_payment.assert_called_once()

        # Verify payment was saved
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify logging
        mock_logging.assert_called_once()

    def test_create_payment_invalid_data(self):
        """Test payment creation with invalid data."""
        # Missing required fields
        payment_data = {
            "amount": "invalid_amount",
            "method": "invalid_method",
        }

        response = self.client.post("/api/v1/payments/", json=payment_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('backend.app.api.v1.routes.payments.get_db_session')
    @patch('backend.app.api.v1.routes.payments.PaymentProviderFactory')
    def test_create_payment_provider_error(self, mock_factory, mock_get_db):
        """Test payment creation with provider error."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock provider error
        mock_provider = Mock()
        mock_provider.create_payment.side_effect = PaymentProviderError("Payment failed")
        mock_factory.get_provider.return_value = mock_provider

        # Test data
        payment_data = {
            "amount": "100.00",
            "currency": "BRL",
            "method": "credit_card",
            "description": "Test payment",
        }

        # Execute request
        response = self.client.post("/api/v1/payments/", json=payment_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = response.json()
        assert "Payment failed" in response_data["detail"]

    @patch('backend.app.api.v1.routes.payments.get_db_session')
    def test_get_payment_success(self, mock_get_db):
        """Test successful payment retrieval."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock payment
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.provider_payment_id = "pay_123"
        mock_payment.provider_name = "mock"
        mock_payment.amount = Decimal("100.00")
        mock_payment.currency = "BRL"
        mock_payment.method = PaymentMethod.CREDIT_CARD
        mock_payment.status = PaymentStatus.COMPLETED
        mock_payment.description = "Test payment"
        mock_payment.customer_id = "customer_123"
        mock_payment.booking_id = 1
        mock_payment.metadata = {}
        mock_payment.provider_data = {}
        mock_payment.created_at = "2023-01-01T12:00:00Z"
        mock_payment.updated_at = "2023-01-01T12:00:00Z"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_session.execute.return_value = mock_result

        # Execute request
        response = self.client.get("/api/v1/payments/1")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data["id"] == 1
        assert response_data["provider_payment_id"] == "pay_123"
        assert response_data["status"] == "completed"
        assert response_data["amount"] == "100.00"

    @patch('backend.app.api.v1.routes.payments.get_db_session')
    def test_get_payment_not_found(self, mock_get_db):
        """Test payment retrieval when payment not found."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock payment not found
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute request
        response = self.client.get("/api/v1/payments/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

        response_data = response.json()
        assert "Payment not found" in response_data["detail"]

    @patch('backend.app.api.v1.routes.payments.get_db_session')
    def test_list_payments_success(self, mock_get_db):
        """Test successful payment listing."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock payments
        mock_payment1 = Mock()
        mock_payment1.id = 1
        mock_payment1.provider_payment_id = "pay_123"
        mock_payment1.amount = Decimal("100.00")
        mock_payment1.status = PaymentStatus.COMPLETED

        mock_payment2 = Mock()
        mock_payment2.id = 2
        mock_payment2.provider_payment_id = "pay_456"
        mock_payment2.amount = Decimal("50.00")
        mock_payment2.status = PaymentStatus.PENDING

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_payment1, mock_payment2]
        mock_session.execute.return_value = mock_result

        # Execute request
        response = self.client.get("/api/v1/payments/")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["id"] == 1
        assert response_data[1]["id"] == 2

    @patch('backend.app.api.v1.routes.payments.get_db_session')
    @patch('backend.app.api.v1.routes.payments.PaymentProviderFactory')
    @patch('backend.app.api.v1.routes.payments.PaymentLoggingService')
    def test_cancel_payment_success(self, mock_logging, mock_factory, mock_get_db):
        """Test successful payment cancellation."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock payment
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.provider_payment_id = "pay_123"
        mock_payment.provider_name = "mock"
        mock_payment.status = PaymentStatus.PENDING

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_session.execute.return_value = mock_result

        # Mock provider
        mock_provider = Mock()
        cancel_response = PaymentResponse(
            payment_id="pay_123",
            status=PaymentStatus.CANCELLED,
            amount=Decimal("100.00"),
            currency="BRL",
        )
        mock_provider.cancel_payment.return_value = cancel_response
        mock_factory.get_provider.return_value = mock_provider

        # Execute request
        response = self.client.post("/api/v1/payments/1/cancel")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data["status"] == "cancelled"

        # Verify provider was called
        mock_provider.cancel_payment.assert_called_once_with("pay_123")

        # Verify payment status was updated
        assert mock_payment.status == PaymentStatus.CANCELLED
        mock_session.commit.assert_called_once()

    @patch('backend.app.api.v1.routes.payments.get_db_session')
    def test_cancel_payment_already_completed(self, mock_get_db):
        """Test cancelling already completed payment."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock completed payment
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.status = PaymentStatus.COMPLETED

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_session.execute.return_value = mock_result

        # Execute request
        response = self.client.post("/api/v1/payments/1/cancel")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = response.json()
        assert "Cannot cancel" in response_data["detail"]


class TestRefundEndpoints:
    """Test refund endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch('backend.app.api.v1.routes.refunds.get_db_session')
    @patch('backend.app.api.v1.routes.refunds.PaymentProviderFactory')
    @patch('backend.app.api.v1.routes.refunds.PaymentLoggingService')
    def test_create_refund_success(self, mock_logging, mock_factory, mock_get_db):
        """Test successful refund creation."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock payment
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.provider_payment_id = "pay_123"
        mock_payment.provider_name = "mock"
        mock_payment.status = PaymentStatus.COMPLETED
        mock_payment.amount = Decimal("100.00")

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_session.execute.return_value = mock_result

        # Mock provider
        mock_provider = Mock()
        refund_response = RefundResponse(
            refund_id="ref_123",
            payment_id="pay_123",
            amount=Decimal("50.00"),
            currency="BRL",
            status="processing",
        )
        mock_provider.create_refund.return_value = refund_response
        mock_factory.get_provider.return_value = mock_provider

        # Test data
        refund_data = {
            "amount": "50.00",
            "reason": "Customer request",
        }

        # Execute request
        response = self.client.post("/api/v1/payments/1/refunds", json=refund_data)

        assert response.status_code == status.HTTP_201_CREATED

        response_data = response.json()
        assert response_data["provider_refund_id"] == "ref_123"
        assert response_data["payment_id"] == 1
        assert response_data["amount"] == "50.00"
        assert response_data["status"] == "processing"
        assert response_data["reason"] == "Customer request"

        # Verify provider was called
        mock_provider.create_refund.assert_called_once()

        # Verify refund was saved
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_create_refund_invalid_amount(self):
        """Test refund creation with invalid amount."""
        refund_data = {
            "amount": "invalid_amount",
            "reason": "Test refund",
        }

        response = self.client.post("/api/v1/payments/1/refunds", json=refund_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('backend.app.api.v1.routes.refunds.get_db_session')
    def test_create_refund_payment_not_found(self, mock_get_db):
        """Test refund creation when payment not found."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock payment not found
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Test data
        refund_data = {
            "amount": "50.00",
            "reason": "Customer request",
        }

        # Execute request
        response = self.client.post("/api/v1/payments/999/refunds", json=refund_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        response_data = response.json()
        assert "Payment not found" in response_data["detail"]

    @patch('backend.app.api.v1.routes.refunds.get_db_session')
    def test_get_refund_success(self, mock_get_db):
        """Test successful refund retrieval."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock refund
        mock_refund = Mock()
        mock_refund.id = 1
        mock_refund.provider_refund_id = "ref_123"
        mock_refund.payment_id = 1
        mock_refund.amount = Decimal("50.00")
        mock_refund.currency = "BRL"
        mock_refund.status = "completed"
        mock_refund.reason = "Customer request"
        mock_refund.metadata = {}
        mock_refund.provider_data = {}
        mock_refund.created_at = "2023-01-01T12:00:00Z"
        mock_refund.updated_at = "2023-01-01T12:00:00Z"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_refund
        mock_session.execute.return_value = mock_result

        # Execute request
        response = self.client.get("/api/v1/refunds/1")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data["id"] == 1
        assert response_data["provider_refund_id"] == "ref_123"
        assert response_data["amount"] == "50.00"
        assert response_data["status"] == "completed"


class TestWebhookEndpoints:
    """Test webhook endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch('backend.app.api.v1.routes.webhooks.process_payment_webhook')
    def test_stripe_webhook_success(self, mock_task):
        """Test successful Stripe webhook processing."""
        # Mock Celery task
        mock_task.delay.return_value = Mock(id="task_123")

        # Test data
        webhook_payload = {"event": "payment.completed", "payment_id": "pay_123"}
        headers = {"stripe-signature": "valid_signature"}

        # Execute request
        response = self.client.post(
            "/api/v1/webhooks/stripe",
            json=webhook_payload,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data["status"] == "received"
        assert response_data["task_id"] == "task_123"

        # Verify task was queued
        mock_task.delay.assert_called_once()

    def test_stripe_webhook_missing_signature(self):
        """Test Stripe webhook without signature header."""
        webhook_payload = {"event": "payment.completed"}

        response = self.client.post(
            "/api/v1/webhooks/stripe",
            json=webhook_payload
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response_data = response.json()
        assert "Missing signature" in response_data["detail"]

    @patch('backend.app.api.v1.routes.webhooks.process_payment_webhook')
    def test_mock_webhook_success(self, mock_task):
        """Test successful Mock webhook processing."""
        # Mock Celery task
        mock_task.delay.return_value = Mock(id="task_456")

        # Test data
        webhook_payload = {"event": "refund.completed", "refund_id": "ref_123"}

        # Execute request
        response = self.client.post(
            "/api/v1/webhooks/mock",
            json=webhook_payload
        )

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data["status"] == "received"
        assert response_data["task_id"] == "task_456"

        # Verify task was queued
        mock_task.delay.assert_called_once()

    def test_webhook_invalid_provider(self):
        """Test webhook for invalid provider."""
        webhook_payload = {"event": "payment.completed"}

        response = self.client.post(
            "/api/v1/webhooks/invalid_provider",
            json=webhook_payload
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
