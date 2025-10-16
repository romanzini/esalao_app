"""Booking repository for database operations."""

from datetime import date, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.professional import Professional


class BookingRepository:
    """Repository for Booking model database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        client_id: int,
        professional_id: int,
        service_id: int,
        scheduled_at: datetime,
        total_price: float,
        status: BookingStatus = BookingStatus.PENDING,
        notes: str | None = None,
    ) -> Booking:
        """
        Create a new booking.

        Args:
            client_id: ID of the client (User)
            professional_id: ID of the professional
            service_id: ID of the service
            scheduled_at: Scheduled date and time
            total_price: Total price for the booking
            status: Booking status (default: PENDING)
            notes: Optional booking notes

        Returns:
            Created Booking instance
        """
        booking = Booking(
            client_id=client_id,
            professional_id=professional_id,
            service_id=service_id,
            scheduled_at=scheduled_at,
            total_price=total_price,
            status=status,
            notes=notes,
        )

        self.session.add(booking)
        await self.session.commit()
        await self.session.refresh(booking)

        return booking

    async def get_by_id(self, booking_id: int, load_relationships: bool = False) -> Booking | None:
        """
        Get booking by ID.

        Args:
            booking_id: Booking ID
            load_relationships: Whether to eagerly load client, professional, service

        Returns:
            Booking instance or None if not found
        """
        stmt = select(Booking).where(Booking.id == booking_id)

        if load_relationships:
            stmt = stmt.options(
                selectinload(Booking.client),
                selectinload(Booking.professional).selectinload(Professional.user),
                selectinload(Booking.service),
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_client_id(self, client_id: int) -> list[Booking]:
        """
        List all bookings for a client.

        Args:
            client_id: Client (User) ID

        Returns:
            List of Booking instances ordered by scheduled_at descending
        """
        stmt = (
            select(Booking)
            .where(Booking.client_id == client_id)
            .options(
                selectinload(Booking.professional).selectinload(Professional.user),
                selectinload(Booking.service),
            )
            .order_by(Booking.scheduled_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_professional_id(self, professional_id: int) -> list[Booking]:
        """
        List all bookings for a professional.

        Args:
            professional_id: Professional ID

        Returns:
            List of Booking instances ordered by scheduled_at descending
        """
        stmt = (
            select(Booking)
            .where(Booking.professional_id == professional_id)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.service),
            )
            .order_by(Booking.scheduled_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_professional_and_date(
        self,
        professional_id: int,
        target_date: date,
    ) -> list[Booking]:
        """
        List bookings for a professional on a specific date.

        Args:
            professional_id: Professional ID
            target_date: Date to filter bookings

        Returns:
            List of Booking instances ordered by scheduled_at
        """
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        stmt = (
            select(Booking)
            .where(
                and_(
                    Booking.professional_id == professional_id,
                    Booking.scheduled_at >= start_datetime,
                    Booking.scheduled_at <= end_datetime,
                    Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                )
            )
            .options(selectinload(Booking.service))
            .order_by(Booking.scheduled_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: BookingStatus) -> list[Booking]:
        """
        List all bookings with a specific status.

        Args:
            status: Booking status

        Returns:
            List of Booking instances
        """
        stmt = (
            select(Booking)
            .where(Booking.status == status)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.professional),
                selectinload(Booking.service),
            )
            .order_by(Booking.scheduled_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def check_conflict(
        self,
        professional_id: int,
        scheduled_at: datetime,
        duration_minutes: int,
        exclude_booking_id: int | None = None,
    ) -> bool:
        """
        Check if there's a booking conflict for a professional.

        Args:
            professional_id: Professional ID
            scheduled_at: Proposed start time
            duration_minutes: Duration of the service
            exclude_booking_id: Optional booking ID to exclude from conflict check

        Returns:
            True if there's a conflict, False otherwise
        """
        from datetime import timedelta

        end_time = scheduled_at + timedelta(minutes=duration_minutes)

        stmt = select(Booking).where(
            and_(
                Booking.professional_id == professional_id,
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                or_(
                    # New booking starts during existing booking
                    and_(
                        Booking.scheduled_at <= scheduled_at,
                        Booking.scheduled_at + timedelta(minutes=Booking.duration_minutes) > scheduled_at,
                    ),
                    # New booking ends during existing booking
                    and_(
                        Booking.scheduled_at < end_time,
                        Booking.scheduled_at + timedelta(minutes=Booking.duration_minutes) >= end_time,
                    ),
                    # New booking completely contains existing booking
                    and_(
                        Booking.scheduled_at >= scheduled_at,
                        Booking.scheduled_at + timedelta(minutes=Booking.duration_minutes) <= end_time,
                    ),
                ),
            )
        )

        if exclude_booking_id:
            stmt = stmt.where(Booking.id != exclude_booking_id)

        result = await self.session.execute(stmt)
        conflicting = result.scalar_one_or_none()

        return conflicting is not None

    async def update_status(self, booking_id: int, status: BookingStatus) -> Booking | None:
        """
        Update booking status.

        Args:
            booking_id: Booking ID
            status: New status

        Returns:
            Updated Booking instance or None if not found
        """
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None

        booking.status = status
        await self.session.commit()
        await self.session.refresh(booking)

        return booking

    async def update(
        self,
        booking_id: int,
        **fields,
    ) -> Booking | None:
        """
        Update booking fields.

        Args:
            booking_id: Booking ID
            **fields: Fields to update

        Returns:
            Updated Booking instance or None if not found
        """
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None

        for key, value in fields.items():
            if hasattr(booking, key):
                setattr(booking, key, value)

        await self.session.commit()
        await self.session.refresh(booking)

        return booking

    async def delete(self, booking_id: int) -> bool:
        """
        Delete a booking (soft delete via status change is recommended).

        Args:
            booking_id: Booking ID

        Returns:
            True if deleted, False if not found
        """
        booking = await self.get_by_id(booking_id)
        if not booking:
            return False

        await self.session.delete(booking)
        await self.session.commit()

        return True

    async def exists_by_id(self, booking_id: int) -> bool:
        """
        Check if booking exists by ID.

        Args:
            booking_id: Booking ID

        Returns:
            True if exists, False otherwise
        """
        stmt = select(Booking.id).where(Booking.id == booking_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
