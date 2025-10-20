"""Base SQLAlchemy models and mixins."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, func, String
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case)."""
        import re
        name = cls.__name__
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IDMixin:
    """Mixin to add integer primary key id."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class UUIDMixin:
    """Mixin to add UUID string primary key id."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
