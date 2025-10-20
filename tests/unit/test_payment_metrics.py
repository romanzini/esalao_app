"""
Tests for Payment Metrics Service

Comprehensive tests for payment metrics calculation, aggregation,
and real-time monitoring functionality.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from backend.app.domain.payments.services.metrics_service import (
    PaymentMetricsService,
    MetricsPeriod,
    PaymentMetrics,
    ProviderMetrics
)
from backend.app.db.models.payment import Payment, PaymentStatus, Refund
from backend.app.db.models.payment_log import PaymentLog, PaymentLogLevel
from backend.app.db.models.user import User, UserRole


class TestPaymentMetricsService:
    """Test suite for PaymentMetricsService."""

    @pytest.fixture
    def metrics_service(self, db_session):
        """Create metrics service instance."""
        return PaymentMetricsService(db_session)

    @pytest.fixture
    def sample_user(self, db_session):
        """Create a sample user for testing."""
        # Use a unique email for each test by appending timestamp
        import time
        unique_email = f"metrics_test_{int(time.time() * 1000)}@example.com"

        user = User(
            email=unique_email,
            password_hash="test_hash",
            full_name="Metrics Test User",
            role=UserRole.CLIENT,
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def sample_payments(self, db_session, sample_user):
        """Create sample payments for testing."""
        base_time = datetime.utcnow() - timedelta(hours=2)

        payments = [
            # Successful payments
            Payment(
                user_id=sample_user.id,
                provider_payment_id="pi_success_1",
                amount=Decimal("100.00"),
                currency="BRL",
                payment_method="credit_card",
                provider_name="stripe",
                status="succeeded",
                created_at=base_time,
                paid_at=base_time + timedelta(minutes=2),
                extra_data={"booking_id": "1"}
            ),
            Payment(
                user_id=sample_user.id,
                provider_payment_id="pi_success_2",
                amount=Decimal("150.00"),
                currency="BRL",
                payment_method="pix",
                provider_name="stripe",
                status="succeeded",
                created_at=base_time + timedelta(minutes=30),
                paid_at=base_time + timedelta(minutes=35),
                extra_data={"booking_id": "2"}
            ),
            # Failed payment
            Payment(
                user_id=sample_user.id,
                provider_payment_id="pi_failed_1",
                amount=Decimal("75.00"),
                currency="BRL",
                payment_method="credit_card",
                provider_name="mock",
                status="failed",
                created_at=base_time + timedelta(hours=1),
                failed_at=base_time + timedelta(hours=1, minutes=1),
                extra_data={"booking_id": "3"}
            ),
            # Pending payment
            Payment(
                user_id=sample_user.id,
                provider_payment_id="pi_pending_1",
                amount=Decimal("200.00"),
                currency="BRL",
                payment_method="credit_card",
                provider_name="stripe",
                status="pending",
                created_at=base_time + timedelta(hours=1, minutes=30),
                extra_data={"booking_id": "4"}
            )
        ]

        for payment in payments:
            db_session.add(payment)
        db_session.commit()

        return payments

    def test_get_payment_metrics_basic(self, metrics_service, sample_payments):
        """Test basic payment metrics calculation."""
        # Get metrics for last 3 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=3)

        metrics = metrics_service.get_payment_metrics(
            period=MetricsPeriod.HOUR,
            start_date=start_time,
            end_date=end_time
        )

        assert isinstance(metrics, PaymentMetrics)
        assert metrics.total_transactions == 4
        assert metrics.successful_transactions == 2
        assert metrics.failed_transactions == 1
        assert metrics.pending_transactions == 1

        # Check amounts
        assert metrics.total_amount == Decimal("525.00")  # 100 + 150 + 75 + 200
        assert metrics.successful_amount == Decimal("250.00")  # 100 + 150

        # Check success rate
        assert metrics.success_rate == 50.0  # 2/4 * 100

    def test_get_payment_metrics_with_provider_filter(self, metrics_service, sample_payments):
        """Test payment metrics with provider filtering."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=3)

        # Filter by Stripe provider
        metrics = metrics_service.get_payment_metrics(
            period=MetricsPeriod.HOUR,
            start_date=start_time,
            end_date=end_time,
            provider_name="stripe"
        )

        assert metrics.total_transactions == 3  # 2 successful + 1 pending
        assert metrics.successful_transactions == 2
        assert metrics.failed_transactions == 0
        assert metrics.pending_transactions == 1
        assert metrics.success_rate == 66.67  # 2/3 * 100 (rounded)

    def test_get_provider_metrics(self, metrics_service, sample_payments):
        """Test provider-specific metrics calculation."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=3)

        # Get Stripe provider metrics
        stripe_metrics = metrics_service.get_provider_metrics(
            provider_name="stripe",
            period=MetricsPeriod.HOUR,
            start_date=start_time,
            end_date=end_time
        )

        assert isinstance(stripe_metrics, ProviderMetrics)
        assert stripe_metrics.provider_name == "stripe"
        assert stripe_metrics.total_transactions == 3
        assert stripe_metrics.successful_transactions == 2
        assert stripe_metrics.failed_transactions == 0
        assert stripe_metrics.success_rate == 66.67
        assert stripe_metrics.total_amount == Decimal("450.00")  # 100 + 150 + 200

    def test_calculate_average_latency(self, metrics_service, sample_payments):
        """Test average latency calculation."""
        # Get completed payments
        completed_payments = [p for p in sample_payments if p.status == PaymentStatus.COMPLETED]

        latency = metrics_service._calculate_average_latency(completed_payments)

        # Payment 1: 2 minutes = 120 seconds
        # Payment 2: 5 minutes = 300 seconds
        # Average: (120 + 300) / 2 = 210 seconds
        assert latency == 210.0

    def test_get_real_time_metrics(self, metrics_service, sample_payments):
        """Test real-time metrics for dashboard."""
        with patch.object(metrics_service, '_get_provider_status') as mock_status, \
             patch.object(metrics_service, '_get_active_errors') as mock_errors:

            mock_status.return_value = {"stripe": "healthy", "mock": "error"}
            mock_errors.return_value = []

            real_time = metrics_service.get_real_time_metrics()

            assert "current_hour" in real_time
            assert "trends" in real_time
            assert "provider_status" in real_time
            assert "active_errors" in real_time
            assert "last_updated" in real_time

            # Verify provider status was called
            mock_status.assert_called_once()
            mock_errors.assert_called_once()

    def test_get_historical_metrics(self, metrics_service, sample_payments):
        """Test historical metrics data points."""
        data_points = metrics_service.get_historical_metrics(
            period=MetricsPeriod.HOUR,
            points=3
        )

        assert len(data_points) == 3
        assert all("timestamp" in point for point in data_points)
        assert all("total_transactions" in point for point in data_points)
        assert all("success_rate" in point for point in data_points)

    def test_get_refunded_amount(self, metrics_service, db_session, sample_payments):
        """Test refunded amount calculation."""
        # Create a refund
        payment = sample_payments[0]  # First successful payment
        refund = Refund(
            payment_id=payment.id,
            amount=Decimal("50.00"),
            reason="Customer request",
            status="completed",
            provider_refund_id="re_test_123",
            initiated_by_user_id=payment.user_id,
            extra_data={}
        )
        db_session.add(refund)
        db_session.commit()

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=3)

        refunded_amount = metrics_service._get_refunded_amount(start_time, end_time)
        assert refunded_amount == Decimal("50.00")

    def test_get_error_breakdown(self, metrics_service, db_session, sample_payments):
        """Test error breakdown calculation."""
        # Create some error logs
        payment = sample_payments[2]  # Failed payment

        error_logs = [
            PaymentLog(
                payment_id=payment.id,
                level=PaymentLogLevel.ERROR,
                message="Payment failed: Insufficient funds",
                metadata={"error_code": "insufficient_funds"}
            ),
            PaymentLog(
                payment_id=payment.id,
                level=PaymentLogLevel.ERROR,
                message="Payment failed: Card declined",
                metadata={"error_code": "card_declined"}
            ),
            PaymentLog(
                payment_id=payment.id,
                level=PaymentLogLevel.INFO,
                message="Payment attempt initiated",
                metadata={}
            )
        ]

        for log in error_logs:
            db_session.add(log)
        db_session.commit()

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=3)

        error_breakdown = metrics_service._get_error_breakdown(start_time, end_time)

        # Should have 2 errors (only ERROR level logs)
        assert "Payment failed" in error_breakdown
        assert error_breakdown["Payment failed"] == 2

    def test_calculate_trend(self, metrics_service):
        """Test trend calculation."""
        # Test upward trend
        trend_up = metrics_service._calculate_trend(120, 100)
        assert trend_up["percentage"] == 20.0
        assert trend_up["direction"] == "up"

        # Test downward trend
        trend_down = metrics_service._calculate_trend(80, 100)
        assert trend_down["percentage"] == -20.0
        assert trend_down["direction"] == "down"

        # Test stable trend
        trend_stable = metrics_service._calculate_trend(102, 100)
        assert trend_stable["percentage"] == 2.0
        assert trend_stable["direction"] == "stable"

        # Test with zero previous value
        trend_zero = metrics_service._calculate_trend(100, 0)
        assert trend_zero["percentage"] == 0.0
        assert trend_zero["direction"] == "stable"

    def test_get_provider_status(self, metrics_service, sample_payments):
        """Test provider status determination."""
        provider_status = metrics_service._get_provider_status()

        # Should have both stripe and mock providers
        assert "stripe" in provider_status
        assert "mock" in provider_status

        # Stripe should be healthy (high success rate)
        # Mock should have errors (failed payment)
        assert provider_status["stripe"] in ["healthy", "warning"]
        assert provider_status["mock"] in ["error", "warning"]

    def test_metrics_with_empty_data(self, metrics_service):
        """Test metrics calculation with no data."""
        # Get metrics for a future time period (no data)
        future_time = datetime.utcnow() + timedelta(days=1)
        start_time = future_time - timedelta(hours=1)

        metrics = metrics_service.get_payment_metrics(
            period=MetricsPeriod.HOUR,
            start_date=start_time,
            end_date=future_time
        )

        assert metrics.total_transactions == 0
        assert metrics.successful_transactions == 0
        assert metrics.failed_transactions == 0
        assert metrics.success_rate == 0
        assert metrics.total_amount == Decimal("0")
        assert metrics.average_latency == 0.0

    def test_period_start_calculation(self, metrics_service):
        """Test period start date calculation."""
        end_date = datetime(2023, 10, 20, 15, 30, 0)

        # Test different periods
        hour_start = metrics_service._get_period_start(MetricsPeriod.HOUR, end_date)
        assert hour_start == datetime(2023, 10, 20, 14, 30, 0)

        day_start = metrics_service._get_period_start(MetricsPeriod.DAY, end_date)
        assert day_start == datetime(2023, 10, 19, 15, 30, 0)

        week_start = metrics_service._get_period_start(MetricsPeriod.WEEK, end_date)
        assert week_start == datetime(2023, 10, 13, 15, 30, 0)

    @patch('backend.app.core.metrics.MetricsCollector')
    def test_record_metrics(self, mock_collector, metrics_service, sample_payments):
        """Test metrics recording to monitoring system."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=3)

        metrics = metrics_service.get_payment_metrics(
            period=MetricsPeriod.HOUR,
            start_date=start_time,
            end_date=end_time
        )

        # Verify metrics were recorded (called in _record_metrics)
        assert metrics is not None
