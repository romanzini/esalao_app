"""Temporary sync alembic env for migration generation"""

from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# Import models
from backend.app.db.models.base import Base
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

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = "postgresql://esalao_user:esalao_pass@localhost:5432/esalao_db"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = "postgresql://esalao_user:esalao_pass@localhost:5432/esalao_db"

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
