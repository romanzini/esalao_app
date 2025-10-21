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
        duration_minutes: int,
        service_price: float,
        status: BookingStatus = BookingStatus.PENDING,
        notes: str | None = None,
        deposit_amount: float | None = None,
        cancellation_policy_id: int | None = None,
    ) -> Booking:
        """
        Create a new booking.

        Args:
            client_id: ID of the client (User)
            professional_id: ID of the professional
            service_id: ID of the service
            scheduled_at: Scheduled date and time
            duration_minutes: Service duration in minutes
            service_price: Service price at booking time
            status: Booking status (default: PENDING)
            notes: Optional booking notes
            deposit_amount: Optional deposit/prepayment amount
            cancellation_policy_id: ID of applicable cancellation policy

        Returns:
            Created Booking instance
        """
        booking = Booking(
            client_id=client_id,
            professional_id=professional_id,
            service_id=service_id,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            service_price=service_price,
            status=status,
            notes=notes,
            deposit_amount=deposit_amount,
            cancellation_policy_id=cancellation_policy_id,
        )

        self.session.add(booking)
        await self.session.flush()

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

    async def update_status(
        self,
        booking_id: int,
        new_status: BookingStatus,
        cancellation_reason: str | None = None,
    ) -> Booking | None:
        """
        Update booking status.

        Args:
            booking_id: Booking ID
            new_status: New status
            cancellation_reason: Reason for cancellation (required if status is CANCELLED)

        Returns:
            Updated Booking instance or None if not found
        """
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None

        booking.status = new_status

        if new_status == BookingStatus.CANCELLED:
            booking.cancelled_at = datetime.now()
            booking.cancellation_reason = cancellation_reason

        await self.session.flush()

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

    async def find_by_criteria(
        self,
        status: BookingStatus | None = None,
        unit_id: int | None = None,
        professional_id: int | None = None,
        client_id: int | None = None,
        service_id: int | None = None,
        scheduled_after: datetime | None = None,
        scheduled_before: datetime | None = None,
        exclude_no_show: bool = False,
        include_no_show_only: bool = False,
        limit: int | None = None,
    ) -> list[Booking]:
        """
        Find bookings by multiple criteria.

        Args:
            status: Filter by booking status
            unit_id: Filter by unit ID
            professional_id: Filter by professional ID
            client_id: Filter by client ID
            service_id: Filter by service ID
            scheduled_after: Filter bookings scheduled after this time
            scheduled_before: Filter bookings scheduled before this time
            exclude_no_show: Exclude bookings marked as no-show
            include_no_show_only: Include only bookings marked as no-show
            limit: Maximum number of results

        Returns:
            List of matching bookings
        """
        stmt = select(Booking).options(
            selectinload(Booking.client),
            selectinload(Booking.professional),
            selectinload(Booking.service),
        )

        conditions = []

        if status:
            conditions.append(Booking.status == status)

        if unit_id:
            conditions.append(Booking.unit_id == unit_id)

        if professional_id:
            conditions.append(Booking.professional_id == professional_id)

        if client_id:
            conditions.append(Booking.client_id == client_id)

        if service_id:
            conditions.append(Booking.service_id == service_id)

        if scheduled_after:
            conditions.append(Booking.scheduled_at >= scheduled_after)

        if scheduled_before:
            conditions.append(Booking.scheduled_at <= scheduled_before)

        if exclude_no_show:
            conditions.append(Booking.marked_no_show_at.is_(None))

        if include_no_show_only:
            conditions.append(Booking.marked_no_show_at.is_not(None))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(Booking.scheduled_at.desc())

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_eligible_for_no_show_detection(
        self,
        cutoff_time: datetime,
        limit: int = 1000,
    ) -> List[Booking]:
        """
        Find bookings eligible for no-show detection.

        Args:
            cutoff_time: Bookings scheduled before this time are eligible
            limit: Maximum number of bookings to return

        Returns:
            List of bookings eligible for no-show evaluation
        """
        stmt = select(Booking).where(
            and_(
                # Scheduled time has passed (with grace period)
                Booking.scheduled_at < cutoff_time,
                # Status is confirmed or in progress
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]),
                # Not already marked as no-show
                Booking.marked_no_show_at.is_(None),
                # Not cancelled or completed
                ~Booking.status.in_([BookingStatus.CANCELLED, BookingStatus.COMPLETED])
            )
        ).order_by(Booking.scheduled_at.asc()).limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()
