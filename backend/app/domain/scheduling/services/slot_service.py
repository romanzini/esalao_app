"""Slot calculation service for scheduling."""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.availability import DayOfWeek
from backend.app.db.repositories.availability import AvailabilityRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.service import ServiceRepository
from backend.app.domain.scheduling.schemas import SlotResponse, TimeSlot

if TYPE_CHECKING:
    from backend.app.db.models.availability import Availability
    from backend.app.db.models.booking import Booking
    from backend.app.db.models.service import Service


class SlotService:
    """Service for calculating available time slots."""

    def __init__(self, session: AsyncSession):
        """
        Initialize service with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.availability_repo = AvailabilityRepository(session)
        self.booking_repo = BookingRepository(session)
        self.service_repo = ServiceRepository(session)

    async def calculate_available_slots(
        self,
        professional_id: int,
        target_date: date,
        service_id: int,
        slot_interval_minutes: int = 30,
    ) -> SlotResponse:
        """
        Calculate available time slots for a professional on a specific date.

        This method:
        1. Retrieves the service to get its duration
        2. Gets the professional's availability for the target date
        3. Gets all existing bookings for that date
        4. Generates time slots based on availability windows
        5. Filters out slots that conflict with existing bookings

        Args:
            professional_id: ID of the professional
            target_date: Date to calculate slots for
            service_id: ID of the service to book
            slot_interval_minutes: Interval between slot start times (default: 30)

        Returns:
            SlotResponse with list of available time slots

        Raises:
            ValueError: If service not found or professional has no availability
        """
        # Get service details
        service = await self.service_repo.get_by_id(service_id)
        if not service:
            raise ValueError(f"Service with ID {service_id} not found")

        service_duration = service.duration_minutes

        # Get day of week from target date
        day_of_week = DayOfWeek(target_date.weekday())

        # Get active availabilities for the professional on this day
        availabilities = await self.availability_repo.list_active_by_professional_and_day(
            professional_id=professional_id,
            day_of_week=day_of_week,
            check_date=target_date,
        )

        if not availabilities:
            return SlotResponse(
                professional_id=professional_id,
                date=target_date.isoformat(),
                service_id=service_id,
                service_duration_minutes=service_duration,
                slots=[],
                total_slots=0,
            )

        # Get existing bookings for this date
        existing_bookings = await self.booking_repo.list_by_professional_and_date(
            professional_id=professional_id,
            target_date=target_date,
        )

        # Generate slots from availability windows
        all_slots = self._generate_slots_from_availabilities(
            availabilities=availabilities,
            target_date=target_date,
            service_duration=service_duration,
            slot_interval=slot_interval_minutes,
        )

        # Filter out slots that conflict with existing bookings
        available_slots = self._filter_conflicting_slots(
            slots=all_slots,
            bookings=existing_bookings,
            service=service,
        )

        return SlotResponse(
            professional_id=professional_id,
            date=target_date.isoformat(),
            service_id=service_id,
            service_duration_minutes=service_duration,
            slots=available_slots,
            total_slots=len(available_slots),
        )

    def _generate_slots_from_availabilities(
        self,
        availabilities: list["Availability"],
        target_date: date,
        service_duration: int,
        slot_interval: int,
    ) -> list[TimeSlot]:
        """
        Generate time slots from availability windows.

        Args:
            availabilities: List of availability records
            target_date: Target date
            service_duration: Duration of service in minutes
            slot_interval: Interval between slots in minutes

        Returns:
            List of TimeSlot objects
        """
        slots = []

        for availability in availabilities:
            # Combine date with availability times
            start_datetime = datetime.combine(target_date, availability.start_time)
            end_datetime = datetime.combine(target_date, availability.end_time)

            # Generate slots within this availability window
            current_time = start_datetime

            while current_time + timedelta(minutes=service_duration) <= end_datetime:
                slot_end = current_time + timedelta(minutes=service_duration)

                slots.append(
                    TimeSlot(
                        start_time=current_time,
                        end_time=slot_end,
                        available=True,
                    )
                )

                current_time += timedelta(minutes=slot_interval)

        # Sort slots by start time
        slots.sort(key=lambda s: s.start_time)

        return slots

    def _filter_conflicting_slots(
        self,
        slots: list[TimeSlot],
        bookings: list["Booking"],
        service: "Service",
    ) -> list[TimeSlot]:
        """
        Filter out slots that conflict with existing bookings.

        A slot conflicts if:
        - The slot starts during an existing booking
        - The slot ends during an existing booking
        - The slot completely contains an existing booking

        Args:
            slots: List of generated time slots
            bookings: List of existing bookings
            service: Service being booked

        Returns:
            List of available (non-conflicting) time slots
        """
        if not bookings:
            return slots

        available_slots = []

        for slot in slots:
            is_available = True

            for booking in bookings:
                booking_end = booking.scheduled_at + timedelta(
                    minutes=service.duration_minutes
                )

                # Check for overlap
                # Slot starts before booking ends AND slot ends after booking starts
                if slot.start_time < booking_end and slot.end_time > booking.scheduled_at:
                    is_available = False
                    break

            if is_available:
                available_slots.append(slot)
            else:
                # Mark slot as unavailable (for debugging/logging purposes)
                slot.available = False

        return available_slots

    async def check_slot_availability(
        self,
        professional_id: int,
        scheduled_at: datetime,
        service_id: int,
    ) -> bool:
        """
        Check if a specific time slot is available for booking.

        Args:
            professional_id: ID of the professional
            scheduled_at: Proposed booking datetime
            service_id: ID of the service

        Returns:
            True if slot is available, False otherwise

        Raises:
            ValueError: If service not found
        """
        # Get service details
        service = await self.service_repo.get_by_id(service_id)
        if not service:
            raise ValueError(f"Service with ID {service_id} not found")

        # Check if there's a conflict with existing bookings
        has_conflict = await self.booking_repo.check_conflict(
            professional_id=professional_id,
            scheduled_at=scheduled_at,
            duration_minutes=service.duration_minutes,
        )

        if has_conflict:
            return False

        # Check if the slot falls within professional's availability
        target_date = scheduled_at.date()
        day_of_week = DayOfWeek(target_date.weekday())

        availabilities = await self.availability_repo.list_active_by_professional_and_day(
            professional_id=professional_id,
            day_of_week=day_of_week,
            check_date=target_date,
        )

        if not availabilities:
            return False

        # Check if scheduled time falls within any availability window
        scheduled_time = scheduled_at.time()
        service_end_time = (scheduled_at + timedelta(minutes=service.duration_minutes)).time()

        for availability in availabilities:
            # Slot must start at or after availability start
            # AND end at or before availability end
            if (
                availability.start_time <= scheduled_time
                and service_end_time <= availability.end_time
            ):
                return True

        return False

    async def get_next_available_slot(
        self,
        professional_id: int,
        service_id: int,
        from_date: date | None = None,
        max_days_ahead: int = 30,
    ) -> TimeSlot | None:
        """
        Find the next available slot for a service.

        Args:
            professional_id: ID of the professional
            service_id: ID of the service
            from_date: Start searching from this date (default: today)
            max_days_ahead: Maximum days to search ahead (default: 30)

        Returns:
            Next available TimeSlot or None if no slots found

        Raises:
            ValueError: If service not found
        """
        if from_date is None:
            from_date = date.today()

        # Get service to validate it exists
        service = await self.service_repo.get_by_id(service_id)
        if not service:
            raise ValueError(f"Service with ID {service_id} not found")

        # Search for available slots day by day
        current_date = from_date

        for _ in range(max_days_ahead):
            slots_response = await self.calculate_available_slots(
                professional_id=professional_id,
                target_date=current_date,
                service_id=service_id,
            )

            if slots_response.slots:
                # Return the first available slot
                return slots_response.slots[0]

            current_date += timedelta(days=1)

        # No available slots found within the search window
        return None
