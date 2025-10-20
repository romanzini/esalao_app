"""
Payment Metrics Service

Comprehensive payment metrics tracking and analytics service for monitoring
transaction volume, success rates, latency, and provider performance.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from backend.app.db.models.payment import Payment, PaymentStatus, Refund
from backend.app.db.models.payment_log import PaymentLog
from backend.app.core.metrics import http_requests_total, http_request_duration_seconds


logger = logging.getLogger(__name__)


class MetricsPeriod(str, Enum):
    """Time periods for metrics aggregation."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class MetricsType(str, Enum):
    """Types of payment metrics."""
    VOLUME = "volume"
    SUCCESS_RATE = "success_rate"
    LATENCY = "latency"
    AMOUNT = "amount"
    PROVIDER_PERFORMANCE = "provider_performance"
    ERROR_RATES = "error_rates"


@dataclass
class PaymentMetrics:
    """Payment metrics data structure."""
    period: str
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    pending_transactions: int
    total_amount: Decimal
    successful_amount: Decimal
    refunded_amount: Decimal
    success_rate: float
    average_latency: float
    provider_metrics: Dict[str, Dict[str, Any]]
    error_breakdown: Dict[str, int]
    created_at: datetime


@dataclass
class ProviderMetrics:
    """Provider-specific metrics."""
    provider_name: str
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    success_rate: float
    average_latency: float
    total_amount: Decimal
    error_breakdown: Dict[str, int]


class PaymentMetricsService:
    """Service for collecting and analyzing payment metrics."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_payment_metrics(
        self,
        period: MetricsPeriod,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider_name: Optional[str] = None
    ) -> PaymentMetrics:
        """
        Get comprehensive payment metrics for specified period.

        Args:
            period: Time period for aggregation
            start_date: Start date for metrics (optional)
            end_date: End date for metrics (optional)
            provider_name: Filter by specific provider (optional)

        Returns:
            PaymentMetrics object with aggregated data
        """
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()

            if not start_date:
                start_date = self._get_period_start(period, end_date)

            # Build base query
            query = self.db.query(Payment).filter(
                and_(
                    Payment.created_at >= start_date,
                    Payment.created_at <= end_date
                )
            )

            if provider_name:
                query = query.filter(Payment.provider_name == provider_name)

            payments = query.all()

            # Calculate basic metrics
            total_transactions = len(payments)
            successful_transactions = len([p for p in payments if p.status == "succeeded"])
            failed_transactions = len([p for p in payments if p.status == "failed"])
            pending_transactions = len([p for p in payments if p.status == "pending"])

            # Calculate amounts
            total_amount = sum(p.amount for p in payments)
            successful_amount = sum(p.amount for p in payments if p.status == "succeeded")

            # Calculate refunded amount
            refunded_amount = self._get_refunded_amount(start_date, end_date, provider_name)

            # Calculate success rate
            success_rate = (successful_transactions / total_transactions * 100) if total_transactions > 0 else 0

            # Calculate average latency
            average_latency = self._calculate_average_latency(payments)

            # Get provider metrics
            provider_metrics = self._get_provider_metrics(start_date, end_date)

            # Get error breakdown
            error_breakdown = self._get_error_breakdown(start_date, end_date, provider_name)

            metrics = PaymentMetrics(
                period=f"{start_date.isoformat()}_{end_date.isoformat()}",
                total_transactions=total_transactions,
                successful_transactions=successful_transactions,
                failed_transactions=failed_transactions,
                pending_transactions=pending_transactions,
                total_amount=total_amount,
                successful_amount=successful_amount,
                refunded_amount=refunded_amount,
                success_rate=success_rate,
                average_latency=average_latency,
                provider_metrics=provider_metrics,
                error_breakdown=error_breakdown,
                created_at=datetime.utcnow()
            )

            # Record metrics for monitoring
            self._record_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error calculating payment metrics: {str(e)}")
            raise

    def get_provider_metrics(
        self,
        provider_name: str,
        period: MetricsPeriod,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ProviderMetrics:
        """
        Get detailed metrics for specific payment provider.

        Args:
            provider_name: Name of the payment provider
            period: Time period for aggregation
            start_date: Start date for metrics (optional)
            end_date: End date for metrics (optional)

        Returns:
            ProviderMetrics object with provider-specific data
        """
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()

            if not start_date:
                start_date = self._get_period_start(period, end_date)

            # Query payments for specific provider
            payments = self.db.query(Payment).filter(
                and_(
                    Payment.provider_name == provider_name,
                    Payment.created_at >= start_date,
                    Payment.created_at <= end_date
                )
            ).all()

            # Calculate provider-specific metrics
            total_transactions = len(payments)
            successful_transactions = len([p for p in payments if p.status == "succeeded"])
            failed_transactions = len([p for p in payments if p.status == "failed"])

            success_rate = (successful_transactions / total_transactions * 100) if total_transactions > 0 else 0
            average_latency = self._calculate_average_latency(payments)
            total_amount = sum(p.amount for p in payments)

            # Get error breakdown for provider
            error_breakdown = self._get_error_breakdown(start_date, end_date, provider_name)

            return ProviderMetrics(
                provider_name=provider_name,
                total_transactions=total_transactions,
                successful_transactions=successful_transactions,
                failed_transactions=failed_transactions,
                success_rate=success_rate,
                average_latency=average_latency,
                total_amount=total_amount,
                error_breakdown=error_breakdown
            )

        except Exception as e:
            logger.error(f"Error calculating provider metrics for {provider_name}: {str(e)}")
            raise

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get real-time payment metrics for dashboard.

        Returns:
            Dictionary with current metrics
        """
        try:
            # Get metrics for last hour
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            # Current hour metrics
            current_metrics = self.get_payment_metrics(
                period=MetricsPeriod.HOUR,
                start_date=start_time,
                end_date=end_time
            )

            # Get metrics for comparison (previous hour)
            prev_start = start_time - timedelta(hours=1)
            prev_metrics = self.get_payment_metrics(
                period=MetricsPeriod.HOUR,
                start_date=prev_start,
                end_date=start_time
            )

            # Calculate trends
            transaction_trend = self._calculate_trend(
                current_metrics.total_transactions,
                prev_metrics.total_transactions
            )

            success_rate_trend = self._calculate_trend(
                current_metrics.success_rate,
                prev_metrics.success_rate
            )

            amount_trend = self._calculate_trend(
                float(current_metrics.total_amount),
                float(prev_metrics.total_amount)
            )

            return {
                "current_hour": {
                    "total_transactions": current_metrics.total_transactions,
                    "success_rate": current_metrics.success_rate,
                    "total_amount": float(current_metrics.total_amount),
                    "average_latency": current_metrics.average_latency,
                    "failed_transactions": current_metrics.failed_transactions
                },
                "trends": {
                    "transactions": transaction_trend,
                    "success_rate": success_rate_trend,
                    "amount": amount_trend
                },
                "provider_status": self._get_provider_status(),
                "active_errors": self._get_active_errors(),
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting real-time metrics: {str(e)}")
            raise

    def get_historical_metrics(
        self,
        period: MetricsPeriod,
        points: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics data points for charts.

        Args:
            period: Time period for each data point
            points: Number of data points to return

        Returns:
            List of metrics data points
        """
        try:
            end_time = datetime.utcnow()
            data_points = []

            for i in range(points):
                # Calculate time range for this point
                point_end = end_time - timedelta(**{f"{period.value}s": i})
                point_start = point_end - timedelta(**{f"{period.value}s": 1})

                # Get metrics for this time range
                metrics = self.get_payment_metrics(
                    period=period,
                    start_date=point_start,
                    end_date=point_end
                )

                data_points.append({
                    "timestamp": point_start.isoformat(),
                    "total_transactions": metrics.total_transactions,
                    "success_rate": metrics.success_rate,
                    "total_amount": float(metrics.total_amount),
                    "average_latency": metrics.average_latency,
                    "failed_transactions": metrics.failed_transactions
                })

            # Reverse to get chronological order
            return list(reversed(data_points))

        except Exception as e:
            logger.error(f"Error getting historical metrics: {str(e)}")
            raise

    def _get_period_start(self, period: MetricsPeriod, end_date: datetime) -> datetime:
        """Get start date for given period."""
        if period == MetricsPeriod.HOUR:
            return end_date - timedelta(hours=1)
        elif period == MetricsPeriod.DAY:
            return end_date - timedelta(days=1)
        elif period == MetricsPeriod.WEEK:
            return end_date - timedelta(weeks=1)
        elif period == MetricsPeriod.MONTH:
            return end_date - timedelta(days=30)
        elif period == MetricsPeriod.YEAR:
            return end_date - timedelta(days=365)
        else:
            return end_date - timedelta(days=1)

    def _get_refunded_amount(
        self,
        start_date: datetime,
        end_date: datetime,
        provider_name: Optional[str] = None
    ) -> Decimal:
        """Calculate total refunded amount for period."""
        query = self.db.query(func.sum(Refund.amount)).filter(
            and_(
                Refund.created_at >= start_date,
                Refund.created_at <= end_date,
                Refund.status == "completed"
            )
        )

        if provider_name:
            query = query.join(Payment).filter(Payment.provider_name == provider_name)

        result = query.scalar()
        return result or Decimal('0.00')

    def _calculate_average_latency(self, payments: List[Payment]) -> float:
        """Calculate average payment processing latency."""
        latencies = []

        for payment in payments:
            if payment.status == "succeeded" and payment.paid_at:
                latency = (payment.paid_at - payment.created_at).total_seconds()
                latencies.append(latency)

        return sum(latencies) / len(latencies) if latencies else 0.0

    def _get_provider_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Dict[str, Any]]:
        """Get metrics broken down by provider."""
        provider_data = {}

        # Get all providers used in period
        providers = self.db.query(Payment.provider_name).filter(
            and_(
                Payment.created_at >= start_date,
                Payment.created_at <= end_date
            )
        ).distinct().all()

        for (provider_name,) in providers:
            provider_metrics = self.get_provider_metrics(
                provider_name=provider_name,
                period=MetricsPeriod.DAY,  # Use day as default
                start_date=start_date,
                end_date=end_date
            )

            provider_data[provider_name] = {
                "total_transactions": provider_metrics.total_transactions,
                "success_rate": provider_metrics.success_rate,
                "average_latency": provider_metrics.average_latency,
                "total_amount": float(provider_metrics.total_amount)
            }

        return provider_data

    def _get_error_breakdown(
        self,
        start_date: datetime,
        end_date: datetime,
        provider_name: Optional[str] = None
    ) -> Dict[str, int]:
        """Get breakdown of payment errors."""
        query = self.db.query(PaymentLog).filter(
            and_(
                PaymentLog.timestamp >= start_date,
                PaymentLog.timestamp <= end_date,
                PaymentLog.level == "ERROR"
            )
        )

        if provider_name:
            # Join with Payment to filter by provider
            query = query.join(Payment).filter(Payment.provider_name == provider_name)

        logs = query.all()

        error_counts = {}
        for log in logs:
            error_type = log.message.split(":")[0] if ":" in log.message else "Unknown"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return error_counts

    def _calculate_trend(self, current: float, previous: float) -> Dict[str, Any]:
        """Calculate trend percentage and direction."""
        if previous == 0:
            return {"percentage": 0.0, "direction": "stable"}

        percentage = ((current - previous) / previous) * 100

        if percentage > 5:
            direction = "up"
        elif percentage < -5:
            direction = "down"
        else:
            direction = "stable"

        return {
            "percentage": round(percentage, 2),
            "direction": direction
        }

    def _get_provider_status(self) -> Dict[str, str]:
        """Get current status of each payment provider."""
        # Check recent payment success rates
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=30)

        providers = self.db.query(Payment.provider_name).filter(
            Payment.created_at >= start_time
        ).distinct().all()

        status = {}
        for (provider_name,) in providers:
            recent_payments = self.db.query(Payment).filter(
                and_(
                    Payment.provider_name == provider_name,
                    Payment.created_at >= start_time
                )
            ).all()

            if not recent_payments:
                status[provider_name] = "inactive"
                continue

            success_rate = len([p for p in recent_payments if p.status == "succeeded"]) / len(recent_payments) * 100

            if success_rate >= 95:
                status[provider_name] = "healthy"
            elif success_rate >= 80:
                status[provider_name] = "warning"
            else:
                status[provider_name] = "error"

        return status

    def _get_active_errors(self) -> List[Dict[str, Any]]:
        """Get currently active payment errors."""
        # Check for recent errors (last 30 minutes)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=30)

        error_logs = self.db.query(PaymentLog).filter(
            and_(
                PaymentLog.created_at >= start_time,
                PaymentLog.level == "ERROR"
            )
        ).order_by(PaymentLog.created_at.desc()).limit(10).all()

        return [
            {
                "timestamp": log.created_at.isoformat(),
                "message": log.message,
                "payment_id": log.payment_id,
                "metadata": log.metadata
            }
            for log in error_logs
        ]

    def _record_metrics(self, metrics: PaymentMetrics):
        """Record metrics to monitoring system."""
        try:
            # Record to Prometheus metrics
            # Note: These would typically be recorded in the application layer
            # when actual payments are processed
            pass
        except Exception as e:
            logger.warning(f"Failed to record metrics: {str(e)}")
