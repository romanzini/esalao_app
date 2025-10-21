"""Overbooking configuration model."""

from datetime import datetime, time
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Time, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.salon import Salon
    from backend.app.db.models.professional import Professional
    from backend.app.db.models.service import Service


class OverbookingScope(str, Enum):
    """Scope of overbooking configuration."""
    
    GLOBAL = "global"  # Platform-wide default
    SALON = "salon"  # Salon-specific
    PROFESSIONAL = "professional"  # Professional-specific
    SERVICE = "service"  # Service-specific


class OverbookingTimeframe(str, Enum):
    """Timeframe for overbooking limits."""
    
    HOURLY = "hourly"  # Per hour
    DAILY = "daily"  # Per day
    WEEKLY = "weekly"  # Per week


class OverbookingConfig(Base, IDMixin, TimestampMixin):
    """
    Overbooking configuration model.
    
    Manages overbooking limits and rules based on historical no-show data
    to optimize capacity utilization while minimizing conflicts.
    """

    __tablename__ = "overbooking_configs"

    # Configuration name and description
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Configuration name"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Configuration description"
    )

    # Scope configuration
    scope: Mapped[OverbookingScope] = mapped_column(
        SQLEnum(OverbookingScope),
        nullable=False,
        default=OverbookingScope.SALON,
        comment="Scope of this configuration"
    )

    # Relationships for scope
    salon_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("salons.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Salon ID if scope is salon"
    )
    
    professional_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Professional ID if scope is professional"
    )
    
    service_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Service ID if scope is service"
    )

    # Overbooking limits
    max_overbooking_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=20.0,
        comment="Maximum overbooking percentage (0-100)"
    )
    
    timeframe: Mapped[OverbookingTimeframe] = mapped_column(
        SQLEnum(OverbookingTimeframe),
        nullable=False,
        default=OverbookingTimeframe.HOURLY,
        comment="Timeframe for overbooking calculation"
    )

    # Time-based restrictions
    start_time: Mapped[Optional[time]] = mapped_column(
        Time,
        nullable=True,
        comment="Start time for overbooking (if time-restricted)"
    )
    
    end_time: Mapped[Optional[time]] = mapped_column(
        Time,
        nullable=True,
        comment="End time for overbooking (if time-restricted)"
    )

    # Historical data requirements
    min_historical_bookings: Mapped[int] = mapped_column(
        nullable=False,
        default=10,
        comment="Minimum historical bookings required to enable overbooking"
    )
    
    historical_period_days: Mapped[int] = mapped_column(
        nullable=False,
        default=30,
        comment="Historical period in days to analyze no-show patterns"
    )

    # No-show rate thresholds
    min_no_show_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=5.0,
        comment="Minimum no-show rate (%) to enable overbooking"
    )
    
    max_no_show_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=50.0,
        comment="Maximum no-show rate (%) for safety cap"
    )

    # Status and settings
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Whether this configuration is active"
    )
    
    effective_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date from which this configuration is effective"
    )
    
    effective_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date until which this configuration is effective"
    )

    # Relationships
    salon: Mapped[Optional["Salon"]] = relationship(
        "Salon",
        back_populates="overbooking_configs",
        lazy="select"
    )
    
    professional: Mapped[Optional["Professional"]] = relationship(
        "Professional",
        back_populates="overbooking_configs",
        lazy="select"
    )
    
    service: Mapped[Optional["Service"]] = relationship(
        "Service",
        back_populates="overbooking_configs",
        lazy="select"
    )

    def __repr__(self) -> str:
        """String representation of overbooking config."""
        return f"<OverbookingConfig(id={self.id}, name='{self.name}', scope={self.scope}, max_percentage={self.max_overbooking_percentage}%)>"

    @property
    def is_currently_effective(self) -> bool:
        """Check if configuration is currently effective."""
        now = datetime.utcnow()
        
        if not self.is_active:
            return False
            
        if self.effective_from and now < self.effective_from:
            return False
            
        if self.effective_until and now > self.effective_until:
            return False
            
        return True

    @property
    def max_overbooking_decimal(self) -> float:
        """Get max overbooking as decimal (0.20 for 20%)."""
        return float(self.max_overbooking_percentage) / 100.0

    def applies_to_time(self, check_time: time) -> bool:
        """Check if config applies to a specific time."""
        if not self.start_time or not self.end_time:
            return True
            
        return self.start_time <= check_time <= self.end_time

    def calculate_max_capacity(self, base_capacity: int) -> int:
        """Calculate maximum capacity including overbooking."""
        if not self.is_currently_effective:
            return base_capacity
            
        additional_capacity = int(base_capacity * self.max_overbooking_decimal)
        return base_capacity + additional_capacity