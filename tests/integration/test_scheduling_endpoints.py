"""Integration tests for scheduling endpoints."""

from datetime import time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.availability import Availability, DayOfWeek
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole


@pytest.mark.asyncio
async def test_get_available_slots_success(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test getting available slots with valid data."""
    # Create test data
    # 1. Create salon owner
    owner = User(
        email="owner@test.com",
        password_hash="hashed",
        full_name="Test Owner",
        role=UserRole.SALON_OWNER,
    )
    db_session.add(owner)
    await db_session.flush()

    # 2. Create salon
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

    # 3. Create professional user
    prof_user = User(
        email="professional@test.com",
        password_hash="hashed",
        full_name="Test Professional",
        role=UserRole.PROFESSIONAL,
    )
    db_session.add(prof_user)
    await db_session.flush()

    # 4. Create professional
    professional = Professional(
        user_id=prof_user.id,
        salon_id=salon.id,
        specialties="Haircut, Color",
    )
    db_session.add(professional)
    await db_session.flush()

    # 5. Create service
    service = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Basic haircut",
        duration_minutes=60,
        price=50.0,
    )
    db_session.add(service)
    await db_session.flush()

    # 6. Create availability (Monday 9 AM to 5 PM)
    availability = Availability(
        professional_id=professional.id,
        day_of_week=DayOfWeek.MONDAY,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    db_session.add(availability)
    await db_session.commit()

    # Test the endpoint
    test_date = "2025-10-20"  # Monday

    response = await client.get(
        "/v1/scheduling/slots",
        params={
            "professional_id": professional.id,
            "date": test_date,
            "service_id": service.id,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["professional_id"] == professional.id
    assert data["service_id"] == service.id
    assert data["date"] == test_date
    assert data["service_duration_minutes"] == 60
    assert len(data["slots"]) > 0
    assert data["total_slots"] == len(data["slots"])

    # Check first slot structure
    first_slot = data["slots"][0]
    assert "start_time" in first_slot
    assert "end_time" in first_slot
    assert "available" in first_slot
    assert first_slot["available"] is True


@pytest.mark.asyncio
async def test_get_available_slots_service_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test getting slots with non-existent service."""
    response = await client.get(
        "/v1/scheduling/slots",
        params={
            "professional_id": 1,
            "date": "2025-10-20",
            "service_id": 99999,  # Non-existent service
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_available_slots_no_availability(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test getting slots when professional has no availability."""
    # Create minimal data without availability
    owner = User(
        email="owner2@test.com",
        password_hash="hashed",
        full_name="Test Owner",
        role=UserRole.SALON_OWNER,
    )
    db_session.add(owner)
    await db_session.flush()

    salon = Salon(
        owner_id=owner.id,
        name="Test Salon 2",
        cnpj="23.456.789/0001-91",
        phone="555-0200",
        address_street="Test Street",
        address_number="456",
        address_neighborhood="Test Neighborhood",
        address_city="Test City",
        address_state="RJ",
        address_zipcode="23456-789",
    )
    db_session.add(salon)
    await db_session.flush()

    prof_user = User(
        email="professional2@test.com",
        password_hash="hashed",
        full_name="Test Professional 2",
        role=UserRole.PROFESSIONAL,
    )
    db_session.add(prof_user)
    await db_session.flush()

    professional = Professional(
        user_id=prof_user.id,
        salon_id=salon.id,
    )
    db_session.add(professional)
    await db_session.flush()

    service = Service(
        salon_id=salon.id,
        name="Service 2",
        description="Test",
        duration_minutes=30,
        price=25.0,
    )
    db_session.add(service)
    await db_session.commit()

    # No availability created - should return empty slots
    response = await client.get(
        "/v1/scheduling/slots",
        params={
            "professional_id": professional.id,
            "date": "2025-10-20",
            "service_id": service.id,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["slots"] == []
    assert data["total_slots"] == 0


@pytest.mark.asyncio
async def test_get_available_slots_invalid_parameters(client: AsyncClient):
    """Test validation errors with invalid parameters."""
    # Test with negative professional_id
    response = await client.get(
        "/v1/scheduling/slots",
        params={
            "professional_id": -1,
            "date": "2025-10-20",
            "service_id": 1,
        },
    )
    assert response.status_code == 422

    # Test with invalid date format
    response = await client.get(
        "/v1/scheduling/slots",
        params={
            "professional_id": 1,
            "date": "invalid-date",
            "service_id": 1,
        },
    )
    assert response.status_code == 422

    # Test with missing required parameter
    response = await client.get(
        "/v1/scheduling/slots",
        params={
            "professional_id": 1,
            "date": "2025-10-20",
            # Missing service_id
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_available_slots_custom_interval(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test getting slots with custom interval."""
    # Create test data
    owner = User(
        email="owner3@test.com",
        password_hash="hashed",
        full_name="Test Owner",
        role=UserRole.SALON_OWNER,
    )
    db_session.add(owner)
    await db_session.flush()

    salon = Salon(
        owner_id=owner.id,
        name="Test Salon 3",
        cnpj="34.567.890/0001-92",
        phone="555-0300",
        address_street="Test Street",
        address_number="789",
        address_neighborhood="Test Neighborhood",
        address_city="Test City",
        address_state="MG",
        address_zipcode="34567-890",
    )
    db_session.add(salon)
    await db_session.flush()

    prof_user = User(
        email="professional3@test.com",
        password_hash="hashed",
        full_name="Test Professional 3",
        role=UserRole.PROFESSIONAL,
    )
    db_session.add(prof_user)
    await db_session.flush()

    professional = Professional(
        user_id=prof_user.id,
        salon_id=salon.id,
    )
    db_session.add(professional)
    await db_session.flush()

    service = Service(
        salon_id=salon.id,
        name="Service 3",
        description="Test",
        duration_minutes=60,
        price=50.0,
    )
    db_session.add(service)
    await db_session.flush()

    # Availability 9 AM to 12 PM (3 hours)
    availability = Availability(
        professional_id=professional.id,
        day_of_week=DayOfWeek.MONDAY,
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    db_session.add(availability)
    await db_session.commit()

    # Test with 60-minute intervals
    response = await client.get(
        "/v1/scheduling/slots",
        params={
            "professional_id": professional.id,
            "date": "2025-10-20",  # Monday
            "service_id": service.id,
            "slot_interval_minutes": 60,
        },
    )

    assert response.status_code == 200

    data = response.json()
    # 9:00, 10:00, 11:00 (3 slots with 60-min service and 60-min interval)
    assert data["total_slots"] == 3
