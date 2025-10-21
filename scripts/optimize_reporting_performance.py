"""
Database optimization script for reporting performance.

This script applies database indexes, analyzes table statistics,
and optimizes database configuration for reporting workloads.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.core.performance.reporting import (
    REPORTING_INDEXES,
    analyze_table_stats,
    create_reporting_indexes,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def optimize_database_for_reporting():
    """Run complete database optimization for reporting."""
    logger.info("Starting database optimization for reporting...")

    # Create async engine
    engine = create_async_engine(
        settings.ASYNC_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    # Create session maker
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with async_session_maker() as session:
            # 1. Create performance indexes
            logger.info("Creating performance indexes...")
            await create_reporting_indexes(session)

            # 2. Analyze table statistics
            logger.info("Analyzing table statistics...")
            await analyze_table_stats(session)

            # 3. Additional performance optimizations
            logger.info("Applying additional optimizations...")

            # Enable parallel query execution for reporting
            await session.execute(text("SET max_parallel_workers_per_gather = 4;"))
            await session.execute(text("SET work_mem = '256MB';"))

            # Optimize for analytical queries
            await session.execute(text("SET random_page_cost = 1.1;"))
            await session.execute(text("SET effective_cache_size = '1GB';"))

            # 4. Create partial indexes for common report filters
            partial_indexes = [
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_completed_last_year
                ON bookings(scheduled_at, service_price)
                WHERE status = 'completed' AND scheduled_at >= CURRENT_DATE - INTERVAL '1 year'
                """,
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_revenue_monthly
                ON bookings(DATE_TRUNC('month', scheduled_at), salon_id, service_price)
                WHERE status = 'completed'
                """,
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_professionals_performance
                ON professionals(salon_id, is_active, created_at)
                WHERE is_active = true
                """,
            ]

            for index_sql in partial_indexes:
                try:
                    await session.execute(text(index_sql))
                    await session.commit()
                    logger.info("Created partial index")
                except Exception as e:
                    logger.warning(f"Partial index creation failed (may exist): {e}")
                    await session.rollback()

            # 5. Create materialized view refresh function
            refresh_function = """
            CREATE OR REPLACE FUNCTION refresh_reporting_views()
            RETURNS void AS $$
            BEGIN
                -- This function will refresh materialized views when they're created
                -- For now, it's a placeholder for future materialized views
                RAISE NOTICE 'Refreshing reporting views...';
            END;
            $$ LANGUAGE plpgsql;
            """

            try:
                await session.execute(text(refresh_function))
                await session.commit()
                logger.info("Created materialized view refresh function")
            except Exception as e:
                logger.warning(f"Function creation failed: {e}")
                await session.rollback()

            # 6. Verify index creation
            logger.info("Verifying index creation...")
            index_check_query = text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                    AND (indexname LIKE 'idx_bookings_%'
                         OR indexname LIKE 'idx_professionals_%'
                         OR indexname LIKE 'idx_services_%'
                         OR indexname LIKE 'idx_users_%')
                ORDER BY tablename, indexname
            """)

            result = await session.execute(index_check_query)
            indexes = result.fetchall()

            logger.info(f"Found {len(indexes)} reporting indexes:")
            for idx in indexes:
                logger.info(f"  {idx.tablename}.{idx.indexname}")

            # 7. Check table sizes and performance
            table_stats_query = text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    n_tup_ins + n_tup_upd + n_tup_del as total_writes,
                    seq_scan,
                    idx_scan,
                    CASE
                        WHEN seq_scan + idx_scan > 0 THEN
                            ROUND((idx_scan::decimal / (seq_scan + idx_scan) * 100), 2)
                        ELSE 0
                    END as index_usage_pct
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                    AND tablename IN ('bookings', 'professionals', 'services', 'users', 'salons')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)

            result = await session.execute(table_stats_query)
            table_stats = result.fetchall()

            logger.info("\nTable performance statistics:")
            logger.info("Table         | Total Size | Index Usage | Seq Scans | Idx Scans")
            logger.info("-" * 70)
            for stat in table_stats:
                logger.info(
                    f"{stat.tablename:<12} | {stat.total_size:<10} | "
                    f"{stat.index_usage_pct:>8}% | {stat.seq_scan:>8} | {stat.idx_scan:>8}"
                )

            logger.info("\nDatabase optimization completed successfully!")

            # 8. Performance recommendations
            recommendations = []

            for stat in table_stats:
                if stat.index_usage_pct < 80 and stat.seq_scan > 100:
                    recommendations.append(
                        f"Consider adding indexes to {stat.tablename} "
                        f"(index usage: {stat.index_usage_pct}%)"
                    )

                if stat.total_writes > 10000:
                    recommendations.append(
                        f"High write activity on {stat.tablename} "
                        f"({stat.total_writes} writes) - monitor for lock contention"
                    )

            if recommendations:
                logger.info("\nPerformance Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    logger.info(f"{i}. {rec}")
            else:
                logger.info("\nNo performance issues detected!")

    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        raise
    finally:
        await engine.dispose()


async def run_performance_benchmark():
    """Run performance benchmark for reporting queries."""
    logger.info("Running performance benchmark...")

    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with async_session_maker() as session:
            # Benchmark queries
            benchmark_queries = [
                ("Simple booking count", "SELECT COUNT(*) FROM bookings"),
                (
                    "Booking metrics",
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        SUM(CASE WHEN status = 'completed' THEN service_price ELSE 0 END) as revenue
                    FROM bookings
                    WHERE scheduled_at >= CURRENT_DATE - INTERVAL '30 days'
                    """
                ),
                (
                    "Professional performance",
                    """
                    SELECT
                        p.id, p.name,
                        COUNT(b.id) as booking_count,
                        SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END) as revenue
                    FROM professionals p
                    LEFT JOIN bookings b ON p.id = b.professional_id
                        AND b.scheduled_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY p.id, p.name
                    ORDER BY revenue DESC
                    LIMIT 10
                    """
                ),
            ]

            results = []

            for query_name, query_sql in benchmark_queries:
                import time

                start_time = time.time()
                result = await session.execute(text(query_sql))
                rows = result.fetchall()
                end_time = time.time()

                execution_time = round((end_time - start_time) * 1000, 2)  # ms
                row_count = len(rows)

                results.append({
                    "query": query_name,
                    "execution_time_ms": execution_time,
                    "row_count": row_count
                })

                logger.info(f"{query_name}: {execution_time}ms ({row_count} rows)")

            # Performance assessment
            logger.info("\nBenchmark Results:")
            for result in results:
                status = "✓" if result["execution_time_ms"] < 100 else "⚠" if result["execution_time_ms"] < 500 else "✗"
                logger.info(
                    f"{status} {result['query']}: {result['execution_time_ms']}ms "
                    f"({result['row_count']} rows)"
                )

            avg_time = sum(r["execution_time_ms"] for r in results) / len(results)
            logger.info(f"\nAverage query time: {avg_time:.2f}ms")

            if avg_time < 100:
                logger.info("🎉 Excellent performance!")
            elif avg_time < 300:
                logger.info("👍 Good performance")
            else:
                logger.warning("⚠️  Consider additional optimizations")

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """Main optimization script."""
    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        await run_performance_benchmark()
    else:
        await optimize_database_for_reporting()


if __name__ == "__main__":
    asyncio.run(main())
