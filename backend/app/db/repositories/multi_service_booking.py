"""Repository for MultiServiceBooking operations."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.multi_service_booking import MultiServiceBooking, MultiServiceBookingStatus
from backend.app.db.models.booking import Booking, BookingStatus

logger = logging.getLogger(__name__)


class MultiServiceBookingRepository:
    """Repository for MultiServiceBooking database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        client_id: int,
        primary_professional_id: int,
        package_name: str,
        total_price: float,
        total_duration_minutes: int,
        starts_at: datetime,
        ends_at: datetime,
        notes: Optional[str] = None,
        status: MultiServiceBookingStatus = MultiServiceBookingStatus.PENDING,
    ) -> MultiServiceBooking:
        """
        Create a new multi-service booking.

        Args:
            client_id: ID of the client
            primary_professional_id: ID of the primary professional
            package_name: Name/description of the service package
            total_price: Total price for all services
            total_duration_minutes: Total duration in minutes
            starts_at: Start time of first service
            ends_at: End time of last service
            notes: Optional notes
            status: Initial status

        Returns:
            Created MultiServiceBooking instance
        """
        multi_booking = MultiServiceBooking(
            client_id=client_id,
            primary_professional_id=primary_professional_id,
            package_name=package_name,
            total_price=total_price,
            total_duration_minutes=total_duration_minutes,
            total_services_count=0,  # Will be updated when services are added
            starts_at=starts_at,
            ends_at=ends_at,
            notes=notes,
            status=status,
        )

        self.session.add(multi_booking)
        await self.session.flush()

        return multi_booking

    async def get_by_id(self, multi_booking_id: int) -> Optional[MultiServiceBooking]:
        """Get multi-service booking by ID with related data."""
        query = (
            select(MultiServiceBooking)
            .options(
                selectinload(MultiServiceBooking.client),
                selectinload(MultiServiceBooking.primary_professional),
                selectinload(MultiServiceBooking.individual_bookings).selectinload(Booking.service),
                selectinload(MultiServiceBooking.individual_bookings).selectinload(Booking.professional),
            )
            .where(MultiServiceBooking.id == multi_booking_id)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_client(
        self,
        client_id: int,
        status_filter: Optional[List[MultiServiceBookingStatus]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MultiServiceBooking]:
        """Get multi-service bookings by client ID."""
        query = (
            select(MultiServiceBooking)
            .options(
                selectinload(MultiServiceBooking.primary_professional),
                selectinload(MultiServiceBooking.individual_bookings),
            )
            .where(MultiServiceBooking.client_id == client_id)
        )

        if status_filter:
            query = query.where(MultiServiceBooking.status.in_(status_filter))

        query = query.order_by(desc(MultiServiceBooking.starts_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_professional(
        self,
        professional_id: int,
        status_filter: Optional[List[MultiServiceBookingStatus]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MultiServiceBooking]:
        """Get multi-service bookings by professional ID."""
        query = (
            select(MultiServiceBooking)
            .options(
                selectinload(MultiServiceBooking.client),
                selectinload(MultiServiceBooking.individual_bookings),
            )
            .where(MultiServiceBooking.primary_professional_id == professional_id)
        )

        if status_filter:
            query = query.where(MultiServiceBooking.status.in_(status_filter))

        if start_date:
            query = query.where(MultiServiceBooking.starts_at >= start_date)

        if end_date:
            query = query.where(MultiServiceBooking.ends_at <= end_date)

        query = query.order_by(desc(MultiServiceBooking.starts_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        multi_booking_id: int,
        new_status: MultiServiceBookingStatus,
        cancellation_reason: Optional[str] = None,
        cancelled_by_id: Optional[int] = None,
    ) -> Optional[MultiServiceBooking]:
        """Update multi-service booking status."""
        multi_booking = await self.get_by_id(multi_booking_id)
        if not multi_booking:
            return None

        multi_booking.status = new_status
        multi_booking.updated_at = datetime.utcnow()

        if new_status in (MultiServiceBookingStatus.CANCELLED, MultiServiceBookingStatus.PARTIALLY_CANCELLED):
            multi_booking.cancellation_reason = cancellation_reason
            multi_booking.cancelled_at = datetime.utcnow()
            multi_booking.cancelled_by_id = cancelled_by_id

        await self.session.flush()
        return multi_booking

    async def add_individual_booking(
        self,
        multi_booking_id: int,
        booking: Booking,
    ) -> bool:
        """Add an individual booking to a multi-service booking."""
        multi_booking = await self.get_by_id(multi_booking_id)
        if not multi_booking:
            return False

        # Update the booking to reference the multi-service booking
        booking.multi_service_booking_id = multi_booking_id

        # Update the services count
        multi_booking.total_services_count = len(multi_booking.individual_bookings) + 1

        await self.session.flush()
        return True

    async def calculate_and_update_status(self, multi_booking_id: int) -> Optional[MultiServiceBookingStatus]:
        """
        Calculate and update status based on individual booking statuses.

        Returns:
            Updated status or None if booking not found
        """
        multi_booking = await self.get_by_id(multi_booking_id)
        if not multi_booking:
            return None

        individual_bookings = multi_booking.individual_bookings
        if not individual_bookings:
            return multi_booking.status

        total_bookings = len(individual_bookings)
        completed_bookings = sum(
            1 for booking in individual_bookings
            if booking.status in (BookingStatus.COMPLETED, BookingStatus.NO_SHOW)
        )
        cancelled_bookings = sum(
            1 for booking in individual_bookings
            if booking.status == BookingStatus.CANCELLED
        )
        in_progress_bookings = sum(
            1 for booking in individual_bookings
            if booking.status == BookingStatus.IN_PROGRESS
        )

        # Determine new status
        new_status = multi_booking.status

        if cancelled_bookings == total_bookings:
            new_status = MultiServiceBookingStatus.CANCELLED
        elif cancelled_bookings > 0:
            new_status = MultiServiceBookingStatus.PARTIALLY_CANCELLED
        elif completed_bookings == total_bookings:
            new_status = MultiServiceBookingStatus.COMPLETED
        elif completed_bookings > 0 or in_progress_bookings > 0:
            new_status = MultiServiceBookingStatus.PARTIALLY_COMPLETED
        else:
            # All pending or confirmed
            confirmed_bookings = sum(
                1 for booking in individual_bookings
                if booking.status == BookingStatus.CONFIRMED
            )
            if confirmed_bookings == total_bookings:
                new_status = MultiServiceBookingStatus.CONFIRMED

        # Update if status changed
        if new_status != multi_booking.status:
            multi_booking.status = new_status
            multi_booking.updated_at = datetime.utcnow()
            await self.session.flush()

        return new_status

    async def get_upcoming_packages(
        self,
        professional_id: Optional[int] = None,
        client_id: Optional[int] = None,
        hours_ahead: int = 24,
    ) -> List[MultiServiceBooking]:
        """Get upcoming multi-service bookings within specified hours."""
        from_time = datetime.utcnow()
        to_time = datetime.utcnow().replace(hour=23, minute=59, second=59)
        if hours_ahead > 24:
            to_time = datetime.utcnow().replace(hour=23, minute=59, second=59)
            # Add extra days if needed
            import datetime as dt
            to_time += dt.timedelta(days=hours_ahead // 24)

        query = (
            select(MultiServiceBooking)
            .options(
                selectinload(MultiServiceBooking.client),
                selectinload(MultiServiceBooking.primary_professional),
                selectinload(MultiServiceBooking.individual_bookings),
            )
            .where(
                and_(
                    MultiServiceBooking.starts_at >= from_time,
                    MultiServiceBooking.starts_at <= to_time,
                    MultiServiceBooking.status.in_([
                        MultiServiceBookingStatus.CONFIRMED,
                        MultiServiceBookingStatus.PARTIALLY_COMPLETED,
                    ])
                )
            )
        )

        if professional_id:
            query = query.where(MultiServiceBooking.primary_professional_id == professional_id)

        if client_id:
            query = query.where(MultiServiceBooking.client_id == client_id)

        query = query.order_by(MultiServiceBooking.starts_at)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, multi_booking_id: int) -> bool:
        """
        Delete multi-service booking and all related individual bookings.

        Returns:
            True if deleted, False if not found
        """
        multi_booking = await self.get_by_id(multi_booking_id)
        if not multi_booking:
            return False

        # Delete individual bookings first (cascade should handle this, but being explicit)
        for booking in multi_booking.individual_bookings:
            await self.session.delete(booking)

        await self.session.delete(multi_booking)
        await self.session.flush()

        return True

    async def get_statistics(
        self,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get statistics for multi-service bookings."""
        query = select(MultiServiceBooking)

        if professional_id:
            query = query.where(MultiServiceBooking.primary_professional_id == professional_id)

        if start_date:
            query = query.where(MultiServiceBooking.created_at >= start_date)

        if end_date:
            query = query.where(MultiServiceBooking.created_at <= end_date)

        # Get total count
        total_query = select(func.count(MultiServiceBooking.id)).select_from(query.subquery())
        total_result = await self.session.execute(total_query)
        total_count = total_result.scalar()

        # Get count by status
        status_query = (
            select(MultiServiceBooking.status, func.count(MultiServiceBooking.id))
            .select_from(query.subquery())
            .group_by(MultiServiceBooking.status)
        )
        status_result = await self.session.execute(status_query)
        status_counts = dict(status_result.all())

        # Get revenue
        revenue_query = select(func.sum(MultiServiceBooking.total_price)).select_from(
            query.where(
                MultiServiceBooking.status.in_([
                    MultiServiceBookingStatus.COMPLETED,
                    MultiServiceBookingStatus.PARTIALLY_COMPLETED,
                ])
            ).subquery()
        )
        revenue_result = await self.session.execute(revenue_query)
        total_revenue = revenue_result.scalar() or 0

        return {
            "total_packages": total_count,
            "status_breakdown": status_counts,
            "total_revenue": float(total_revenue),
            "average_package_value": float(total_revenue / total_count) if total_count > 0 else 0,
        }
