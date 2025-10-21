"""Alembic environment configuration."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.app.core.config import settings
from backend.app.db.models.base import Base

# Import all models here for Alembic autogenerate
from backend.app.db.models.user import User  # noqa: F401
from backend.app.db.models.salon import Salon  # noqa: F401
from backend.app.db.models.professional import Professional  # noqa: F401
from backend.app.db.models.service import Service  # noqa: F401
from backend.app.db.models.availability import Availability  # noqa: F401
from backend.app.db.models.booking import Booking  # noqa: F401
from backend.app.db.models.payment import Payment, PaymentMethod  # noqa: F401
from backend.app.db.models.payment_log import PaymentLog  # noqa: F401
from backend.app.db.models.payment_metrics import PaymentMetricsSnapshot, ProviderPerformanceMetrics, PaymentAlert  # noqa: F401
from backend.app.db.models.cancellation_policy import CancellationPolicy, CancellationTier  # noqa: F401
from backend.app.db.models.audit_event import AuditEvent  # noqa: F401

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set SQLAlchemy URL from settings
# Use raw string to avoid interpolation issues with % in URL
config.set_main_option(
    "sqlalchemy.url",
    str(settings.DATABASE_URL).replace("%", "%%")
)

# Add model's MetaData for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
