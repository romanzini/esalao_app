"""
Payment Metrics Models

Database models for storing aggregated payment metrics data.
Optimized for fast retrieval and historical analysis.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.models.base import Base, IDMixin, TimestampMixin


class PaymentMetricsSnapshot(Base, IDMixin, TimestampMixin):
    """
    Aggregated payment metrics snapshot for specific time periods.

    Stores pre-calculated metrics to improve dashboard performance
    and enable historical trend analysis.
    """
    __tablename__ = "payment_metrics_snapshots"

    # Time period information
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # hour, day, week, month
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Optional provider filter
    provider_name: Mapped[str] = mapped_column(String(50), nullable=True)

    # Transaction counts
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    successful_transactions: Mapped[int] = mapped_column(Integer, default=0)
    failed_transactions: Mapped[int] = mapped_column(Integer, default=0)
    pending_transactions: Mapped[int] = mapped_column(Integer, default=0)

    # Financial metrics
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
    successful_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))

    # Performance metrics
    success_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    average_latency: Mapped[float] = mapped_column(Numeric(8, 3), default=0.0)

    # Detailed breakdowns (JSON)
    provider_metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"),
        default=dict
    )
    error_breakdown: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"),
        default=dict
    )

    # Metadata
    calculation_duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    data_source_version: Mapped[str] = mapped_column(String(10), default="1.0")

    def __repr__(self) -> str:
        return f"<PaymentMetricsSnapshot(period={self.period_type}, start={self.period_start}, provider={self.provider_name})>"


class ProviderPerformanceMetrics(Base, IDMixin, TimestampMixin):
    """
    Provider-specific performance metrics and SLA tracking.

    Tracks individual payment provider performance, uptime,
    and service level agreement compliance.
    """
    __tablename__ = "provider_performance_metrics"

    # Provider information
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    measurement_period: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly
    measurement_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Performance metrics
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0)
    timeout_requests: Mapped[int] = mapped_column(Integer, default=0)

    # Latency metrics (in milliseconds)
    avg_response_time: Mapped[float] = mapped_column(Numeric(8, 3), default=0.0)
    p50_response_time: Mapped[float] = mapped_column(Numeric(8, 3), default=0.0)
    p95_response_time: Mapped[float] = mapped_column(Numeric(8, 3), default=0.0)
    p99_response_time: Mapped[float] = mapped_column(Numeric(8, 3), default=0.0)

    # Availability metrics
    uptime_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    downtime_incidents: Mapped[int] = mapped_column(Integer, default=0)

    # Financial impact
    total_amount_processed: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0.00'))
    failed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0.00'))

    # Error analysis
    error_categories: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"),
        default=dict
    )

    # SLA compliance
    sla_target_uptime: Mapped[float] = mapped_column(Numeric(5, 2), default=99.5)
    sla_target_response_time: Mapped[float] = mapped_column(Numeric(8, 3), default=2000.0)
    sla_compliance: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"<ProviderPerformanceMetrics(provider={self.provider_name}, date={self.measurement_date})>"


class PaymentAlert(Base, IDMixin, TimestampMixin):
    """
    Payment system alerts and notifications.

    Tracks system alerts, anomalies, and performance issues
    for monitoring and incident response.
    """
    __tablename__ = "payment_alerts"

    # Alert information
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # error_rate, latency, downtime
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, acknowledged, resolved

    # Context
    provider_name: Mapped[str] = mapped_column(String(50), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True)
    actual_value: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True)

    # Description and details
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Metadata
    alert_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"),
        default=dict
    )

    # Resolution tracking
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[str] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PaymentAlert(type={self.alert_type}, severity={self.severity}, status={self.status})>"


# Create indexes for performance
Index("idx_metrics_snapshot_period", PaymentMetricsSnapshot.period_type, PaymentMetricsSnapshot.period_start)
Index("idx_metrics_snapshot_provider", PaymentMetricsSnapshot.provider_name, PaymentMetricsSnapshot.period_start)
Index("idx_provider_performance_date", ProviderPerformanceMetrics.provider_name, ProviderPerformanceMetrics.measurement_date)
Index("idx_payment_alerts_status", PaymentAlert.status, PaymentAlert.severity, PaymentAlert.created_at)
