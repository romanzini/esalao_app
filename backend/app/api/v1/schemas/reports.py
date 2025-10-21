"""
OpenAPI schemas for reporting endpoints.

This module contains Pydantic models specifically designed for
OpenAPI documentation of reporting endpoints.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field


class BookingMetricsSchema(BaseModel):
    """Schema for booking metrics."""

    total_bookings: int = Field(..., description="Total number of bookings", example=1250)
    confirmed_bookings: int = Field(..., description="Number of confirmed bookings", example=980)
    completed_bookings: int = Field(..., description="Number of completed bookings", example=875)
    cancelled_bookings: int = Field(..., description="Number of cancelled bookings", example=200)
    no_show_bookings: int = Field(..., description="Number of no-show bookings", example=75)
    total_revenue: Decimal = Field(..., description="Total revenue", example=87500.00)
    average_booking_value: Decimal = Field(..., description="Average booking value", example=125.50)
    completion_rate: float = Field(..., description="Completion rate percentage", example=89.3)
    no_show_rate: float = Field(..., description="No-show rate percentage", example=7.7)
    cancellation_rate: float = Field(..., description="Cancellation rate percentage", example=16.0)


class ProfessionalMetricsSchema(BaseModel):
    """Schema for professional performance metrics."""

    professional_id: int = Field(..., description="Professional ID", example=123)
    professional_name: str = Field(..., description="Professional name", example="Maria Silva")
    total_bookings: int = Field(..., description="Total bookings", example=145)
    completed_bookings: int = Field(..., description="Completed bookings", example=130)
    cancelled_bookings: int = Field(..., description="Cancelled bookings", example=10)
    no_show_bookings: int = Field(..., description="No-show bookings", example=5)
    total_revenue: Decimal = Field(..., description="Total revenue generated", example=18750.00)
    average_booking_value: Decimal = Field(..., description="Average booking value", example=144.23)
    completion_rate: float = Field(..., description="Completion rate percentage", example=89.7)
    client_satisfaction: Optional[float] = Field(None, description="Average client rating", example=4.8)
    utilization_rate: float = Field(..., description="Schedule utilization percentage", example=78.5)


class ServiceMetricsSchema(BaseModel):
    """Schema for service performance metrics."""

    service_id: int = Field(..., description="Service ID", example=456)
    service_name: str = Field(..., description="Service name", example="Haircut & Style")
    category: str = Field(..., description="Service category", example="haircut")
    total_bookings: int = Field(..., description="Total bookings", example=89)
    completed_bookings: int = Field(..., description="Completed bookings", example=78)
    total_revenue: Decimal = Field(..., description="Total revenue", example=11700.00)
    average_price: Decimal = Field(..., description="Average service price", example=150.00)
    demand_score: float = Field(..., description="Demand score (0-100)", example=85.6)
    popularity_rank: int = Field(..., description="Popularity rank within category", example=2)


class DashboardMetricsSchema(BaseModel):
    """Schema for dashboard metrics overview."""

    booking_metrics: BookingMetricsSchema = Field(..., description="Booking overview metrics")
    revenue_metrics: Dict[str, Union[Decimal, float]] = Field(
        ...,
        description="Revenue metrics",
        example={
            "total_revenue": 87500.00,
            "monthly_revenue": 28300.00,
            "revenue_growth": 12.5,
            "average_transaction": 125.50
        }
    )
    professional_metrics: Dict[str, Union[int, float]] = Field(
        ...,
        description="Professional metrics summary",
        example={
            "total_professionals": 15,
            "active_professionals": 12,
            "average_utilization": 78.5,
            "top_performer_revenue": 3450.00
        }
    )
    client_metrics: Dict[str, Union[int, float]] = Field(
        ...,
        description="Client metrics summary",
        example={
            "total_clients": 456,
            "new_clients": 28,
            "returning_clients": 428,
            "client_retention_rate": 85.2
        }
    )
    period_comparison: Dict[str, float] = Field(
        ...,
        description="Period-over-period comparison",
        example={
            "bookings_change": 8.5,
            "revenue_change": 12.3,
            "clients_change": 15.7
        }
    )


class RevenueBreakdownSchema(BaseModel):
    """Schema for revenue breakdown."""

    by_service_category: Dict[str, Decimal] = Field(
        ...,
        description="Revenue by service category",
        example={
            "haircut": 35000.00,
            "coloring": 28500.00,
            "styling": 15000.00,
            "treatment": 9000.00
        }
    )
    by_professional: Dict[str, Decimal] = Field(
        ...,
        description="Revenue by professional (top 10)",
        example={
            "Maria Silva": 12500.00,
            "João Santos": 11200.00,
            "Ana Costa": 10800.00
        }
    )
    by_time_period: Dict[str, Decimal] = Field(
        ...,
        description="Revenue by time period",
        example={
            "morning": 25000.00,
            "afternoon": 35000.00,
            "evening": 27500.00
        }
    )


class TrendDataPointSchema(BaseModel):
    """Schema for trend data point."""

    trend_date: date = Field(..., description="Date of the data point", example="2025-01-27")
    amount: Decimal = Field(..., description="Value for this date", example=2450.00)
    count: int = Field(..., description="Count for this date", example=18)
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata",
        example={"day_of_week": "Monday", "is_holiday": False}
    )


class TrendAnalysisSchema(BaseModel):
    """Schema for trend analysis."""

    data: List[TrendDataPointSchema] = Field(..., description="Trend data points")
    summary: Dict[str, Union[float, Decimal]] = Field(
        ...,
        description="Trend summary statistics",
        example={
            "total_value": 85000.00,
            "average_daily": 2833.33,
            "growth_rate": 12.5,
            "highest_day": 3450.00,
            "lowest_day": 1850.00
        }
    )
    period: Dict[str, date] = Field(
        ...,
        description="Analysis period",
        example={
            "start_date": "2025-01-01",
            "end_date": "2025-01-30"
        }
    )


class ReportFilterSchema(BaseModel):
    """Schema for report filtering parameters."""

    salon_id: Optional[int] = Field(None, description="Filter by salon ID", example=1)
    professional_id: Optional[int] = Field(None, description="Filter by professional ID", example=123)
    service_id: Optional[int] = Field(None, description="Filter by service ID", example=456)
    category: Optional[str] = Field(None, description="Filter by service category", example="haircut")
    start_date: Optional[date] = Field(None, description="Start date for filtering", example="2025-01-01")
    end_date: Optional[date] = Field(None, description="End date for filtering", example="2025-01-31")
    status: Optional[List[str]] = Field(
        None,
        description="Filter by booking status",
        example=["completed", "confirmed"]
    )
    client_type: Optional[str] = Field(None, description="Filter by client type", example="returning")


class ComparativeAnalysisSchema(BaseModel):
    """Schema for comparative analysis."""

    current_period: Dict[str, Union[int, float, Decimal]] = Field(
        ...,
        description="Current period metrics"
    )
    previous_period: Dict[str, Union[int, float, Decimal]] = Field(
        ...,
        description="Previous period metrics"
    )
    changes: Dict[str, float] = Field(
        ...,
        description="Percentage changes between periods",
        example={
            "bookings_change": 15.5,
            "revenue_change": 12.3,
            "completion_rate_change": 2.1
        }
    )
    significance: Dict[str, str] = Field(
        ...,
        description="Statistical significance of changes",
        example={
            "bookings": "significant",
            "revenue": "significant",
            "completion_rate": "not_significant"
        }
    )


class PerformanceRankingSchema(BaseModel):
    """Schema for performance ranking."""

    rankings: List[Dict[str, Union[int, str, float, Decimal]]] = Field(
        ...,
        description="Ranked list of performers",
        example=[
            {
                "rank": 1,
                "professional_id": 123,
                "name": "Maria Silva",
                "metric_value": 12500.00,
                "score": 95.8
            }
        ]
    )
    criteria: str = Field(..., description="Ranking criteria", example="total_revenue")
    period: Dict[str, date] = Field(..., description="Ranking period")


class PlatformOverviewSchema(BaseModel):
    """Schema for platform-wide overview metrics."""

    total_salons: int = Field(..., description="Total number of salons", example=45)
    active_salons: int = Field(..., description="Active salons", example=42)
    total_professionals: int = Field(..., description="Total professionals", example=234)
    total_clients: int = Field(..., description="Total clients", example=12456)
    total_bookings: int = Field(..., description="Total bookings", example=25678)
    total_revenue: Decimal = Field(..., description="Platform total revenue", example=2456789.00)
    growth_metrics: Dict[str, float] = Field(
        ...,
        description="Platform growth metrics",
        example={
            "salon_growth": 12.5,
            "professional_growth": 18.7,
            "booking_growth": 25.3,
            "revenue_growth": 22.1
        }
    )


class SalonComparisonSchema(BaseModel):
    """Schema for salon comparison metrics."""

    salon_id: int = Field(..., description="Salon ID", example=1)
    salon_name: str = Field(..., description="Salon name", example="Beauty Studio")
    metrics: Dict[str, Union[int, float, Decimal]] = Field(
        ...,
        description="Salon metrics",
        example={
            "total_bookings": 456,
            "total_revenue": 45600.00,
            "professionals_count": 8,
            "avg_booking_value": 100.00,
            "completion_rate": 89.5
        }
    )
    rank: int = Field(..., description="Salon rank in comparison", example=3)
    percentile: float = Field(..., description="Performance percentile", example=78.5)
