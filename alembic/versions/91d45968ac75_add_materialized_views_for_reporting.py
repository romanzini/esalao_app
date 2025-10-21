"""Mako template for Alembic migrations."""

"""Add materialized views for reporting

Revision ID: 91d45968ac75
Revises: 7e2f46038f27
Create Date: 2025-10-21 13:08:14.959716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91d45968ac75'
down_revision = '7e2f46038f27'
branch_labels = None
depends_on = None


"""Add materialized views for reporting

Revision ID: 91d45968ac75
Revises: 7e2f46038f27
Create Date: 2025-10-21 13:08:14.959716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91d45968ac75'
down_revision = '7e2f46038f27'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create booking metrics materialized view
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS booking_metrics_mv AS
        SELECT
            DATE_TRUNC('day', b.scheduled_at) as metric_date,
            1 as unit_id,  -- Default unit ID since not in table
            salon.id as salon_id,
            -- Booking counts
            COUNT(*) as total_bookings,
            COUNT(CASE WHEN b.status = 'completed' THEN 1 END) as completed_bookings,
            COUNT(CASE WHEN b.status = 'cancelled' THEN 1 END) as cancelled_bookings,
            COUNT(CASE WHEN b.status = 'no_show' THEN 1 END) as no_show_bookings,
            COUNT(CASE WHEN b.status = 'confirmed' THEN 1 END) as confirmed_bookings,

            -- Timing metrics
            AVG(EXTRACT(EPOCH FROM (b.completed_at - b.scheduled_at))/60) as avg_duration_minutes,
            AVG(EXTRACT(EPOCH FROM (b.created_at - b.scheduled_at))/3600) as avg_booking_lead_hours,

            -- Revenue metrics
            SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END) as completed_revenue,
            AVG(CASE WHEN b.status = 'completed' THEN b.service_price END) as avg_booking_value,
            COALESCE(SUM(b.cancellation_fee_amount), 0) as cancellation_fees,
            COALESCE(SUM(b.no_show_fee_amount), 0) as no_show_fees,

            -- Performance ratios
            ROUND(
                COUNT(CASE WHEN b.status = 'completed' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as completion_rate_pct,
            ROUND(
                COUNT(CASE WHEN b.status = 'cancelled' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as cancellation_rate_pct,
            ROUND(
                COUNT(CASE WHEN b.status = 'no_show' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as no_show_rate_pct,

            -- Service metrics
            COUNT(DISTINCT b.service_id) as unique_services,
            COUNT(DISTINCT b.professional_id) as unique_professionals,
            COUNT(DISTINCT b.client_id) as unique_clients,

            -- Time slots analysis
            COUNT(CASE WHEN EXTRACT(hour FROM b.scheduled_at) BETWEEN 6 AND 11 THEN 1 END) as morning_bookings,
            COUNT(CASE WHEN EXTRACT(hour FROM b.scheduled_at) BETWEEN 12 AND 17 THEN 1 END) as afternoon_bookings,
            COUNT(CASE WHEN EXTRACT(hour FROM b.scheduled_at) BETWEEN 18 AND 23 THEN 1 END) as evening_bookings,

            -- Weekly pattern
            COUNT(CASE WHEN EXTRACT(dow FROM b.scheduled_at) IN (1,2,3,4,5) THEN 1 END) as weekday_bookings,
            COUNT(CASE WHEN EXTRACT(dow FROM b.scheduled_at) IN (0,6) THEN 1 END) as weekend_bookings,

            -- Update tracking
            NOW() as last_updated
        FROM bookings b
        JOIN services sv ON b.service_id = sv.id
        JOIN professionals p ON b.professional_id = p.id
        JOIN salons salon ON p.salon_id = salon.id
        WHERE b.scheduled_at >= CURRENT_DATE - INTERVAL '2 years'
        GROUP BY
            DATE_TRUNC('day', b.scheduled_at),
            salon.id;
    """)

    # Create indexes for booking metrics
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_booking_metrics_mv_date_salon
        ON booking_metrics_mv (metric_date, salon_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_booking_metrics_mv_salon_date
        ON booking_metrics_mv (salon_id, metric_date DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_booking_metrics_mv_date_desc
        ON booking_metrics_mv (metric_date DESC);
    """)

    # Create revenue metrics materialized view
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS revenue_metrics_mv AS
        SELECT
            DATE_TRUNC('day', p.created_at) as metric_date,
            EXTRACT(month FROM p.created_at) as metric_month,
            EXTRACT(year FROM p.created_at) as metric_year,
            1 as unit_id,  -- Default unit ID
            s.salon_id,
            sv.category,

            -- Payment totals
            COUNT(*) as total_payments,
            SUM(p.amount) as total_revenue,
            SUM(CASE WHEN p.status = 'succeeded' THEN p.amount ELSE 0 END) as confirmed_revenue,
            SUM(CASE WHEN p.status = 'failed' THEN p.amount ELSE 0 END) as failed_revenue,
            SUM(CASE WHEN p.status = 'refunded' THEN p.amount ELSE 0 END) as refunded_revenue,

            -- Payment methods
            COUNT(CASE WHEN p.payment_method = 'pix' THEN 1 END) as pix_payments,
            COUNT(CASE WHEN p.payment_method = 'credit_card' THEN 1 END) as credit_card_payments,
            COUNT(CASE WHEN p.payment_method = 'debit_card' THEN 1 END) as debit_card_payments,
            SUM(CASE WHEN p.payment_method = 'pix' AND p.status = 'succeeded' THEN p.amount ELSE 0 END) as pix_revenue,
            SUM(CASE WHEN p.payment_method = 'credit_card' AND p.status = 'succeeded' THEN p.amount ELSE 0 END) as credit_card_revenue,
            SUM(CASE WHEN p.payment_method = 'debit_card' AND p.status = 'succeeded' THEN p.amount ELSE 0 END) as debit_card_revenue,

            -- Transaction statistics
            AVG(CASE WHEN p.status = 'succeeded' THEN p.amount END) as avg_transaction_value,
            MIN(CASE WHEN p.status = 'succeeded' THEN p.amount END) as min_transaction_value,
            MAX(CASE WHEN p.status = 'succeeded' THEN p.amount END) as max_transaction_value,

            -- Success rates
            ROUND(
                COUNT(CASE WHEN p.status = 'succeeded' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as success_rate_pct,
            ROUND(
                COUNT(CASE WHEN p.status = 'failed' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as failure_rate_pct,

            -- Processing metrics (using paid_at when available)
            AVG(EXTRACT(EPOCH FROM (p.paid_at - p.created_at))/60) as avg_processing_time_minutes,

            -- Revenue per service category
            COUNT(DISTINCT sv.id) as unique_services,
            COUNT(DISTINCT b.client_id) as unique_customers,

            -- Update tracking
            NOW() as last_updated
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        JOIN services sv ON b.service_id = sv.id
        JOIN professionals pr ON b.professional_id = pr.id
        JOIN salons s ON pr.salon_id = s.id
        WHERE p.created_at >= CURRENT_DATE - INTERVAL '2 years'
        GROUP BY
            DATE_TRUNC('day', p.created_at),
            EXTRACT(month FROM p.created_at),
            EXTRACT(year FROM p.created_at),
            s.salon_id,
            sv.category;
    """)

    # Create indexes for revenue metrics
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_revenue_metrics_mv_date_salon_category
        ON revenue_metrics_mv (metric_date, salon_id, category);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_revenue_metrics_mv_salon_date
        ON revenue_metrics_mv (salon_id, metric_date DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_revenue_metrics_mv_year_month
        ON revenue_metrics_mv (metric_year, metric_month);
    """)

    # Create professional performance materialized view
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS professional_performance_mv AS
        SELECT
            DATE_TRUNC('week', b.scheduled_at) as metric_week,
            DATE_TRUNC('month', b.scheduled_at) as metric_month,
            b.professional_id,
            p.name as professional_name,
            p.salon_id,
            s.name as salon_name,

            -- Booking metrics
            COUNT(*) as total_bookings,
            COUNT(CASE WHEN b.status = 'completed' THEN 1 END) as completed_bookings,
            COUNT(CASE WHEN b.status = 'cancelled' THEN 1 END) as cancelled_bookings,
            COUNT(CASE WHEN b.status = 'no_show' THEN 1 END) as no_show_bookings,

            -- Revenue metrics
            SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END) as total_revenue,
            AVG(CASE WHEN b.status = 'completed' THEN b.service_price END) as avg_booking_value,

            -- Time efficiency (using actual duration vs scheduled)
            SUM(CASE WHEN b.status = 'completed' THEN sv.duration_minutes ELSE 0 END) as total_service_minutes,
            AVG(CASE WHEN b.status = 'completed' AND b.completed_at IS NOT NULL
                THEN EXTRACT(EPOCH FROM (b.completed_at - b.scheduled_at))/60 END) as avg_actual_duration,

            -- Performance ratings
            ROUND(
                COUNT(CASE WHEN b.status = 'completed' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as completion_rate_pct,
            ROUND(
                COUNT(CASE WHEN b.status = 'no_show' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as no_show_rate_pct,

            -- Client relationship
            COUNT(DISTINCT b.client_id) as unique_clients,
            COUNT(DISTINCT CASE WHEN client_bookings.booking_count > 1 THEN b.client_id END) as repeat_clients,

            -- Service diversity
            COUNT(DISTINCT b.service_id) as unique_services,
            COUNT(DISTINCT sv.category) as service_categories,

            -- Schedule utilization
            COUNT(DISTINCT DATE(b.scheduled_at)) as active_days,
            ROUND(
                COUNT(*)::numeric /
                NULLIF(COUNT(DISTINCT DATE(b.scheduled_at)) * 8, 0), 2
            ) as avg_bookings_per_day,

            -- Peak performance
            COUNT(CASE WHEN EXTRACT(hour FROM b.scheduled_at) BETWEEN 9 AND 17 THEN 1 END) as peak_hour_bookings,

            -- Update tracking
            NOW() as last_updated
        FROM bookings b
        JOIN professionals p ON b.professional_id = p.id
        JOIN salons s ON p.salon_id = s.id
        JOIN services sv ON b.service_id = sv.id
        LEFT JOIN (
            SELECT client_id, COUNT(*) as booking_count
            FROM bookings
            WHERE status = 'completed'
            GROUP BY client_id
        ) client_bookings ON b.client_id = client_bookings.client_id
        WHERE b.scheduled_at >= CURRENT_DATE - INTERVAL '1 year'
        GROUP BY
            DATE_TRUNC('week', b.scheduled_at),
            DATE_TRUNC('month', b.scheduled_at),
            b.professional_id,
            p.name,
            p.salon_id,
            s.name;
    """)

    # Create indexes for professional performance
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_professional_performance_mv_week_prof
        ON professional_performance_mv (metric_week, professional_id);
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_professional_performance_mv_month_prof
        ON professional_performance_mv (metric_month, professional_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_professional_performance_mv_salon
        ON professional_performance_mv (salon_id, metric_month DESC);
    """)

    # Create customer analytics materialized view
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS customer_analytics_mv AS
        SELECT
            DATE_TRUNC('month', first_booking.first_booking_date) as cohort_month,
            b.client_id,
            u.email as client_email,
            u.phone as client_phone,
            first_booking.salon_id,
            s.name as salon_name,

            -- Customer lifecycle
            first_booking.first_booking_date,
            MAX(b.scheduled_at) as last_booking_date,
            COUNT(*) as total_bookings,
            COUNT(CASE WHEN b.status = 'completed' THEN 1 END) as completed_bookings,
            COUNT(CASE WHEN b.status = 'cancelled' THEN 1 END) as cancelled_bookings,
            COUNT(CASE WHEN b.status = 'no_show' THEN 1 END) as no_show_bookings,

            -- Revenue metrics
            SUM(CASE WHEN b.status = 'completed' THEN b.service_price ELSE 0 END) as lifetime_value,
            AVG(CASE WHEN b.status = 'completed' THEN b.service_price END) as avg_booking_value,
            COALESCE(SUM(b.cancellation_fee_amount), 0) as total_cancellation_fees,
            COALESCE(SUM(b.no_show_fee_amount), 0) as total_no_show_fees,

            -- Behavior patterns
            COUNT(DISTINCT b.service_id) as unique_services_used,
            COUNT(DISTINCT b.professional_id) as unique_professionals_used,
            COUNT(DISTINCT sv.category) as service_categories_used,

            -- Frequency analysis
            ROUND(
                COUNT(*)::numeric /
                NULLIF(EXTRACT(EPOCH FROM (MAX(b.scheduled_at) - first_booking.first_booking_date))/2629746, 0), 2
            ) as avg_bookings_per_month,

            -- Loyalty indicators
            CASE
                WHEN COUNT(*) >= 10 THEN 'high_loyalty'
                WHEN COUNT(*) >= 5 THEN 'medium_loyalty'
                WHEN COUNT(*) >= 2 THEN 'low_loyalty'
                ELSE 'single_visit'
            END as loyalty_segment,

            -- Recency analysis
            CASE
                WHEN MAX(b.scheduled_at) >= CURRENT_DATE - INTERVAL '30 days' THEN 'active'
                WHEN MAX(b.scheduled_at) >= CURRENT_DATE - INTERVAL '90 days' THEN 'at_risk'
                WHEN MAX(b.scheduled_at) >= CURRENT_DATE - INTERVAL '180 days' THEN 'dormant'
                ELSE 'churned'
            END as recency_segment,

            -- Performance metrics
            ROUND(
                COUNT(CASE WHEN b.status = 'completed' THEN 1 END)::numeric /
                NULLIF(COUNT(*), 0) * 100, 2
            ) as completion_rate_pct,

            -- Seasonal patterns
            COUNT(CASE WHEN EXTRACT(month FROM b.scheduled_at) IN (12,1,2) THEN 1 END) as winter_bookings,
            COUNT(CASE WHEN EXTRACT(month FROM b.scheduled_at) IN (3,4,5) THEN 1 END) as spring_bookings,
            COUNT(CASE WHEN EXTRACT(month FROM b.scheduled_at) IN (6,7,8) THEN 1 END) as summer_bookings,
            COUNT(CASE WHEN EXTRACT(month FROM b.scheduled_at) IN (9,10,11) THEN 1 END) as fall_bookings,

            -- Update tracking
            NOW() as last_updated
        FROM bookings b
        JOIN (
            SELECT
                client_id,
                MIN(scheduled_at) as first_booking_date,
                MIN(p.salon_id) as salon_id
            FROM bookings b
            JOIN professionals p ON b.professional_id = p.id
            GROUP BY client_id
        ) first_booking ON b.client_id = first_booking.client_id
        JOIN users u ON b.client_id = u.id
        JOIN services sv ON b.service_id = sv.id
        JOIN salons s ON first_booking.salon_id = s.id
        WHERE b.scheduled_at >= CURRENT_DATE - INTERVAL '2 years'
        GROUP BY
            DATE_TRUNC('month', first_booking.first_booking_date),
            b.client_id,
            u.email,
            u.phone,
            first_booking.salon_id,
            s.name,
            first_booking.first_booking_date;
    """)

    # Create indexes for customer analytics
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_analytics_mv_client
        ON customer_analytics_mv (client_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_analytics_mv_cohort
        ON customer_analytics_mv (cohort_month, salon_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_analytics_mv_salon_loyalty
        ON customer_analytics_mv (salon_id, loyalty_segment);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_analytics_mv_recency
        ON customer_analytics_mv (recency_segment, last_booking_date DESC);
    """)

    # Create refresh functions
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_all_report_views()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY booking_metrics_mv;
            REFRESH MATERIALIZED VIEW CONCURRENTLY revenue_metrics_mv;
            REFRESH MATERIALIZED VIEW CONCURRENTLY professional_performance_mv;
            REFRESH MATERIALIZED VIEW CONCURRENTLY customer_analytics_mv;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_booking_metrics()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY booking_metrics_mv;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_revenue_metrics()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY revenue_metrics_mv;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_professional_performance()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY professional_performance_mv;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_customer_analytics()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY customer_analytics_mv;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop refresh functions
    op.execute("DROP FUNCTION IF EXISTS refresh_customer_analytics();")
    op.execute("DROP FUNCTION IF EXISTS refresh_professional_performance();")
    op.execute("DROP FUNCTION IF EXISTS refresh_revenue_metrics();")
    op.execute("DROP FUNCTION IF EXISTS refresh_booking_metrics();")
    op.execute("DROP FUNCTION IF EXISTS refresh_all_report_views();")

    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS customer_analytics_mv;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS professional_performance_mv;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS revenue_metrics_mv;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS booking_metrics_mv;")
