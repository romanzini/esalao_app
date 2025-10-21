"""
Optimized reporting endpoints with caching and performance monitoring.

This module provides enhanced versions of reporting endpoints with:
- Redis caching for improved response times
- Optimized SQL queries with proper indexing
- Performance monitoring and logging
- Query result optimization
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.routes.reports import (
    BookingMetrics,
    DashboardMetrics,
    ProfessionalMetrics,
    ServiceMetrics,
)
from backend.app.core.performance.reporting import (
    PerformanceMonitor,
    QueryOptimizer,
    ReportCache,
    cache_report,
)
from backend.app.core.security.rbac import require_role
from backend.app.db.models.user import UserRole
from backend.app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimized-reports", tags=["📊 Reports - Optimized (Cache)"])


@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Get optimized dashboard metrics",
    description="""
    Get comprehensive dashboard metrics with performance optimizations.

    **Performance Features:**
    - Redis caching (15-minute TTL)
    - Optimized SQL queries
    - Performance monitoring
    - Efficient aggregations

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
@cache_report("dashboard", ttl=900)  # 15 minutes cache
@PerformanceMonitor.monitor_endpoint_performance("dashboard_metrics")
async def get_optimized_dashboard_metrics(
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
    """Get optimized dashboard metrics."""
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

        # Get optimized booking metrics
        query, params = QueryOptimizer.get_optimized_booking_metrics_query(
            start_date=start_date,
            end_date=end_date,
            salon_id=salon_id,
        )

        start_time = datetime.utcnow()
        result = await db.execute(text(query), params)
        row = result.fetchone()
        query_time = (datetime.utcnow() - start_time).total_seconds()

        PerformanceMonitor.log_query_performance(
            "optimized_booking_metrics",
            query_time
        )

        if not row:
            # Return empty metrics if no data
            booking_metrics = BookingMetrics(
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
        else:
            booking_metrics = BookingMetrics(
                total_bookings=row.total_bookings,
                completed_bookings=row.completed_bookings,
                cancelled_bookings=row.cancelled_bookings,
                no_show_bookings=row.no_show_bookings,
                confirmed_bookings=row.confirmed_bookings,
                completion_rate=float(row.completion_rate),
                cancellation_rate=float(row.cancellation_rate),
                no_show_rate=float(row.no_show_rate),
                avg_booking_value=float(row.avg_booking_value) if row.avg_booking_value else None,
                total_revenue=float(row.total_revenue)
            )

        # Get top professionals (simplified for performance)
        prof_query, prof_params = QueryOptimizer.get_optimized_professional_performance_query(
            start_date=start_date,
            end_date=end_date,
            salon_id=salon_id,
            limit=5  # Top 5 for dashboard
        )

        start_time = datetime.utcnow()
        prof_result = await db.execute(text(prof_query), prof_params)
        prof_rows = prof_result.fetchall()
        prof_query_time = (datetime.utcnow() - start_time).total_seconds()

        PerformanceMonitor.log_query_performance(
            "optimized_professional_metrics",
            prof_query_time,
            len(prof_rows)
        )

        top_professionals = []
        for row in prof_rows:
            prof_metrics = ProfessionalMetrics(
                professional_id=row.professional_id,
                professional_name=row.professional_name,
                total_bookings=row.total_bookings,
                completed_bookings=row.completed_bookings,
                completion_rate=float(row.completion_rate),
                total_revenue=float(row.total_revenue),
                avg_booking_value=float(row.avg_booking_value) if row.avg_booking_value else None,
                unique_clients=row.unique_clients,
                repeat_clients=row.repeat_clients,
                client_retention_rate=float(row.client_retention_rate)
            )
            top_professionals.append(prof_metrics)

        # Simplified service metrics for dashboard
        top_services = []  # Could be implemented with similar optimization

        # Simplified trends for dashboard
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
        logger.error(f"Failed to get optimized dashboard metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics"
        )


@router.get(
    "/bookings",
    response_model=BookingMetrics,
    summary="Get optimized booking metrics",
    description="""
    Get detailed booking statistics with performance optimizations.

    **Performance Features:**
    - Optimized SQL with efficient indexes
    - Query result caching
    - Performance monitoring

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
@cache_report("booking_metrics", ttl=600)  # 10 minutes cache
@PerformanceMonitor.monitor_endpoint_performance("booking_metrics")
async def get_optimized_booking_metrics(
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
    """Get optimized booking metrics."""
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get optimized query
        query, params = QueryOptimizer.get_optimized_booking_metrics_query(
            start_date=start_date,
            end_date=end_date,
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id,
        )

        start_time = datetime.utcnow()
        result = await db.execute(text(query), params)
        row = result.fetchone()
        query_time = (datetime.utcnow() - start_time).total_seconds()

        PerformanceMonitor.log_query_performance(
            "optimized_booking_metrics_detailed",
            query_time
        )

        if not row:
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

        return BookingMetrics(
            total_bookings=row.total_bookings,
            completed_bookings=row.completed_bookings,
            cancelled_bookings=row.cancelled_bookings,
            no_show_bookings=row.no_show_bookings,
            confirmed_bookings=row.confirmed_bookings,
            completion_rate=float(row.completion_rate),
            cancellation_rate=float(row.cancellation_rate),
            no_show_rate=float(row.no_show_rate),
            avg_booking_value=float(row.avg_booking_value) if row.avg_booking_value else None,
            total_revenue=float(row.total_revenue)
        )

    except Exception as e:
        logger.error(f"Failed to get optimized booking metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve booking metrics"
        )


@router.get(
    "/professionals",
    response_model=List[ProfessionalMetrics],
    summary="Get optimized professional performance",
    description="""
    Get professional performance metrics with optimizations.

    **Performance Features:**
    - Single optimized query with CTEs
    - Efficient client retention calculation
    - Result caching

    **Authentication Required:** Salon Owner, Admin, or Receptionist
    """,
)
@cache_report("professional_metrics", ttl=600)  # 10 minutes cache
@PerformanceMonitor.monitor_endpoint_performance("professional_metrics")
async def get_optimized_professional_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    salon_id: Optional[int] = Query(None, description="Filter by salon"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of professionals"),
    current_user: dict = Depends(
        require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])
    ),
    db: AsyncSession = Depends(get_db),
) -> List[ProfessionalMetrics]:
    """Get optimized professional performance metrics."""
    try:
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get optimized query
        query, params = QueryOptimizer.get_optimized_professional_performance_query(
            start_date=start_date,
            end_date=end_date,
            salon_id=salon_id,
            limit=limit,
        )

        start_time = datetime.utcnow()
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        query_time = (datetime.utcnow() - start_time).total_seconds()

        PerformanceMonitor.log_query_performance(
            "optimized_professional_performance",
            query_time,
            len(rows)
        )

        metrics_list = []
        for row in rows:
            metrics = ProfessionalMetrics(
                professional_id=row.professional_id,
                professional_name=row.professional_name,
                total_bookings=row.total_bookings,
                completed_bookings=row.completed_bookings,
                completion_rate=float(row.completion_rate),
                total_revenue=float(row.total_revenue),
                avg_booking_value=float(row.avg_booking_value) if row.avg_booking_value else None,
                unique_clients=row.unique_clients,
                repeat_clients=row.repeat_clients,
                client_retention_rate=float(row.client_retention_rate)
            )
            metrics_list.append(metrics)

        return metrics_list

    except Exception as e:
        logger.error(f"Failed to get optimized professional metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve professional metrics"
        )


@router.post(
    "/cache/clear",
    summary="Clear report cache",
    description="""
    Clear cached report data.

    **Admin Only Endpoint**

    Useful for forcing fresh data after system changes.
    """,
)
async def clear_report_cache(
    pattern: str = Query("*", description="Cache pattern to clear"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
) -> dict:
    """Clear report cache."""
    try:
        deleted_count = ReportCache.delete_pattern(pattern)

        return {
            "status": "success",
            "message": f"Cleared {deleted_count} cache entries",
            "pattern": pattern,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get(
    "/performance/stats",
    summary="Get performance statistics",
    description="""
    Get performance statistics for reporting endpoints.

    **Admin Only Endpoint**

    Shows cache hit rates, query performance, and system metrics.
    """,
)
async def get_performance_stats(
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get performance statistics."""
    try:
        # Get cache statistics
        cache_stats = {}
        if ReportCache.redis_client:
            try:
                info = ReportCache.redis_client.info()
                cache_stats = {
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": (
                        info.get("keyspace_hits", 0) /
                        max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100
                    )
                }
            except Exception as e:
                cache_stats = {"connected": False, "error": str(e)}
        else:
            cache_stats = {"connected": False, "reason": "Redis not configured"}

        # Get database performance stats
        db_stats_query = text("""
            SELECT
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                seq_scan,
                seq_tup_read,
                idx_scan,
                idx_tup_fetch
            FROM pg_stat_user_tables
            WHERE tablename IN ('bookings', 'professionals', 'services', 'users')
            ORDER BY tablename
        """)

        start_time = datetime.utcnow()
        db_result = await db.execute(db_stats_query)
        db_rows = db_result.fetchall()
        db_query_time = (datetime.utcnow() - start_time).total_seconds()

        db_stats = []
        for row in db_rows:
            db_stats.append({
                "table": row.tablename,
                "inserts": row.inserts,
                "updates": row.updates,
                "deletes": row.deletes,
                "sequential_scans": row.seq_scan,
                "index_scans": row.idx_scan,
                "index_efficiency": (
                    row.idx_scan / max(row.seq_scan + row.idx_scan, 1) * 100
                ) if (row.seq_scan + row.idx_scan) > 0 else 0
            })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cache": cache_stats,
            "database": {
                "query_time_ms": round(db_query_time * 1000, 2),
                "table_stats": db_stats
            },
            "recommendations": {
                "cache_hit_rate_target": "> 80%",
                "index_efficiency_target": "> 90%",
                "query_time_target": "< 100ms"
            }
        }

    except Exception as e:
        logger.error(f"Failed to get performance stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance statistics"
        )
