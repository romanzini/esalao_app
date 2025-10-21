"""Overbooking service for capacity management."""

import logging
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.booking import BookingStatus
from backend.app.db.models.overbooking import OverbookingConfig, OverbookingTimeframe
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.overbooking import OverbookingRepository

logger = logging.getLogger(__name__)


class OverbookingService:
    """Service for managing overbooking capacity and decisions."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.overbooking_repo = OverbookingRepository(session)
        self.booking_repo = BookingRepository(session)

    async def calculate_available_capacity(
        self,
        professional_id: int,
        target_datetime: datetime,
        service_duration_minutes: int,
        salon_id: Optional[int] = None,
        service_id: Optional[int] = None,
        base_capacity: int = 1  # Default: one appointment per slot
    ) -> Dict:
        """
        Calculate available capacity considering overbooking rules.

        Args:
            professional_id: Professional ID
            target_datetime: Target datetime for booking
            service_duration_minutes: Duration of the service
            salon_id: Salon ID for configuration lookup
            service_id: Service ID for configuration lookup
            base_capacity: Base capacity without overbooking

        Returns:
            Dictionary with capacity information
        """
        target_date = target_datetime.date()
        target_time = target_datetime.time()

        # Get effective overbooking configuration
        config = await self.overbooking_repo.get_effective_config(
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id,
            check_time=target_time,
            check_datetime=target_datetime
        )

        result = {
            "base_capacity": base_capacity,
            "overbooking_enabled": False,
            "max_capacity": base_capacity,
            "current_bookings": 0,
            "available_slots": 0,
            "overbooking_slots": 0,
            "no_show_rate": 0.0,
            "config_used": None,
            "warnings": []
        }

        if not config:
            logger.debug(f"No overbooking config found for professional {professional_id}")
            # Count current bookings for this slot
            current_bookings = await self._count_current_bookings(
                professional_id, target_datetime, service_duration_minutes
            )
            result["current_bookings"] = current_bookings
            result["available_slots"] = max(0, base_capacity - current_bookings)
            return result

        # Check if we have enough historical data
        no_show_stats = await self._get_no_show_statistics(
            professional_id=professional_id,
            salon_id=salon_id,
            service_id=service_id,
            historical_period_days=config.historical_period_days
        )

        # Validate minimum requirements
        if no_show_stats["total_bookings"] < config.min_historical_bookings:
            result["warnings"].append(
                f"Insufficient historical data: {no_show_stats['total_bookings']} < {config.min_historical_bookings}"
            )
            current_bookings = await self._count_current_bookings(
                professional_id, target_datetime, service_duration_minutes
            )
            result["current_bookings"] = current_bookings
            result["available_slots"] = max(0, base_capacity - current_bookings)
            return result

        no_show_rate = no_show_stats["no_show_rate"]

        # Check no-show rate thresholds
        if no_show_rate < config.min_no_show_rate:
            result["warnings"].append(
                f"No-show rate too low: {no_show_rate:.1f}% < {config.min_no_show_rate}%"
            )
            current_bookings = await self._count_current_bookings(
                professional_id, target_datetime, service_duration_minutes
            )
            result["current_bookings"] = current_bookings
            result["available_slots"] = max(0, base_capacity - current_bookings)
            return result

        if no_show_rate > config.max_no_show_rate:
            result["warnings"].append(
                f"No-show rate too high: {no_show_rate:.1f}% > {config.max_no_show_rate}%"
            )
            current_bookings = await self._count_current_bookings(
                professional_id, target_datetime, service_duration_minutes
            )
            result["current_bookings"] = current_bookings
            result["available_slots"] = max(0, base_capacity - current_bookings)
            return result

        # Calculate overbooking capacity
        max_capacity = config.calculate_max_capacity(base_capacity)
        current_bookings = await self._count_current_bookings(
            professional_id, target_datetime, service_duration_minutes
        )

        result.update({
            "overbooking_enabled": True,
            "max_capacity": max_capacity,
            "current_bookings": current_bookings,
            "available_slots": max(0, max_capacity - current_bookings),
            "overbooking_slots": max(0, max_capacity - base_capacity),
            "no_show_rate": no_show_rate,
            "config_used": {
                "id": config.id,
                "name": config.name,
                "scope": config.scope.value,
                "max_percentage": config.max_overbooking_percentage
            }
        })

        return result

    async def can_accept_booking(
        self,
        professional_id: int,
        target_datetime: datetime,
        service_duration_minutes: int,
        salon_id: Optional[int] = None,
        service_id: Optional[int] = None
    ) -> Tuple[bool, Dict]:
        """
        Check if a booking can be accepted considering overbooking.

        Returns:
            Tuple of (can_accept, capacity_info)
        """
        capacity_info = await self.calculate_available_capacity(
            professional_id=professional_id,
            target_datetime=target_datetime,
            service_duration_minutes=service_duration_minutes,
            salon_id=salon_id,
            service_id=service_id
        )

        can_accept = capacity_info["available_slots"] > 0

        return can_accept, capacity_info

    async def _count_current_bookings(
        self,
        professional_id: int,
        target_datetime: datetime,
        service_duration_minutes: int
    ) -> int:
        """Count current bookings that overlap with the target slot."""
        # Calculate slot end time
        slot_end = target_datetime + timedelta(minutes=service_duration_minutes)

        # Get bookings that overlap with this time slot
        overlapping_bookings = await self.booking_repo.find_overlapping_bookings(
            professional_id=professional_id,
            start_time=target_datetime,
            end_time=slot_end,
            exclude_statuses=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW]
        )

        return len(overlapping_bookings)

    async def _get_no_show_statistics(
        self,
        professional_id: int,
        salon_id: Optional[int] = None,
        service_id: Optional[int] = None,
        historical_period_days: int = 30
    ) -> Dict:
        """Get no-show statistics for the specified period."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=historical_period_days)

        # Get historical bookings
        historical_bookings = await self.booking_repo.find_by_criteria(
            professional_id=professional_id,
            salon_id=salon_id,
            service_id=service_id,
            start_date=start_date.date(),
            end_date=end_date.date(),
            include_completed=True
        )

        total_bookings = len(historical_bookings)
        no_show_bookings = len([
            booking for booking in historical_bookings
            if booking.status == BookingStatus.NO_SHOW
        ])

        no_show_rate = (no_show_bookings / total_bookings * 100) if total_bookings > 0 else 0.0

        return {
            "total_bookings": total_bookings,
            "no_show_bookings": no_show_bookings,
            "no_show_rate": no_show_rate,
            "period_start": start_date.date(),
            "period_end": end_date.date()
        }

    async def get_overbooking_status(
        self,
        professional_id: int,
        target_date: date,
        salon_id: Optional[int] = None,
        service_id: Optional[int] = None
    ) -> Dict:
        """Get overbooking status for a specific date."""
        # Get configuration
        config = await self.overbooking_repo.get_effective_config(
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id
        )

        # Get bookings for the date
        bookings = await self.booking_repo.list_by_professional_and_date(
            professional_id=professional_id,
            target_date=target_date
        )

        # Count by status
        status_counts = {}
        for status in BookingStatus:
            status_counts[status.value] = len([
                b for b in bookings if b.status == status
            ])

        return {
            "date": target_date.isoformat(),
            "professional_id": professional_id,
            "overbooking_enabled": config is not None,
            "config": {
                "id": config.id,
                "name": config.name,
                "max_percentage": config.max_overbooking_percentage
            } if config else None,
            "total_bookings": len(bookings),
            "bookings_by_status": status_counts,
            "potential_conflicts": status_counts.get("confirmed", 0) + status_counts.get("pending", 0)
        }

    async def create_configuration(self, config_data: dict) -> OverbookingConfig:
        """Create a new overbooking configuration."""
        # Validate configuration
        await self._validate_configuration(config_data)

        # Create configuration
        config = await self.overbooking_repo.create(config_data)
        await self.session.commit()

        logger.info(f"Created overbooking configuration: {config.name} (ID: {config.id})")
        return config

    async def _validate_configuration(self, config_data: dict) -> None:
        """Validate overbooking configuration data."""
        # Check for conflicts
        scope = config_data.get("scope")
        conflicts = await self.overbooking_repo.check_conflicts(
            scope=scope,
            salon_id=config_data.get("salon_id"),
            professional_id=config_data.get("professional_id"),
            service_id=config_data.get("service_id")
        )

        if conflicts:
            raise ValueError(f"Conflicting overbooking configuration already exists for scope {scope}")

        # Validate percentage range
        max_percentage = config_data.get("max_overbooking_percentage", 0)
        if not 0 <= max_percentage <= 100:
            raise ValueError("Overbooking percentage must be between 0 and 100")

        # Validate no-show rate thresholds
        min_rate = config_data.get("min_no_show_rate", 0)
        max_rate = config_data.get("max_no_show_rate", 100)

        if min_rate >= max_rate:
            raise ValueError("Minimum no-show rate must be less than maximum no-show rate")
