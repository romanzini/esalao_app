"""Integration tests for service endpoints."""

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.salon import Salon
from backend.app.db.models.user import User


@pytest.fixture
async def test_service_data(db_session: AsyncSession):
    """Create test data for service tests."""
    # Create owner user
    owner = User(
        email="owner@example.com",
        full_name="Owner User",
        phone="11999999999",
        password_hash="hashed",
        role="admin",
    )
    db_session.add(owner)
    await db_session.flush()

    # Create salon
    salon = Salon(
        name="Test Salon",
        cnpj="12345678000100",
        phone="11888888888",
        owner_id=owner.id,
        address_street="Test Street",
        address_number="123",
        address_neighborhood="Test Neighborhood",
        address_city="Test City",
        address_state="SP",
        address_zipcode="12345678",
    )
    db_session.add(salon)
    await db_session.flush()
    await db_session.commit()

    return {"owner": owner, "salon": salon}


# ==================== CREATE TESTS ====================


@pytest.mark.asyncio
async def test_create_service_success(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test successful service creation by admin."""
    # Make user admin
    auth_user.role = "admin"
    await db_session.commit()

    salon = test_service_data["salon"]

    response = await authenticated_client.post(
        "/v1/services",
        json={
            "salon_id": salon.id,
            "name": "Haircut",
            "description": "Professional haircut with wash and styling",
            "duration_minutes": 60,
            "price": "100.00",
            "category": "Hair",
            "requires_deposit": False,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Haircut"
    assert data["salon_id"] == salon.id
    assert data["duration_minutes"] == 60
    assert Decimal(data["price"]) == Decimal("100.00")
    assert data["category"] == "Hair"
    assert data["is_active"] is True
    assert data["requires_deposit"] is False


@pytest.mark.asyncio
async def test_create_service_with_deposit(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test service creation with deposit requirement."""
    auth_user.role = "admin"
    await db_session.commit()

    salon = test_service_data["salon"]

    response = await authenticated_client.post(
        "/v1/services",
        json={
            "salon_id": salon.id,
            "name": "Massage",
            "description": "Full body massage",
            "duration_minutes": 90,
            "price": "200.00",
            "category": "Body",
            "requires_deposit": True,
            "deposit_percentage": "50.0",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["requires_deposit"] is True
    assert Decimal(data["deposit_percentage"]) == Decimal("50.0")


@pytest.mark.asyncio
async def test_create_service_salon_not_found(
    authenticated_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
):
    """Test service creation with non-existent salon."""
    auth_user.role = "admin"
    await db_session.commit()

    response = await authenticated_client.post(
        "/v1/services",
        json={
            "salon_id": 99999,
            "name": "Haircut",
            "description": "Test",
            "duration_minutes": 60,
            "price": "100.00",
        },
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_service_invalid_deposit_logic(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test service creation with deposit_percentage but requires_deposit=False."""
    auth_user.role = "admin"
    await db_session.commit()

    salon = test_service_data["salon"]

    response = await authenticated_client.post(
        "/v1/services",
        json={
            "salon_id": salon.id,
            "name": "Haircut",
            "description": "Test",
            "duration_minutes": 60,
            "price": "100.00",
            "requires_deposit": False,
            "deposit_percentage": "50.0",
        },
    )

    assert response.status_code == 400
    assert "requires_deposit" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_service_forbidden_client(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test that clients cannot create services."""
    # auth_user is client by default
    salon = test_service_data["salon"]

    response = await authenticated_client.post(
        "/v1/services",
        json={
            "salon_id": salon.id,
            "name": "Haircut",
            "description": "Test",
            "duration_minutes": 60,
            "price": "100.00",
        },
    )

    assert response.status_code == 403


# ==================== LIST TESTS ====================


@pytest.mark.asyncio
async def test_list_services(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test listing services by salon."""
    from backend.app.db.models.service import Service

    salon = test_service_data["salon"]

    # Create test services
    service1 = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Test",
        duration_minutes=60,
        price=100.00,
        category="Hair",
    )
    service2 = Service(
        salon_id=salon.id,
        name="Manicure",
        description="Test",
        duration_minutes=45,
        price=50.00,
        category="Nails",
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    response = await authenticated_client.get(
        "/v1/services",
        params={"salon_id": salon.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["services"]) == 2


@pytest.mark.asyncio
async def test_list_services_by_category(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test listing services filtered by category."""
    from backend.app.db.models.service import Service

    salon = test_service_data["salon"]

    # Create test services
    service1 = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Test",
        duration_minutes=60,
        price=100.00,
        category="Hair",
    )
    service2 = Service(
        salon_id=salon.id,
        name="Manicure",
        description="Test",
        duration_minutes=45,
        price=50.00,
        category="Nails",
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    response = await authenticated_client.get(
        "/v1/services",
        params={"salon_id": salon.id, "category": "Hair"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["services"][0]["category"] == "Hair"


@pytest.mark.asyncio
async def test_list_services_filter_active(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test listing services filtered by is_active."""
    from backend.app.db.models.service import Service

    salon = test_service_data["salon"]

    # Create test services
    service1 = Service(
        salon_id=salon.id,
        name="Active Service",
        description="Test",
        duration_minutes=60,
        price=100.00,
        is_active=True,
    )
    service2 = Service(
        salon_id=salon.id,
        name="Inactive Service",
        description="Test",
        duration_minutes=45,
        price=50.00,
        is_active=False,
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    response = await authenticated_client.get(
        "/v1/services",
        params={"salon_id": salon.id, "is_active": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["services"][0]["is_active"] is True


# ==================== GET BY ID TESTS ====================


@pytest.mark.asyncio
async def test_get_service_by_id(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test getting a service by ID."""
    from backend.app.db.models.service import Service

    salon = test_service_data["salon"]

    service = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Professional haircut",
        duration_minutes=60,
        price=100.00,
        category="Hair",
    )
    db_session.add(service)
    await db_session.commit()

    response = await authenticated_client.get(f"/v1/services/{service.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == service.id
    assert data["name"] == "Haircut"


@pytest.mark.asyncio
async def test_get_service_not_found(
    authenticated_client: AsyncClient,
    auth_user: User,
):
    """Test getting a non-existent service."""
    response = await authenticated_client.get("/v1/services/99999")

    assert response.status_code == 404


# ==================== UPDATE TESTS ====================


@pytest.mark.asyncio
async def test_update_service_by_admin(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test updating a service by admin."""
    from backend.app.db.models.service import Service

    auth_user.role = "admin"
    await db_session.commit()

    salon = test_service_data["salon"]

    service = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Old description",
        duration_minutes=60,
        price=100.00,
        category="Hair",
    )
    db_session.add(service)
    await db_session.commit()

    response = await authenticated_client.patch(
        f"/v1/services/{service.id}",
        json={
            "name": "Premium Haircut",
            "description": "New description",
            "price": "150.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Premium Haircut"
    assert data["description"] == "New description"
    assert Decimal(data["price"]) == Decimal("150.00")


@pytest.mark.asyncio
async def test_update_service_not_found(
    authenticated_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
):
    """Test updating a non-existent service."""
    auth_user.role = "admin"
    await db_session.commit()

    response = await authenticated_client.patch(
        "/v1/services/99999",
        json={"name": "New Name"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_service_forbidden_client(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test that clients cannot update services."""
    from backend.app.db.models.service import Service

    salon = test_service_data["salon"]

    service = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Test",
        duration_minutes=60,
        price=100.00,
    )
    db_session.add(service)
    await db_session.commit()

    response = await authenticated_client.patch(
        f"/v1/services/{service.id}",
        json={"name": "New Name"},
    )

    assert response.status_code == 403


# ==================== DELETE TESTS ====================


@pytest.mark.asyncio
async def test_deactivate_service(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test deactivating a service."""
    from backend.app.db.models.service import Service

    auth_user.role = "admin"
    await db_session.commit()

    salon = test_service_data["salon"]

    service = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Test",
        duration_minutes=60,
        price=100.00,
    )
    db_session.add(service)
    await db_session.commit()

    service_id = service.id
    response = await authenticated_client.delete(f"/v1/services/{service_id}")

    assert response.status_code == 204

    # Verify service is deactivated - fetch fresh from DB
    from backend.app.db.repositories.service import ServiceRepository
    service_repo = ServiceRepository(db_session)
    updated_service = await service_repo.get_by_id(service_id)
    assert updated_service is not None
    assert updated_service.is_active is False


@pytest.mark.asyncio
async def test_deactivate_service_not_found(
    authenticated_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
):
    """Test deactivating a non-existent service."""
    auth_user.role = "admin"
    await db_session.commit()

    response = await authenticated_client.delete("/v1/services/99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_service_forbidden_client(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_service_data: dict,
    db_session: AsyncSession,
):
    """Test that clients cannot deactivate services."""
    from backend.app.db.models.service import Service

    salon = test_service_data["salon"]

    service = Service(
        salon_id=salon.id,
        name="Haircut",
        description="Test",
        duration_minutes=60,
        price=100.00,
    )
    db_session.add(service)
    await db_session.commit()

    response = await authenticated_client.delete(f"/v1/services/{service.id}")

    assert response.status_code == 403
