"""
Operational reports endpoints for salon dashboard and analytics.

This module provides endpoints for salon owners and managers to access
operational metrics, professional performance reports, and business analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.security.rbac import require_role
from backend.app.db.models.booking import Booking
from backend.app.db.models.payment import Payment
from backend.app.db.models.professional import Professional
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole
from backend.app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["📊 Reports - Operational"])


class BookingMetrics(BaseModel):
    """Booking metrics response model."""

    total_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    no_show_bookings: int
    confirmed_bookings: int
    completion_rate: float
    cancellation_rate: float
    no_show_rate: float
    avg_booking_value: Optional[float]
    total_revenue: float


class ProfessionalMetrics(BaseModel):
    """Professional performance metrics."""

    professional_id: int
    professional_name: str
    total_bookings: int
    completed_bookings: int
    completion_rate: float
    total_revenue: float
    avg_booking_value: Optional[float]
    unique_clients: int
    repeat_clients: int
    client_retention_rate: float


class ServiceMetrics(BaseModel):
    """Service performance metrics."""

    service_id: int
    service_name: str
    category: Optional[str]
    total_bookings: int
    completed_bookings: int
    total_revenue: float
    avg_price: float
    popularity_score: float


class DashboardMetrics(BaseModel):
    """Dashboard overview metrics."""

    period_start: datetime
    period_end: datetime
    booking_metrics: BookingMetrics
    top_professionals: List[ProfessionalMetrics]
    top_services: List[ServiceMetrics]
    revenue_trend: List[dict]
    booking_trend: List[dict]


@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Get dashboard metrics",
    description="""
    Get comprehensive dashboard metrics for salon operations.

    **Includes:**
    - Booking statistics and conversion rates
    - Top performing professionals
    - Most popular services
    - Revenue and booking trends

    **Time Period:** Configurable with start_date and end_date parameters.

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
async def get_dashboard_metrics(
    start_date: Optional[datetime] = Query(
        None,
        description="Start date for metrics (defaults to 30 days ago)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date for metrics (defaults to now)"
    ),
    salon_id: Optional[int] = Query(
        None,
        description="Salon ID (required for non-admin users)"
    ),
    current_user: dict = Depends(
        require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])
    ),
    db: AsyncSession = Depends(get_db),
) -> DashboardMetrics:
    """Get dashboard metrics for salon operations."""
    try:
        # Default time period - last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Determine salon_id based on user role
        if current_user["role"] != UserRole.ADMIN:
            if not salon_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="salon_id is required for non-admin users"
                )
            # TODO: Verify user has access to this salon

        # Build base booking query
        booking_query = db.query(Booking).filter(
            and_(
                Booking.scheduled_at >= start_date,
                Booking.scheduled_at <= end_date
            )
        )

        # Filter by salon if specified
        if salon_id:
            booking_query = booking_query.join(Professional).filter(
                Professional.salon_id == salon_id
            )

        # Get booking metrics
        bookings = await booking_query.all()

        total_bookings = len(bookings)
        completed_bookings = len([b for b in bookings if b.status == 'completed'])
        cancelled_bookings = len([b for b in bookings if b.status == 'cancelled'])
        no_show_bookings = len([b for b in bookings if b.status == 'no_show'])
        confirmed_bookings = len([b for b in bookings if b.status == 'confirmed'])

        completion_rate = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0
        cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
        no_show_rate = (no_show_bookings / total_bookings * 100) if total_bookings > 0 else 0

        # Calculate revenue from completed bookings
        completed_booking_prices = [b.service_price for b in bookings if b.status == 'completed']
        total_revenue = sum(completed_booking_prices)
        avg_booking_value = (total_revenue / completed_bookings) if completed_bookings > 0 else None

        booking_metrics = BookingMetrics(
            total_bookings=total_bookings,
            completed_bookings=completed_bookings,
            cancelled_bookings=cancelled_bookings,
            no_show_bookings=no_show_bookings,
            confirmed_bookings=confirmed_bookings,
            completion_rate=round(completion_rate, 2),
            cancellation_rate=round(cancellation_rate, 2),
            no_show_rate=round(no_show_rate, 2),
            avg_booking_value=round(avg_booking_value, 2) if avg_booking_value else None,
            total_revenue=round(total_revenue, 2)
        )

        # Get top professionals (placeholder - will implement detailed version)
        top_professionals = []

        # Get top services (placeholder - will implement detailed version)
        top_services = []

        # Get trends (placeholder - will implement detailed version)
        revenue_trend = []
        booking_trend = []

        return DashboardMetrics(
            period_start=start_date,
            period_end=end_date,
            booking_metrics=booking_metrics,
            top_professionals=top_professionals,
            top_services=top_services,
            revenue_trend=revenue_trend,
            booking_trend=booking_trend
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics"
        )


@router.get(
    "/bookings",
    response_model=BookingMetrics,
    summary="Get detailed booking metrics",
    description="""
    Get detailed booking statistics and performance metrics.

    **Metrics Include:**
    - Total bookings by status
    - Completion, cancellation, and no-show rates
    - Revenue metrics and average booking value
    - Time-based analysis

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
async def get_booking_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    salon_id: Optional[int] = Query(None, description="Filter by salon"),
    professional_id: Optional[int] = Query(None, description="Filter by professional"),
    service_id: Optional[int] = Query(None, description="Filter by service"),
    current_user: dict = Depends(
        require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])
    ),
    db: AsyncSession = Depends(get_db),
) -> BookingMetrics:
    """Get detailed booking metrics."""
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build query with filters
        query = db.query(Booking).filter(
            and_(
                Booking.scheduled_at >= start_date,
                Booking.scheduled_at <= end_date
            )
        )

        if salon_id:
            query = query.join(Professional).filter(Professional.salon_id == salon_id)

        if professional_id:
            query = query.filter(Booking.professional_id == professional_id)

        if service_id:
            query = query.filter(Booking.service_id == service_id)

        bookings = await query.all()

        # Calculate metrics
        total_bookings = len(bookings)
        if total_bookings == 0:
            return BookingMetrics(
                total_bookings=0,
                completed_bookings=0,
                cancelled_bookings=0,
                no_show_bookings=0,
                confirmed_bookings=0,
                completion_rate=0.0,
                cancellation_rate=0.0,
                no_show_rate=0.0,
                avg_booking_value=None,
                total_revenue=0.0
            )

        completed_bookings = len([b for b in bookings if b.status == 'completed'])
        cancelled_bookings = len([b for b in bookings if b.status == 'cancelled'])
        no_show_bookings = len([b for b in bookings if b.status == 'no_show'])
        confirmed_bookings = len([b for b in bookings if b.status == 'confirmed'])

        completion_rate = (completed_bookings / total_bookings * 100)
        cancellation_rate = (cancelled_bookings / total_bookings * 100)
        no_show_rate = (no_show_bookings / total_bookings * 100)

        # Revenue calculations
        completed_booking_prices = [b.service_price for b in bookings if b.status == 'completed']
        total_revenue = sum(completed_booking_prices)
        avg_booking_value = (total_revenue / completed_bookings) if completed_bookings > 0 else None

        return BookingMetrics(
            total_bookings=total_bookings,
            completed_bookings=completed_bookings,
            cancelled_bookings=cancelled_bookings,
            no_show_bookings=no_show_bookings,
            confirmed_bookings=confirmed_bookings,
            completion_rate=round(completion_rate, 2),
            cancellation_rate=round(cancellation_rate, 2),
            no_show_rate=round(no_show_rate, 2),
            avg_booking_value=round(avg_booking_value, 2) if avg_booking_value else None,
            total_revenue=round(total_revenue, 2)
        )

    except Exception as e:
        logger.error(f"Failed to get booking metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve booking metrics"
        )


@router.get(
    "/professionals",
    response_model=List[ProfessionalMetrics],
    summary="Get professional performance reports",
    description="""
    Get performance metrics for professionals.

    **Metrics Include:**
    - Booking statistics per professional
    - Revenue generated
    - Client acquisition and retention
    - Performance rankings

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
async def get_professional_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    salon_id: Optional[int] = Query(None, description="Filter by salon"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of professionals"),
    current_user: dict = Depends(
        require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])
    ),
    db: AsyncSession = Depends(get_db),
) -> List[ProfessionalMetrics]:
    """Get professional performance metrics."""
    try:
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get professionals with their bookings
        query = (
            db.query(Professional)
            .options(selectinload(Professional.bookings))
        )

        if salon_id:
            query = query.filter(Professional.salon_id == salon_id)

        professionals = await query.limit(limit).all()

        metrics_list = []

        for professional in professionals:
            # Filter bookings by date range
            period_bookings = [
                b for b in professional.bookings
                if start_date <= b.scheduled_at <= end_date
            ]

            total_bookings = len(period_bookings)
            completed_bookings = len([b for b in period_bookings if b.status == 'completed'])

            if total_bookings == 0:
                continue

            completion_rate = (completed_bookings / total_bookings * 100)

            # Revenue calculations
            completed_revenues = [b.service_price for b in period_bookings if b.status == 'completed']
            total_revenue = sum(completed_revenues)
            avg_booking_value = (total_revenue / completed_bookings) if completed_bookings > 0 else None

            # Client metrics
            unique_clients = len(set(b.client_id for b in period_bookings))

            # Simple repeat client calculation (clients with more than 1 booking)
            client_booking_counts = {}
            for booking in period_bookings:
                client_booking_counts[booking.client_id] = client_booking_counts.get(booking.client_id, 0) + 1

            repeat_clients = len([count for count in client_booking_counts.values() if count > 1])
            client_retention_rate = (repeat_clients / unique_clients * 100) if unique_clients > 0 else 0

            metrics = ProfessionalMetrics(
                professional_id=professional.id,
                professional_name=professional.name,
                total_bookings=total_bookings,
                completed_bookings=completed_bookings,
                completion_rate=round(completion_rate, 2),
                total_revenue=round(total_revenue, 2),
                avg_booking_value=round(avg_booking_value, 2) if avg_booking_value else None,
                unique_clients=unique_clients,
                repeat_clients=repeat_clients,
                client_retention_rate=round(client_retention_rate, 2)
            )

            metrics_list.append(metrics)

        # Sort by total revenue descending
        metrics_list.sort(key=lambda x: x.total_revenue, reverse=True)

        return metrics_list

    except Exception as e:
        logger.error(f"Failed to get professional metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve professional metrics"
        )


@router.get(
    "/services",
    response_model=List[ServiceMetrics],
    summary="Get service performance reports",
    description="""
    Get performance metrics for services.

    **Metrics Include:**
    - Booking frequency per service
    - Revenue generation
    - Popularity rankings
    - Category analysis

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
async def get_service_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    salon_id: Optional[int] = Query(None, description="Filter by salon"),
    category: Optional[str] = Query(None, description="Filter by service category"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of services"),
    current_user: dict = Depends(
        require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])
    ),
    db: AsyncSession = Depends(get_db),
) -> List[ServiceMetrics]:
    """Get service performance metrics."""
    try:
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get services with their bookings in the period
        query = db.query(Service)

        if salon_id:
            query = query.filter(Service.salon_id == salon_id)

        if category:
            query = query.filter(Service.category == category)

        services = await query.limit(limit).all()

        metrics_list = []

        for service in services:
            # Get bookings for this service in the period
            bookings = await db.query(Booking).filter(
                and_(
                    Booking.service_id == service.id,
                    Booking.scheduled_at >= start_date,
                    Booking.scheduled_at <= end_date
                )
            ).all()

            total_bookings = len(bookings)
            if total_bookings == 0:
                continue

            completed_bookings = len([b for b in bookings if b.status == 'completed'])

            # Revenue calculations
            completed_revenues = [b.service_price for b in bookings if b.status == 'completed']
            total_revenue = sum(completed_revenues)

            # Popularity score (simple metric based on booking frequency)
            popularity_score = total_bookings

            metrics = ServiceMetrics(
                service_id=service.id,
                service_name=service.name,
                category=service.category,
                total_bookings=total_bookings,
                completed_bookings=completed_bookings,
                total_revenue=round(total_revenue, 2),
                avg_price=float(service.price),
                popularity_score=popularity_score
            )

            metrics_list.append(metrics)

        # Sort by popularity score descending
        metrics_list.sort(key=lambda x: x.popularity_score, reverse=True)

        return metrics_list

    except Exception as e:
        logger.error(f"Failed to get service metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service metrics"
        )


@router.get(
    "/revenue/trend",
    summary="Get revenue trend analysis",
    description="""
    Get revenue trends over time with various aggregation options.

    **Aggregation Options:**
    - daily: Daily revenue data
    - weekly: Weekly aggregated revenue
    - monthly: Monthly aggregated revenue

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
async def get_revenue_trend(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    salon_id: Optional[int] = Query(None, description="Filter by salon"),
    aggregation: str = Query("daily", description="Aggregation level: daily, weekly, monthly"),
    current_user: dict = Depends(
        require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get revenue trend analysis."""
    try:
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build aggregation SQL based on the type
        if aggregation == "daily":
            date_trunc = "day"
        elif aggregation == "weekly":
            date_trunc = "week"
        elif aggregation == "monthly":
            date_trunc = "month"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid aggregation. Use: daily, weekly, monthly"
            )

        # Raw SQL query for revenue trend
        sql_query = text(f"""
            SELECT
                DATE_TRUNC('{date_trunc}', b.scheduled_at) as period,
                COUNT(*) as total_bookings,
                COUNT(CASE WHEN b.status = 'completed' THEN 1 END) as completed_bookings,
                SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END) as revenue
            FROM bookings b
            {"JOIN professionals p ON b.professional_id = p.id" if salon_id else ""}
            WHERE b.scheduled_at >= :start_date
                AND b.scheduled_at <= :end_date
                {f"AND p.salon_id = :salon_id" if salon_id else ""}
            GROUP BY DATE_TRUNC('{date_trunc}', b.scheduled_at)
            ORDER BY period
        """)

        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        if salon_id:
            params["salon_id"] = salon_id

        result = await db.execute(sql_query, params)
        rows = result.fetchall()

        trend_data = []
        for row in rows:
            trend_data.append({
                "period": row.period.isoformat(),
                "total_bookings": row.total_bookings,
                "completed_bookings": row.completed_bookings,
                "revenue": float(row.revenue),
                "completion_rate": round(
                    (row.completed_bookings / row.total_bookings * 100) if row.total_bookings > 0 else 0,
                    2
                )
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "aggregation": aggregation,
            "data": trend_data,
            "summary": {
                "total_periods": len(trend_data),
                "total_revenue": sum(item["revenue"] for item in trend_data),
                "total_bookings": sum(item["total_bookings"] for item in trend_data),
                "avg_revenue_per_period": (
                    sum(item["revenue"] for item in trend_data) / len(trend_data)
                ) if trend_data else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get revenue trend: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve revenue trend"
        )
