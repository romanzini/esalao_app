"""Unit tests for SlotService."""

from datetime import date, datetime, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.db.models.availability import Availability, DayOfWeek
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.service import Service
from backend.app.domain.scheduling.services.slot_service import SlotService


@pytest.fixture
def mock_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def slot_service(mock_session):
    """Create SlotService instance with mocked session."""
    return SlotService(mock_session)


@pytest.fixture
def sample_service():
    """Sample service with 60-minute duration."""
    service = MagicMock(spec=Service)
    service.id = 1
    service.duration_minutes = 60
    service.name = "Haircut"
    service.price = 50.0
    return service


@pytest.fixture
def sample_availability():
    """Sample availability from 9 AM to 5 PM."""
    availability = MagicMock(spec=Availability)
    availability.id = 1
    availability.professional_id = 1
    availability.day_of_week = DayOfWeek.MONDAY
    availability.start_time = time(9, 0)
    availability.end_time = time(17, 0)
    availability.effective_date = None
    availability.expiry_date = None
    return availability


@pytest.mark.asyncio
async def test_calculate_available_slots_no_service(slot_service):
    """Test that ValueError is raised when service doesn't exist."""
    # Mock service repository to return None
    slot_service.service_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="Service with ID 999 not found"):
        await slot_service.calculate_available_slots(
            professional_id=1,
            target_date=date(2025, 10, 16),
            service_id=999,
        )


@pytest.mark.asyncio
async def test_calculate_available_slots_no_availability(
    slot_service, sample_service
):
    """Test that empty slots are returned when professional has no availability."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)
    slot_service.availability_repo.list_active_by_professional_and_day = AsyncMock(
        return_value=[]
    )

    result = await slot_service.calculate_available_slots(
        professional_id=1,
        target_date=date(2025, 10, 16),
        service_id=1,
    )

    assert result.professional_id == 1
    assert result.service_id == 1
    assert result.slots == []
    assert result.total_slots == 0


@pytest.mark.asyncio
async def test_calculate_available_slots_with_availability_no_bookings(
    slot_service, sample_service, sample_availability
):
    """Test slot calculation with availability but no existing bookings."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)
    slot_service.availability_repo.list_active_by_professional_and_day = AsyncMock(
        return_value=[sample_availability]
    )
    slot_service.booking_repo.list_by_professional_and_date = AsyncMock(
        return_value=[]
    )

    target_date = date(2025, 10, 20)  # Monday

    result = await slot_service.calculate_available_slots(
        professional_id=1,
        target_date=target_date,
        service_id=1,
        slot_interval_minutes=60,  # 1-hour slots
    )

    assert result.professional_id == 1
    assert result.service_id == 1
    assert result.service_duration_minutes == 60
    assert len(result.slots) == 8  # 9 AM to 5 PM with 60-min service = 8 slots
    assert result.total_slots == 8

    # Check first slot
    assert result.slots[0].start_time == datetime(2025, 10, 20, 9, 0)
    assert result.slots[0].end_time == datetime(2025, 10, 20, 10, 0)
    assert result.slots[0].available is True

    # Check last slot
    assert result.slots[-1].start_time == datetime(2025, 10, 20, 16, 0)
    assert result.slots[-1].end_time == datetime(2025, 10, 20, 17, 0)


@pytest.mark.asyncio
async def test_calculate_available_slots_with_existing_booking(
    slot_service, sample_service, sample_availability
):
    """Test slot calculation with existing booking blocking some slots."""
    # Create a booking at 10 AM
    booking = MagicMock(spec=Booking)
    booking.id = 1
    booking.scheduled_at = datetime(2025, 10, 20, 10, 0)
    booking.status = BookingStatus.CONFIRMED

    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)
    slot_service.availability_repo.list_active_by_professional_and_day = AsyncMock(
        return_value=[sample_availability]
    )
    slot_service.booking_repo.list_by_professional_and_date = AsyncMock(
        return_value=[booking]
    )

    target_date = date(2025, 10, 20)

    result = await slot_service.calculate_available_slots(
        professional_id=1,
        target_date=target_date,
        service_id=1,
        slot_interval_minutes=60,
    )

    # Should have 7 slots (8 total - 1 blocked by booking)
    assert len(result.slots) == 7

    # 10 AM slot should not be in available slots
    slot_times = [slot.start_time for slot in result.slots]
    assert datetime(2025, 10, 20, 10, 0) not in slot_times

    # 9 AM and 11 AM should be available
    assert datetime(2025, 10, 20, 9, 0) in slot_times
    assert datetime(2025, 10, 20, 11, 0) in slot_times


@pytest.mark.asyncio
async def test_calculate_available_slots_with_30min_intervals(
    slot_service, sample_service, sample_availability
):
    """Test slot calculation with 30-minute intervals."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)
    slot_service.availability_repo.list_active_by_professional_and_day = AsyncMock(
        return_value=[sample_availability]
    )
    slot_service.booking_repo.list_by_professional_and_date = AsyncMock(
        return_value=[]
    )

    target_date = date(2025, 10, 20)

    result = await slot_service.calculate_available_slots(
        professional_id=1,
        target_date=target_date,
        service_id=1,
        slot_interval_minutes=30,  # 30-minute intervals
    )

    # With 30-min intervals and 60-min service, from 9 AM to 5 PM:
    # 9:00, 9:30, 10:00, 10:30, ..., 16:00, 16:30 (but 16:30 + 60min = 17:30 > 17:00)
    # So last slot starts at 16:00
    assert len(result.slots) == 15  # (17:00 - 9:00) * 2 - 1 = 15


@pytest.mark.asyncio
async def test_check_slot_availability_available(
    slot_service, sample_service, sample_availability
):
    """Test checking availability for a specific slot that is available."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)
    slot_service.booking_repo.check_conflict = AsyncMock(return_value=False)
    slot_service.availability_repo.list_active_by_professional_and_day = AsyncMock(
        return_value=[sample_availability]
    )

    scheduled_at = datetime(2025, 10, 20, 10, 0)

    is_available = await slot_service.check_slot_availability(
        professional_id=1,
        scheduled_at=scheduled_at,
        service_id=1,
    )

    assert is_available is True


@pytest.mark.asyncio
async def test_check_slot_availability_has_conflict(
    slot_service, sample_service, sample_availability
):
    """Test checking availability for a slot that has a conflict."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)
    slot_service.booking_repo.check_conflict = AsyncMock(return_value=True)

    scheduled_at = datetime(2025, 10, 20, 10, 0)

    is_available = await slot_service.check_slot_availability(
        professional_id=1,
        scheduled_at=scheduled_at,
        service_id=1,
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_check_slot_availability_outside_availability(
    slot_service, sample_service, sample_availability
):
    """Test checking availability for a slot outside professional's working hours."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)
    slot_service.booking_repo.check_conflict = AsyncMock(return_value=False)
    slot_service.availability_repo.list_active_by_professional_and_day = AsyncMock(
        return_value=[sample_availability]
    )

    # Try to book at 6 AM (before 9 AM availability start)
    scheduled_at = datetime(2025, 10, 20, 6, 0)

    is_available = await slot_service.check_slot_availability(
        professional_id=1,
        scheduled_at=scheduled_at,
        service_id=1,
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_get_next_available_slot_found(
    slot_service, sample_service, sample_availability
):
    """Test finding the next available slot."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)

    # First call returns slots
    async def mock_calculate_slots(professional_id, target_date, service_id):
        from backend.app.domain.scheduling.schemas import SlotResponse, TimeSlot

        slots = [
            TimeSlot(
                start_time=datetime.combine(target_date, time(9, 0)),
                end_time=datetime.combine(target_date, time(10, 0)),
                available=True,
            )
        ]
        return SlotResponse(
            professional_id=professional_id,
            date=target_date.isoformat(),
            service_id=service_id,
            service_duration_minutes=60,
            slots=slots,
            total_slots=1,
        )

    slot_service.calculate_available_slots = AsyncMock(
        side_effect=mock_calculate_slots
    )

    from_date = date(2025, 10, 20)

    next_slot = await slot_service.get_next_available_slot(
        professional_id=1,
        service_id=1,
        from_date=from_date,
    )

    assert next_slot is not None
    assert next_slot.start_time == datetime(2025, 10, 20, 9, 0)
    assert next_slot.end_time == datetime(2025, 10, 20, 10, 0)


@pytest.mark.asyncio
async def test_get_next_available_slot_not_found(slot_service, sample_service):
    """Test when no available slots are found within search window."""
    # Mock repositories
    slot_service.service_repo.get_by_id = AsyncMock(return_value=sample_service)

    # Always return empty slots
    async def mock_calculate_slots(professional_id, target_date, service_id):
        from backend.app.domain.scheduling.schemas import SlotResponse

        return SlotResponse(
            professional_id=professional_id,
            date=target_date.isoformat(),
            service_id=service_id,
            service_duration_minutes=60,
            slots=[],
            total_slots=0,
        )

    slot_service.calculate_available_slots = AsyncMock(
        side_effect=mock_calculate_slots
    )

    from_date = date(2025, 10, 20)

    next_slot = await slot_service.get_next_available_slot(
        professional_id=1,
        service_id=1,
        from_date=from_date,
        max_days_ahead=5,  # Search only 5 days
    )

    assert next_slot is None


@pytest.mark.asyncio
async def test_generate_slots_respects_service_duration(
    slot_service, sample_availability
):
    """Test that slots are generated respecting service duration."""
    target_date = date(2025, 10, 20)
    service_duration = 90  # 90 minutes

    slots = slot_service._generate_slots_from_availabilities(
        availabilities=[sample_availability],
        target_date=target_date,
        service_duration=service_duration,
        slot_interval=30,
    )

    # Each slot should be 90 minutes long
    for slot in slots:
        duration = (slot.end_time - slot.start_time).total_seconds() / 60
        assert duration == 90

    # Last slot should not exceed availability end time
    assert slots[-1].end_time <= datetime(2025, 10, 20, 17, 0)


@pytest.mark.asyncio
async def test_filter_conflicting_slots_overlap_scenarios(slot_service):
    """Test different overlap scenarios for conflict detection."""
    from backend.app.domain.scheduling.schemas import TimeSlot

    service = MagicMock(spec=Service)
    service.duration_minutes = 60

    # Create test slots
    slots = [
        TimeSlot(
            start_time=datetime(2025, 10, 20, 9, 0),
            end_time=datetime(2025, 10, 20, 10, 0),
            available=True,
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 20, 10, 0),
            end_time=datetime(2025, 10, 20, 11, 0),
            available=True,
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 20, 11, 0),
            end_time=datetime(2025, 10, 20, 12, 0),
            available=True,
        ),
    ]

    # Create booking that conflicts with 10 AM slot
    booking = MagicMock(spec=Booking)
    booking.scheduled_at = datetime(2025, 10, 20, 10, 0)

    available = slot_service._filter_conflicting_slots(
        slots=slots,
        bookings=[booking],
        service=service,
    )

    # Only 9 AM and 11 AM slots should be available
    assert len(available) == 2
    assert available[0].start_time == datetime(2025, 10, 20, 9, 0)
    assert available[1].start_time == datetime(2025, 10, 20, 11, 0)
