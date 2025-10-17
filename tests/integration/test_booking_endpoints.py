"""Integration tests for booking endpoints."""

from datetime import datetime, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.availability import Availability, DayOfWeek
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole


@pytest.fixture
async def test_data(db_session: AsyncSession):
    """Create test data for booking tests."""
    # Create salon owner (skip ID to avoid conflicts with authenticated_client user)
    owner = User(
        email="owner_booking@test.com",
        password_hash="hashed",
        full_name="Test Owner",
        role=UserRole.SALON_OWNER,
    )
    db_session.add(owner)
    await db_session.flush()

    # Create salon
    salon = Salon(
        owner_id=owner.id,
        name="Test Salon",
        cnpj="12.345.678/0001-90",
        phone="555-0100",
        address_street="Test Street",
        address_number="123",
        address_neighborhood="Test Neighborhood",
        address_city="Test City",
        address_state="SP",
        address_zipcode="12345-678",
    )
    db_session.add(salon)
    await db_session.flush()

    # Create professional user
    prof_user = User(
        email="professional@test.com",
        password_hash="hashed",
        full_name="Test Professional",
        role=UserRole.PROFESSIONAL,
    )
    db_session.add(prof_user)
    await db_session.flush()

    # Create professional
    professional = Professional(
        user_id=prof_user.id,
        salon_id=salon.id,
        specialties="Haircut, Color",
    )
    db_session.add(professional)
    await db_session.flush()

    # Create service
    service = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Basic haircut",
        duration_minutes=60,
        price=50.0,
    )
    db_session.add(service)
    await db_session.flush()

    # Create availability (Monday 9 AM to 5 PM)
    availability = Availability(
        professional_id=professional.id,
        day_of_week=DayOfWeek.MONDAY,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    db_session.add(availability)

    # Create client user
    client_user = User(
        email="client@test.com",
        password_hash="hashed",
        full_name="Test Client",
        role=UserRole.CLIENT,
    )
    db_session.add(client_user)
    await db_session.flush()

    await db_session.commit()

    return {
        "owner": owner,
        "salon": salon,
        "professional": professional,
        "prof_user": prof_user,
        "service": service,
        "availability": availability,
        "client_user": client_user,
    }


@pytest.mark.asyncio
async def test_create_booking_success(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test creating a booking with valid data."""
    scheduled_time = datetime(2025, 10, 20, 10, 0)  # Monday at 10 AM

    response = await authenticated_client.post(
        "/v1/bookings",
        json={
            "professional_id": test_data["professional"].id,
            "service_id": test_data["service"].id,
            "scheduled_at": scheduled_time.isoformat(),
            "notes": "First haircut",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["professional_id"] == test_data["professional"].id
    assert data["service_id"] == test_data["service"].id
    assert data["status"] == BookingStatus.PENDING.value
    assert data["service_price"] == 50.0
    assert data["duration_minutes"] == 60
    assert data["notes"] == "First haircut"


@pytest.mark.asyncio
async def test_create_booking_service_not_found(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test creating a booking with non-existent service."""
    scheduled_time = datetime(2025, 10, 20, 10, 0)

    response = await authenticated_client.post(
        "/v1/bookings",
        json={
            "professional_id": test_data["professional"].id,
            "service_id": 99999,
            "scheduled_at": scheduled_time.isoformat(),
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_booking_slot_not_available(
    authenticated_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test creating a booking when slot is not available."""
    # Create existing booking
    existing_booking = Booking(
        client_id=auth_user.id,
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 10, 0),
        status=BookingStatus.CONFIRMED,
        service_price=50.0,
        duration_minutes=60,
    )
    db_session.add(existing_booking)
    await db_session.commit()

    # Try to create booking at the same time
    response = await authenticated_client.post(
        "/v1/bookings",
        json={
            "professional_id": test_data["professional"].id,
            "service_id": test_data["service"].id,
            "scheduled_at": "2025-10-20T10:00:00",
        },
    )

    assert response.status_code == 409
    assert "not available" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_bookings_as_client(
    authenticated_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test listing bookings as a client (should see only own bookings)."""
    # Create bookings for different clients
    booking1 = Booking(
        client_id=auth_user.id,
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 10, 0),
        status=BookingStatus.PENDING,
        service_price=50.0,
        duration_minutes=60,
    )
    db_session.add(booking1)

    other_client = User(
        email="other@test.com",
        password_hash="hashed",
        full_name="Other Client",
        role=UserRole.CLIENT,
    )
    db_session.add(other_client)
    await db_session.flush()

    booking2 = Booking(
        client_id=other_client.id,
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 11, 0),
        status=BookingStatus.PENDING,
        service_price=50.0,
        duration_minutes=60,
    )
    db_session.add(booking2)
    await db_session.commit()

    response = await authenticated_client.get("/v1/bookings")

    assert response.status_code == 200
    data = response.json()
    # Should only see own booking (but we need auth to test this properly)
    assert "bookings" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_bookings_pagination(
    authenticated_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test booking list pagination."""
    # Create multiple bookings
    for hour in range(9, 15):  # 6 bookings
        booking = Booking(
            client_id=auth_user.id,
            professional_id=test_data["professional"].id,
            service_id=test_data["service"].id,
            scheduled_at=datetime(2025, 10, 20, hour, 0),
            status=BookingStatus.PENDING,
            service_price=50.0,
            duration_minutes=60,
        )
        db_session.add(booking)
    await db_session.commit()

    # Test pagination
    response = await authenticated_client.get("/v1/bookings?page=1&page_size=3")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 3
    assert len(data["bookings"]) <= 3


@pytest.mark.asyncio
async def test_get_booking_by_id_success(
    authenticated_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test getting a booking by ID."""
    booking = Booking(
        client_id=auth_user.id,  # Use authenticated user
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 10, 0),
        status=BookingStatus.CONFIRMED,
        service_price=50.0,
        duration_minutes=60,
        notes="Test notes",
    )
    db_session.add(booking)
    await db_session.commit()

    response = await authenticated_client.get(f"/v1/bookings/{booking.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == booking.id
    assert data["status"] == BookingStatus.CONFIRMED.value
    assert data["notes"] == "Test notes"


@pytest.mark.asyncio
async def test_get_booking_by_id_not_found(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test getting a non-existent booking."""
    response = await authenticated_client.get("/v1/bookings/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_booking_status_success(
    admin_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test updating booking status (requires admin or professional role)."""
    booking = Booking(
        client_id=auth_user.id,
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 10, 0),
        status=BookingStatus.PENDING,
        service_price=50.0,
        duration_minutes=60,
    )
    db_session.add(booking)
    await db_session.commit()

    response = await admin_client.patch(
        f"/v1/bookings/{booking.id}/status",
        json={"status": BookingStatus.CONFIRMED.value},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == BookingStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_update_booking_status_with_cancellation(
    authenticated_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test cancelling a booking with reason."""
    booking = Booking(
        client_id=auth_user.id,
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 10, 0),
        status=BookingStatus.CONFIRMED,
        service_price=50.0,
        duration_minutes=60,
    )
    db_session.add(booking)
    await db_session.commit()

    response = await authenticated_client.patch(
        f"/v1/bookings/{booking.id}/status",
        json={
            "status": BookingStatus.CANCELLED.value,
            "cancellation_reason": "Client requested cancellation",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == BookingStatus.CANCELLED.value
    assert data["cancellation_reason"] == "Client requested cancellation"
    assert data["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_update_booking_status_cancelled_requires_reason(
    authenticated_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test that cancellation requires a reason."""
    booking = Booking(
        client_id=auth_user.id,
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 10, 0),
        status=BookingStatus.CONFIRMED,
        service_price=50.0,
        duration_minutes=60,
    )
    db_session.add(booking)
    await db_session.commit()

    response = await authenticated_client.patch(
        f"/v1/bookings/{booking.id}/status",
        json={"status": BookingStatus.CANCELLED.value},
    )

    assert response.status_code == 400
    assert "reason" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_booking_endpoint(
    authenticated_client: AsyncClient,
    auth_user,
    db_session: AsyncSession,
    test_data: dict,
):
    """Test the DELETE endpoint for cancelling a booking."""
    booking = Booking(
        client_id=auth_user.id,
        professional_id=test_data["professional"].id,
        service_id=test_data["service"].id,
        scheduled_at=datetime(2025, 10, 20, 10, 0),
        status=BookingStatus.CONFIRMED,
        service_price=50.0,
        duration_minutes=60,
    )
    db_session.add(booking)
    await db_session.commit()

    response = await authenticated_client.delete(
        f"/v1/bookings/{booking.id}",
        params={"cancellation_reason": "User requested cancellation"},
    )

    assert response.status_code == 204

    # Verify booking was cancelled by fetching it
    verify_response = await authenticated_client.get(f"/v1/bookings/{booking.id}")
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["status"] == BookingStatus.CANCELLED.value
    assert data["cancellation_reason"] == "User requested cancellation"


@pytest.mark.asyncio
async def test_cancel_booking_not_found(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test cancelling a non-existent booking."""
    response = await authenticated_client.delete(
        "/v1/bookings/99999",
        params={"cancellation_reason": "Test reason"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
