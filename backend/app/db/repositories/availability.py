"""Availability repository for database operations."""

from datetime import date, time

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.availability import Availability, DayOfWeek


class AvailabilityRepository:
    """Repository for Availability model database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        professional_id: int,
        day_of_week: DayOfWeek,
        start_time: time,
        end_time: time,
        effective_date: date | None = None,
        expiry_date: date | None = None,
    ) -> Availability:
        """
        Create a new availability slot.

        Args:
            professional_id: ID of the professional
            day_of_week: Day of the week
            start_time: Start time
            end_time: End time
            effective_date: Optional start date for validity
            expiry_date: Optional end date for validity

        Returns:
            Created Availability instance
        """
        availability = Availability(
            professional_id=professional_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            effective_date=effective_date,
            expiry_date=expiry_date,
        )

        self.session.add(availability)
        await self.session.commit()
        await self.session.refresh(availability)

        return availability

    async def get_by_id(self, availability_id: int, load_professional: bool = False) -> Availability | None:
        """
        Get availability by ID.

        Args:
            availability_id: Availability ID
            load_professional: Whether to eagerly load professional relationship

        Returns:
            Availability instance or None if not found
        """
        stmt = select(Availability).where(Availability.id == availability_id)

        if load_professional:
            stmt = stmt.options(selectinload(Availability.professional))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_professional_id(self, professional_id: int) -> list[Availability]:
        """
        List all availability slots for a professional.

        Args:
            professional_id: Professional ID

        Returns:
            List of Availability instances
        """
        stmt = (
            select(Availability)
            .where(Availability.professional_id == professional_id)
            .order_by(Availability.day_of_week, Availability.start_time)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_professional_and_day(
        self,
        professional_id: int,
        day_of_week: DayOfWeek,
    ) -> list[Availability]:
        """
        List availability slots for a professional on a specific day.

        Args:
            professional_id: Professional ID
            day_of_week: Day of the week

        Returns:
            List of Availability instances
        """
        stmt = (
            select(Availability)
            .where(
                and_(
                    Availability.professional_id == professional_id,
                    Availability.day_of_week == day_of_week,
                )
            )
            .order_by(Availability.start_time)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_by_professional_and_day(
        self,
        professional_id: int,
        day_of_week: DayOfWeek,
        check_date: date,
    ) -> list[Availability]:
        """
        List active availability slots for a professional on a specific day.

        Considers effective_date and expiry_date to filter active slots.

        Args:
            professional_id: Professional ID
            day_of_week: Day of the week
            check_date: Date to check validity against

        Returns:
            List of active Availability instances
        """
        stmt = (
            select(Availability)
            .where(
                and_(
                    Availability.professional_id == professional_id,
                    Availability.day_of_week == day_of_week,
                )
            )
            .order_by(Availability.start_time)
        )

        result = await self.session.execute(stmt)
        availabilities = list(result.scalars().all())

        # Filter by effective and expiry dates
        active = []
        for avail in availabilities:
            if avail.effective_date and check_date < avail.effective_date:
                continue
            if avail.expiry_date and check_date > avail.expiry_date:
                continue
            active.append(avail)

        return active

    async def update(
        self,
        availability_id: int,
        **fields,
    ) -> Availability | None:
        """
        Update availability fields.

        Args:
            availability_id: Availability ID
            **fields: Fields to update

        Returns:
            Updated Availability instance or None if not found
        """
        availability = await self.get_by_id(availability_id)
        if not availability:
            return None

        for key, value in fields.items():
            if hasattr(availability, key):
                setattr(availability, key, value)

        await self.session.commit()
        await self.session.refresh(availability)

        return availability

    async def delete(self, availability_id: int) -> bool:
        """
        Delete an availability slot.

        Args:
            availability_id: Availability ID

        Returns:
            True if deleted, False if not found
        """
        availability = await self.get_by_id(availability_id)
        if not availability:
            return False

        await self.session.delete(availability)
        await self.session.commit()

        return True

    async def delete_by_professional_id(self, professional_id: int) -> int:
        """
        Delete all availability slots for a professional.

        Args:
            professional_id: Professional ID

        Returns:
            Number of deleted records
        """
        availabilities = await self.list_by_professional_id(professional_id)

        for availability in availabilities:
            await self.session.delete(availability)

        await self.session.commit()

        return len(availabilities)

    async def exists_by_id(self, availability_id: int) -> bool:
        """
        Check if availability exists by ID.

        Args:
            availability_id: Availability ID

        Returns:
            True if exists, False otherwise
        """
        stmt = select(Availability.id).where(Availability.id == availability_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
