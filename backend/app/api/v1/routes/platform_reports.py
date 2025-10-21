"""
Platform-level reporting endpoints for administrators.

This module provides endpoints for platform administrators to access
system-wide analytics, salon performance comparisons, and global metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.security.rbac import require_role
from backend.app.db.models.booking import Booking
from backend.app.db.models.payment import Payment
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole
from backend.app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform-reports", tags=["📊 Reports - Platform (Admin)"])


class SalonPerformance(BaseModel):
    """Salon performance metrics for platform analysis."""

    salon_id: int
    salon_name: str
    total_bookings: int
    completed_bookings: int
    completion_rate: float
    total_revenue: float
    avg_booking_value: Optional[float]
    professional_count: int
    service_count: int
    client_count: int
    growth_rate: Optional[float]


class PlatformMetrics(BaseModel):
    """Platform-wide metrics overview."""

    total_salons: int
    active_salons: int
    total_professionals: int
    total_services: int
    total_bookings: int
    total_revenue: float
    platform_growth_rate: float
    avg_salon_revenue: float
    top_performing_salons: List[SalonPerformance]


class CategoryAnalytics(BaseModel):
    """Service category performance analytics."""

    category: str
    total_services: int
    total_bookings: int
    total_revenue: float
    avg_price: float
    popularity_score: float
    salon_adoption_rate: float


class UserAnalytics(BaseModel):
    """User behavior and engagement analytics."""

    total_users: int
    active_users_30d: int
    new_users_30d: int
    user_retention_rate: float
    avg_bookings_per_user: float
    user_lifetime_value: float


@router.get(
    "/overview",
    response_model=PlatformMetrics,
    summary="Get platform overview metrics",
    description="""
    Get comprehensive platform-wide metrics and analytics.

    **Admin Only Endpoint**

    **Includes:**
    - Total platform statistics
    - Growth metrics
    - Top performing salons
    - System health indicators

    **Authentication Required:** Admin only
    """,
)
async def get_platform_overview(
    start_date: Optional[datetime] = Query(
        None,
        description="Start date for metrics (defaults to 30 days ago)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date for metrics (defaults to now)"
    ),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> PlatformMetrics:
    """Get platform overview metrics."""
    try:
        # Default time period
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get total counts
        total_salons = await db.query(func.count(Salon.id)).scalar()

        # Active salons (have at least one booking in the period)
        active_salons_query = text("""
            SELECT COUNT(DISTINCT s.id)
            FROM salons s
            JOIN professionals p ON s.id = p.salon_id
            JOIN bookings b ON p.id = b.professional_id
            WHERE b.scheduled_at >= :start_date AND b.scheduled_at <= :end_date
        """)
        active_salons_result = await db.execute(
            active_salons_query,
            {"start_date": start_date, "end_date": end_date}
        )
        active_salons = active_salons_result.scalar()

        total_professionals = await db.query(func.count(Professional.id)).scalar()
        total_services = await db.query(func.count(Service.id)).scalar()

        # Booking metrics for the period
        booking_query = db.query(Booking).filter(
            and_(
                Booking.scheduled_at >= start_date,
                Booking.scheduled_at <= end_date
            )
        )

        total_bookings = await booking_query.count()

        # Revenue from completed bookings
        completed_bookings = await booking_query.filter(
            Booking.status == 'completed'
        ).all()

        total_revenue = sum(b.service_price for b in completed_bookings)

        # Platform growth rate (compare with previous period)
        previous_start = start_date - (end_date - start_date)
        previous_end = start_date

        previous_bookings = await db.query(func.count(Booking.id)).filter(
            and_(
                Booking.scheduled_at >= previous_start,
                Booking.scheduled_at <= previous_end
            )
        ).scalar()

        platform_growth_rate = (
            ((total_bookings - previous_bookings) / previous_bookings * 100)
            if previous_bookings > 0 else 0
        )

        avg_salon_revenue = total_revenue / active_salons if active_salons > 0 else 0

        # Get top performing salons
        top_salons_query = text("""
            SELECT
                s.id as salon_id,
                s.name as salon_name,
                COUNT(b.id) as total_bookings,
                COUNT(CASE WHEN b.status = 'completed' THEN 1 END) as completed_bookings,
                SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END) as total_revenue,
                COUNT(DISTINCT p.id) as professional_count,
                COUNT(DISTINCT srv.id) as service_count,
                COUNT(DISTINCT b.client_id) as client_count
            FROM salons s
            LEFT JOIN professionals p ON s.id = p.salon_id
            LEFT JOIN bookings b ON p.id = b.professional_id
                AND b.scheduled_at >= :start_date
                AND b.scheduled_at <= :end_date
            LEFT JOIN services srv ON s.id = srv.salon_id
            GROUP BY s.id, s.name
            HAVING COUNT(b.id) > 0
            ORDER BY total_revenue DESC
            LIMIT 10
        """)

        top_salons_result = await db.execute(
            top_salons_query,
            {"start_date": start_date, "end_date": end_date}
        )

        top_performing_salons = []
        for row in top_salons_result.fetchall():
            completion_rate = (
                (row.completed_bookings / row.total_bookings * 100)
                if row.total_bookings > 0 else 0
            )
            avg_booking_value = (
                (row.total_revenue / row.completed_bookings)
                if row.completed_bookings > 0 else None
            )

            salon_perf = SalonPerformance(
                salon_id=row.salon_id,
                salon_name=row.salon_name,
                total_bookings=row.total_bookings,
                completed_bookings=row.completed_bookings,
                completion_rate=round(completion_rate, 2),
                total_revenue=float(row.total_revenue),
                avg_booking_value=round(avg_booking_value, 2) if avg_booking_value else None,
                professional_count=row.professional_count,
                service_count=row.service_count,
                client_count=row.client_count,
                growth_rate=None  # Would need additional calculation
            )
            top_performing_salons.append(salon_perf)

        return PlatformMetrics(
            total_salons=total_salons,
            active_salons=active_salons,
            total_professionals=total_professionals,
            total_services=total_services,
            total_bookings=total_bookings,
            total_revenue=round(total_revenue, 2),
            platform_growth_rate=round(platform_growth_rate, 2),
            avg_salon_revenue=round(avg_salon_revenue, 2),
            top_performing_salons=top_performing_salons
        )

    except Exception as e:
        logger.error(f"Failed to get platform overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform overview"
        )


@router.get(
    "/salons/performance",
    response_model=List[SalonPerformance],
    summary="Get salon performance comparison",
    description="""
    Get detailed performance metrics for all salons.

    **Admin Only Endpoint**

    **Includes:**
    - Revenue and booking metrics per salon
    - Completion rates and efficiency
    - Growth comparisons
    - Resource utilization

    **Authentication Required:** Admin only
    """,
)
async def get_salon_performance_comparison(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of salons"),
    sort_by: str = Query("revenue", description="Sort by: revenue, bookings, completion_rate"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> List[SalonPerformance]:
    """Get salon performance comparison."""
    try:
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Validate sort_by parameter
        valid_sorts = ["revenue", "bookings", "completion_rate"]
        if sort_by not in valid_sorts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by. Use: {', '.join(valid_sorts)}"
            )

        # SQL query for salon performance
        order_by_mapping = {
            "revenue": "total_revenue DESC",
            "bookings": "total_bookings DESC",
            "completion_rate": "completion_rate DESC"
        }

        salon_performance_query = text(f"""
            SELECT
                s.id as salon_id,
                s.name as salon_name,
                COUNT(b.id) as total_bookings,
                COUNT(CASE WHEN b.status = 'completed' THEN 1 END) as completed_bookings,
                CASE
                    WHEN COUNT(b.id) > 0 THEN
                        (COUNT(CASE WHEN b.status = 'completed' THEN 1 END)::float / COUNT(b.id) * 100)
                    ELSE 0
                END as completion_rate,
                COALESCE(SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END), 0) as total_revenue,
                COUNT(DISTINCT p.id) as professional_count,
                COUNT(DISTINCT srv.id) as service_count,
                COUNT(DISTINCT b.client_id) as client_count
            FROM salons s
            LEFT JOIN professionals p ON s.id = p.salon_id
            LEFT JOIN services srv ON s.id = srv.salon_id
            LEFT JOIN bookings b ON p.id = b.professional_id
                AND b.scheduled_at >= :start_date
                AND b.scheduled_at <= :end_date
            GROUP BY s.id, s.name
            ORDER BY {order_by_mapping[sort_by]}
            LIMIT :limit
        """)

        result = await db.execute(
            salon_performance_query,
            {
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        )

        salon_performances = []
        for row in result.fetchall():
            avg_booking_value = (
                (row.total_revenue / row.completed_bookings)
                if row.completed_bookings > 0 else None
            )

            salon_perf = SalonPerformance(
                salon_id=row.salon_id,
                salon_name=row.salon_name,
                total_bookings=row.total_bookings,
                completed_bookings=row.completed_bookings,
                completion_rate=round(float(row.completion_rate), 2),
                total_revenue=float(row.total_revenue),
                avg_booking_value=round(avg_booking_value, 2) if avg_booking_value else None,
                professional_count=row.professional_count,
                service_count=row.service_count,
                client_count=row.client_count,
                growth_rate=None  # Would require additional query for growth calculation
            )
            salon_performances.append(salon_perf)

        return salon_performances

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get salon performance comparison: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve salon performance comparison"
        )


@router.get(
    "/categories/analytics",
    response_model=List[CategoryAnalytics],
    summary="Get service category analytics",
    description="""
    Get analytics for service categories across the platform.

    **Admin Only Endpoint**

    **Includes:**
    - Category popularity and revenue
    - Adoption rates across salons
    - Pricing analysis
    - Market trends

    **Authentication Required:** Admin only
    """,
)
async def get_category_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> List[CategoryAnalytics]:
    """Get service category analytics."""
    try:
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get total salon count for adoption rate calculation
        total_salons = await db.query(func.count(Salon.id)).scalar()

        # Category analytics query
        category_query = text("""
            SELECT
                s.category,
                COUNT(DISTINCT s.id) as total_services,
                COUNT(b.id) as total_bookings,
                COALESCE(SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END), 0) as total_revenue,
                AVG(s.price) as avg_price,
                COUNT(DISTINCT s.salon_id) as salon_count
            FROM services s
            LEFT JOIN bookings b ON s.id = b.service_id
                AND b.scheduled_at >= :start_date
                AND b.scheduled_at <= :end_date
            WHERE s.category IS NOT NULL
            GROUP BY s.category
            ORDER BY total_revenue DESC
        """)

        result = await db.execute(
            category_query,
            {"start_date": start_date, "end_date": end_date}
        )

        category_analytics = []
        for row in result.fetchall():
            popularity_score = row.total_bookings  # Simple popularity metric
            salon_adoption_rate = (
                (row.salon_count / total_salons * 100) if total_salons > 0 else 0
            )

            analytics = CategoryAnalytics(
                category=row.category,
                total_services=row.total_services,
                total_bookings=row.total_bookings,
                total_revenue=float(row.total_revenue),
                avg_price=float(row.avg_price) if row.avg_price else 0.0,
                popularity_score=popularity_score,
                salon_adoption_rate=round(salon_adoption_rate, 2)
            )
            category_analytics.append(analytics)

        return category_analytics

    except Exception as e:
        logger.error(f"Failed to get category analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category analytics"
        )


@router.get(
    "/users/analytics",
    response_model=UserAnalytics,
    summary="Get user behavior analytics",
    description="""
    Get user engagement and behavior analytics across the platform.

    **Admin Only Endpoint**

    **Includes:**
    - User acquisition and retention
    - Engagement metrics
    - Lifetime value analysis
    - Usage patterns

    **Authentication Required:** Admin only
    """,
)
async def get_user_analytics(
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserAnalytics:
    """Get user behavior analytics."""
    try:
        # Time periods
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)

        # Total users
        total_users = await db.query(func.count(User.id)).filter(
            User.role == UserRole.CLIENT
        ).scalar()

        # Active users (users with bookings in last 30 days)
        active_users_query = text("""
            SELECT COUNT(DISTINCT b.client_id)
            FROM bookings b
            WHERE b.scheduled_at >= :thirty_days_ago
        """)
        active_users_result = await db.execute(
            active_users_query,
            {"thirty_days_ago": thirty_days_ago}
        )
        active_users_30d = active_users_result.scalar() or 0

        # New users (registered in last 30 days)
        new_users_30d = await db.query(func.count(User.id)).filter(
            and_(
                User.role == UserRole.CLIENT,
                User.created_at >= thirty_days_ago
            )
        ).scalar()

        # User retention rate (simplified - users who made bookings both in last 30 days and previous 30 days)
        retention_query = text("""
            WITH recent_users AS (
                SELECT DISTINCT client_id
                FROM bookings
                WHERE scheduled_at >= :thirty_days_ago
            ),
            previous_users AS (
                SELECT DISTINCT client_id
                FROM bookings
                WHERE scheduled_at >= :sixty_days_ago AND scheduled_at < :thirty_days_ago
            )
            SELECT
                COUNT(DISTINCT r.client_id) as retained_users,
                COUNT(DISTINCT p.client_id) as previous_users
            FROM previous_users p
            LEFT JOIN recent_users r ON p.client_id = r.client_id
        """)

        sixty_days_ago = now - timedelta(days=60)
        retention_result = await db.execute(
            retention_query,
            {
                "thirty_days_ago": thirty_days_ago,
                "sixty_days_ago": sixty_days_ago
            }
        )
        retention_row = retention_result.fetchone()

        user_retention_rate = (
            (retention_row.retained_users / retention_row.previous_users * 100)
            if retention_row.previous_users > 0 else 0
        )

        # Average bookings per user
        avg_bookings_query = text("""
            SELECT AVG(booking_count) as avg_bookings
            FROM (
                SELECT client_id, COUNT(*) as booking_count
                FROM bookings
                WHERE scheduled_at >= :thirty_days_ago
                GROUP BY client_id
            ) user_bookings
        """)

        avg_bookings_result = await db.execute(
            avg_bookings_query,
            {"thirty_days_ago": thirty_days_ago}
        )
        avg_bookings_per_user = float(avg_bookings_result.scalar() or 0)

        # User lifetime value (simplified - average revenue per user for completed bookings)
        ltv_query = text("""
            SELECT AVG(user_revenue) as avg_ltv
            FROM (
                SELECT client_id, SUM(service_price) as user_revenue
                FROM bookings
                WHERE status = 'completed'
                GROUP BY client_id
            ) user_revenues
        """)

        ltv_result = await db.execute(ltv_query)
        user_lifetime_value = float(ltv_result.scalar() or 0)

        return UserAnalytics(
            total_users=total_users,
            active_users_30d=active_users_30d,
            new_users_30d=new_users_30d,
            user_retention_rate=round(user_retention_rate, 2),
            avg_bookings_per_user=round(avg_bookings_per_user, 2),
            user_lifetime_value=round(user_lifetime_value, 2)
        )

    except Exception as e:
        logger.error(f"Failed to get user analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user analytics"
        )


@router.get(
    "/growth/trends",
    summary="Get platform growth trends",
    description="""
    Get platform growth trends with month-over-month analysis.

    **Admin Only Endpoint**

    **Includes:**
    - User acquisition trends
    - Revenue growth patterns
    - Salon onboarding rates
    - Market expansion metrics

    **Authentication Required:** Admin only
    """,
)
async def get_growth_trends(
    months_back: int = Query(12, ge=1, le=24, description="Number of months to analyze"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get platform growth trends."""
    try:
        # Growth trends query
        growth_query = text("""
            WITH monthly_stats AS (
                SELECT
                    DATE_TRUNC('month', period_date) as month,
                    COUNT(DISTINCT CASE WHEN data_type = 'user' THEN entity_id END) as new_users,
                    COUNT(DISTINCT CASE WHEN data_type = 'salon' THEN entity_id END) as new_salons,
                    COUNT(DISTINCT CASE WHEN data_type = 'booking' THEN entity_id END) as total_bookings,
                    SUM(CASE WHEN data_type = 'revenue' THEN amount ELSE 0 END) as total_revenue
                FROM (
                    SELECT id as entity_id, created_at as period_date, 'user' as data_type, 0 as amount
                    FROM users WHERE role = 'client'

                    UNION ALL

                    SELECT id as entity_id, created_at as period_date, 'salon' as data_type, 0 as amount
                    FROM salons

                    UNION ALL

                    SELECT id as entity_id, scheduled_at as period_date, 'booking' as data_type, 0 as amount
                    FROM bookings

                    UNION ALL

                    SELECT id as entity_id, scheduled_at as period_date, 'revenue' as data_type, service_price as amount
                    FROM bookings WHERE status = 'completed'
                ) combined_data
                WHERE period_date >= NOW() - INTERVAL ':months_back months'
                GROUP BY DATE_TRUNC('month', period_date)
                ORDER BY month
            )
            SELECT
                month,
                new_users,
                new_salons,
                total_bookings,
                total_revenue,
                LAG(new_users) OVER (ORDER BY month) as prev_users,
                LAG(total_revenue) OVER (ORDER BY month) as prev_revenue
            FROM monthly_stats
        """)

        result = await db.execute(growth_query, {"months_back": months_back})

        growth_data = []
        for row in result.fetchall():
            user_growth = (
                ((row.new_users - row.prev_users) / row.prev_users * 100)
                if row.prev_users and row.prev_users > 0 else 0
            )
            revenue_growth = (
                ((row.total_revenue - row.prev_revenue) / row.prev_revenue * 100)
                if row.prev_revenue and row.prev_revenue > 0 else 0
            )

            growth_data.append({
                "month": row.month.strftime("%Y-%m"),
                "new_users": row.new_users,
                "new_salons": row.new_salons,
                "total_bookings": row.total_bookings,
                "total_revenue": float(row.total_revenue),
                "user_growth_rate": round(user_growth, 2),
                "revenue_growth_rate": round(revenue_growth, 2)
            })

        return {
            "period_months": months_back,
            "data": growth_data,
            "summary": {
                "total_months": len(growth_data),
                "avg_monthly_users": (
                    sum(item["new_users"] for item in growth_data) / len(growth_data)
                ) if growth_data else 0,
                "avg_monthly_revenue": (
                    sum(item["total_revenue"] for item in growth_data) / len(growth_data)
                ) if growth_data else 0
            }
        }

    except Exception as e:
        logger.error(f"Failed to get growth trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve growth trends"
        )
