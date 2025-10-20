"""
Payment Metrics API Routes

Basic endpoints for payment analytics and metrics visualization.
Simplified implementation for TASK-0212 completion.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.db.session import get_sync_db_session
from backend.app.domain.payments.services.metrics_service import (
    PaymentMetricsService,
    MetricsPeriod
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics", tags=["Payment Metrics"])


# Response Models
class PaymentMetricsResponse(BaseModel):
    """Response model for payment metrics."""
    period: str
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    pending_transactions: int
    total_amount: float
    successful_amount: float
    refunded_amount: float
    success_rate: float
    average_latency: float
    provider_metrics: Dict[str, Dict[str, Any]]
    error_breakdown: Dict[str, int]
    created_at: datetime


@router.get("/overview", response_model=PaymentMetricsResponse)
def get_payment_metrics_overview(
    period: MetricsPeriod = Query(MetricsPeriod.DAY, description="Time period for metrics"),
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    provider_name: Optional[str] = Query(None, description="Filter by provider"),
    db: Session = Depends(get_sync_db_session)
):
    """
    Get comprehensive payment metrics overview.

    Provides aggregated payment data including transaction counts, success rates,
    amounts, latency, and error breakdowns for the specified period.
    """
    try:
        logger.info("Getting payment metrics overview")

        metrics_service = PaymentMetricsService(db)
        metrics = metrics_service.get_payment_metrics(
            period=period,
            start_date=start_date,
            end_date=end_date,
            provider_name=provider_name
        )

        return PaymentMetricsResponse(
            period=metrics.period,
            total_transactions=metrics.total_transactions,
            successful_transactions=metrics.successful_transactions,
            failed_transactions=metrics.failed_transactions,
            pending_transactions=metrics.pending_transactions,
            total_amount=float(metrics.total_amount),
            successful_amount=float(metrics.successful_amount),
            refunded_amount=float(metrics.refunded_amount),
            success_rate=metrics.success_rate,
            average_latency=metrics.average_latency,
            provider_metrics=metrics.provider_metrics,
            error_breakdown=metrics.error_breakdown,
            created_at=metrics.created_at
        )

    except Exception as e:
        logger.error(f"Error getting payment metrics overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve payment metrics")


@router.get("/realtime")
def get_real_time_metrics(db: Session = Depends(get_sync_db_session)):
    """
    Get real-time payment metrics for dashboard.

    Provides current metrics, trends, provider status, and active errors
    for real-time monitoring and alerting.
    """
    try:
        logger.info("Getting real-time metrics")

        metrics_service = PaymentMetricsService(db)
        metrics = metrics_service.get_real_time_metrics()

        return metrics

    except Exception as e:
        logger.error(f"Error getting real-time metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve real-time metrics")


@router.get("/providers")
def get_available_providers(db: Session = Depends(get_sync_db_session)):
    """
    Get list of available payment providers with basic stats.
    """
    try:
        logger.info("Getting available providers")

        metrics_service = PaymentMetricsService(db)

        # Get providers used in last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        # Get overall metrics to extract provider data
        overall_metrics = metrics_service.get_payment_metrics(
            period=MetricsPeriod.MONTH,
            start_date=start_date,
            end_date=end_date
        )

        # Get current provider status
        provider_status = metrics_service._get_provider_status()

        providers = []
        for provider_name, metrics in overall_metrics.provider_metrics.items():
            providers.append({
                "name": provider_name,
                "status": provider_status.get(provider_name, "unknown"),
                "total_transactions": metrics["total_transactions"],
                "success_rate": metrics["success_rate"],
                "total_amount": metrics["total_amount"]
            })

        return {
            "providers": providers,
            "total_providers": len(providers),
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting available providers: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve providers")
