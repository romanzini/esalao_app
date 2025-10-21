"""
Performance optimization utilities for reporting endpoints.

This module provides caching, query optimization, and performance monitoring
utilities specifically designed for the reporting system.
"""

import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional

import redis
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client for caching
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    redis_client.ping()
    logger.info("Redis connection established for reporting cache")
except Exception as e:
    logger.warning(f"Redis not available for reporting cache: {e}")
    redis_client = None


class ReportCache:
    """Redis-based caching for reporting endpoints."""

    DEFAULT_TTL = 900  # 15 minutes

    @staticmethod
    def _make_cache_key(prefix: str, **kwargs) -> str:
        """Generate cache key from prefix and parameters."""
        # Sort parameters for consistent keys
        params = sorted(kwargs.items())
        params_str = "&".join(f"{k}={v}" for k, v in params if v is not None)
        return f"reports:{prefix}:{params_str}"

    @staticmethod
    def _serialize_datetime(obj: Any) -> str:
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object {obj} is not JSON serializable")

    @classmethod
    def get(cls, prefix: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached report data."""
        if not redis_client:
            return None

        try:
            cache_key = cls._make_cache_key(prefix, **kwargs)
            cached_data = redis_client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache miss for {cache_key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    @classmethod
    def set(cls, prefix: str, data: Dict[str, Any], ttl: int = None, **kwargs) -> bool:
        """Set cached report data."""
        if not redis_client:
            return False

        try:
            cache_key = cls._make_cache_key(prefix, **kwargs)
            ttl = ttl or cls.DEFAULT_TTL

            serialized_data = json.dumps(data, default=cls._serialize_datetime)
            redis_client.setex(cache_key, ttl, serialized_data)

            logger.debug(f"Cached data for {cache_key} with TTL {ttl}s")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        """Delete cache entries matching pattern."""
        if not redis_client:
            return 0

        try:
            keys = redis_client.keys(f"reports:{pattern}")
            if keys:
                deleted = redis_client.delete(*keys)
                logger.info(f"Deleted {deleted} cache entries matching {pattern}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0


def cache_report(prefix: str, ttl: int = None):
    """
    Decorator to cache report endpoint results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (default: 15 minutes)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request parameters for cache key
            cache_params = {}

            # Get function arguments
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Extract cacheable parameters (skip request objects)
            for name, value in bound_args.arguments.items():
                if name not in ['current_user', 'db', 'request']:
                    if isinstance(value, datetime):
                        cache_params[name] = value.isoformat()
                    elif value is not None:
                        cache_params[name] = str(value)

            # Try to get from cache
            cached_result = ReportCache.get(prefix, **cache_params)
            if cached_result:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)

            # Cache the result
            if isinstance(result, dict):
                ReportCache.set(prefix, result, ttl, **cache_params)

            return result

        return wrapper
    return decorator


class QueryOptimizer:
    """Query optimization utilities for reporting."""

    @staticmethod
    def get_optimized_booking_metrics_query(
        start_date: datetime,
        end_date: datetime,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Get optimized SQL query for booking metrics."""

        # Base query with proper indexes
        query = """
        WITH booking_stats AS (
            SELECT
                COUNT(*) as total_bookings,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_bookings,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_bookings,
                COUNT(CASE WHEN status = 'no_show' THEN 1 END) as no_show_bookings,
                COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_bookings,
                SUM(CASE WHEN status = 'completed' THEN service_price ELSE 0 END) as total_revenue
            FROM bookings b
        """

        # Add joins if needed
        joins = []
        where_conditions = ["b.scheduled_at >= :start_date", "b.scheduled_at <= :end_date"]
        params = {"start_date": start_date, "end_date": end_date}

        if salon_id:
            joins.append("JOIN professionals p ON b.professional_id = p.id")
            where_conditions.append("p.salon_id = :salon_id")
            params["salon_id"] = salon_id

        if professional_id:
            where_conditions.append("b.professional_id = :professional_id")
            params["professional_id"] = professional_id

        if service_id:
            where_conditions.append("b.service_id = :service_id")
            params["service_id"] = service_id

        # Combine query parts
        if joins:
            query += " " + " ".join(joins)

        query += " WHERE " + " AND ".join(where_conditions)
        query += """
        )
        SELECT
            total_bookings,
            completed_bookings,
            cancelled_bookings,
            no_show_bookings,
            confirmed_bookings,
            total_revenue,
            CASE
                WHEN total_bookings > 0 THEN
                    ROUND((completed_bookings::decimal / total_bookings * 100), 2)
                ELSE 0
            END as completion_rate,
            CASE
                WHEN total_bookings > 0 THEN
                    ROUND((cancelled_bookings::decimal / total_bookings * 100), 2)
                ELSE 0
            END as cancellation_rate,
            CASE
                WHEN total_bookings > 0 THEN
                    ROUND((no_show_bookings::decimal / total_bookings * 100), 2)
                ELSE 0
            END as no_show_rate,
            CASE
                WHEN completed_bookings > 0 THEN
                    ROUND((total_revenue / completed_bookings), 2)
                ELSE NULL
            END as avg_booking_value
        FROM booking_stats
        """

        return query, params

    @staticmethod
    def get_optimized_professional_performance_query(
        start_date: datetime,
        end_date: datetime,
        salon_id: Optional[int] = None,
        limit: int = 10,
    ) -> tuple[str, Dict[str, Any]]:
        """Get optimized SQL query for professional performance metrics."""

        query = """
        WITH professional_stats AS (
            SELECT
                p.id as professional_id,
                p.name as professional_name,
                COUNT(b.id) as total_bookings,
                COUNT(CASE WHEN b.status = 'completed' THEN 1 END) as completed_bookings,
                SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END) as total_revenue,
                COUNT(DISTINCT b.client_id) as unique_clients
            FROM professionals p
            LEFT JOIN bookings b ON p.id = b.professional_id
                AND b.scheduled_at >= :start_date
                AND b.scheduled_at <= :end_date
        """

        params = {"start_date": start_date, "end_date": end_date, "limit": limit}

        if salon_id:
            query += " WHERE p.salon_id = :salon_id"
            params["salon_id"] = salon_id

        query += """
            GROUP BY p.id, p.name
            HAVING COUNT(b.id) > 0
        ),
        client_retention AS (
            SELECT
                ps.professional_id,
                COUNT(CASE WHEN client_bookings.booking_count > 1 THEN 1 END) as repeat_clients
            FROM professional_stats ps
            LEFT JOIN (
                SELECT
                    professional_id,
                    client_id,
                    COUNT(*) as booking_count
                FROM bookings
                WHERE scheduled_at >= :start_date AND scheduled_at <= :end_date
                GROUP BY professional_id, client_id
            ) client_bookings ON ps.professional_id = client_bookings.professional_id
            GROUP BY ps.professional_id
        )
        SELECT
            ps.professional_id,
            ps.professional_name,
            ps.total_bookings,
            ps.completed_bookings,
            CASE
                WHEN ps.total_bookings > 0 THEN
                    ROUND((ps.completed_bookings::decimal / ps.total_bookings * 100), 2)
                ELSE 0
            END as completion_rate,
            ps.total_revenue,
            CASE
                WHEN ps.completed_bookings > 0 THEN
                    ROUND((ps.total_revenue / ps.completed_bookings), 2)
                ELSE NULL
            END as avg_booking_value,
            ps.unique_clients,
            COALESCE(cr.repeat_clients, 0) as repeat_clients,
            CASE
                WHEN ps.unique_clients > 0 THEN
                    ROUND((COALESCE(cr.repeat_clients, 0)::decimal / ps.unique_clients * 100), 2)
                ELSE 0
            END as client_retention_rate
        FROM professional_stats ps
        LEFT JOIN client_retention cr ON ps.professional_id = cr.professional_id
        ORDER BY ps.total_revenue DESC
        LIMIT :limit
        """

        return query, params


class PerformanceMonitor:
    """Performance monitoring for reporting endpoints."""

    @staticmethod
    def log_query_performance(query_name: str, execution_time: float, result_count: int = None):
        """Log query performance metrics."""
        log_data = {
            "query_name": query_name,
            "execution_time_ms": round(execution_time * 1000, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }

        if result_count is not None:
            log_data["result_count"] = result_count

        if execution_time > 1.0:  # Log slow queries
            logger.warning(f"Slow query detected: {log_data}")
        else:
            logger.debug(f"Query performance: {log_data}")

    @staticmethod
    def monitor_endpoint_performance(endpoint_name: str):
        """Decorator to monitor endpoint performance."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = datetime.utcnow()

                try:
                    result = await func(*args, **kwargs)

                    end_time = datetime.utcnow()
                    execution_time = (end_time - start_time).total_seconds()

                    # Determine result count
                    result_count = None
                    if isinstance(result, list):
                        result_count = len(result)
                    elif isinstance(result, dict) and 'data' in result:
                        data = result['data']
                        if isinstance(data, list):
                            result_count = len(data)

                    PerformanceMonitor.log_query_performance(
                        endpoint_name,
                        execution_time,
                        result_count
                    )

                    return result

                except Exception as e:
                    end_time = datetime.utcnow()
                    execution_time = (end_time - start_time).total_seconds()

                    logger.error(f"Endpoint {endpoint_name} failed after {execution_time:.2f}s: {e}")
                    raise

            return wrapper
        return decorator


# Database indexes for reporting optimization
REPORTING_INDEXES = [
    # Bookings table indexes for reporting
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_scheduled_at_status ON bookings(scheduled_at, status);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_professional_scheduled ON bookings(professional_id, scheduled_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_service_scheduled ON bookings(service_id, scheduled_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_client_scheduled ON bookings(client_id, scheduled_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_status_completed ON bookings(status) WHERE status = 'completed';",

    # Professional table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_professionals_salon_active ON professionals(salon_id, is_active);",

    # Services table indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_services_salon_category ON services(salon_id, category);",

    # Users table indexes for analytics
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_created ON users(role, created_at);",

    # Audit events indexes
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_events_created_type ON audit_events(created_at, event_type);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id);",
]


async def create_reporting_indexes(db: AsyncSession):
    """Create database indexes for reporting optimization."""
    logger.info("Creating reporting performance indexes...")

    for index_sql in REPORTING_INDEXES:
        try:
            await db.execute(text(index_sql))
            await db.commit()
            logger.debug(f"Created index: {index_sql[:50]}...")
        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")
            await db.rollback()

    logger.info("Completed reporting indexes creation")


async def analyze_table_stats(db: AsyncSession):
    """Update table statistics for query optimization."""
    tables = ['bookings', 'professionals', 'services', 'users', 'salons', 'audit_events']

    for table in tables:
        try:
            await db.execute(text(f"ANALYZE {table};"))
            logger.debug(f"Analyzed table: {table}")
        except Exception as e:
            logger.warning(f"Failed to analyze table {table}: {e}")

    await db.commit()
    logger.info("Completed table statistics analysis")
