"""Integration tests for professional endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.user import User


@pytest.fixture
async def test_professional_data(db_session: AsyncSession):
    """Create test data for professional tests."""
    from backend.app.db.models.salon import Salon
    from backend.app.db.models.user import User, UserRole

    # Create salon owner user
    owner = User(
        email="owner@test.com",
        full_name="Salon Owner",
        password_hash="hashed_password",
        role=UserRole.ADMIN,
    )
    db_session.add(owner)
    await db_session.flush()

    # Create salon
    salon = Salon(
        name="Test Salon",
        cnpj="12.345.678/0001-90",
        email="salon@test.com",
        phone="11999999999",
        address_street="Test Street",
        address_number="123",
        address_neighborhood="Test District",
        address_city="São Paulo",
        address_state="SP",
        address_zipcode="01234-567",
        owner_id=owner.id,
    )
    db_session.add(salon)
    await db_session.flush()

    # Create user for professional
    user = User(
        email="professional@test.com",
        full_name="John Professional",
        password_hash="hashed_password",
        role=UserRole.PROFESSIONAL,
    )
    db_session.add(user)
    await db_session.flush()

    await db_session.commit()

    return {
        "salon": salon,
        "user": user,
        "owner": owner,
    }


@pytest.mark.asyncio
async def test_create_professional_success(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test creating a professional successfully."""
    # Make auth_user an ADMIN
    auth_user.role = "admin"
    await db_session.commit()

    data = {
        "user_id": test_professional_data["user"].id,
        "salon_id": test_professional_data["salon"].id,
        "specialties": ["haircut", "coloring"],
        "bio": "Experienced stylist with 10 years",
        "license_number": "ABC-12345",
        "commission_percentage": 50.0,
    }

    response = await authenticated_client.post("/v1/professionals", json=data)

    assert response.status_code == 201
    result = response.json()
    assert result["user_id"] == data["user_id"]
    assert result["salon_id"] == data["salon_id"]
    assert result["specialties"] == data["specialties"]
    assert result["bio"] == data["bio"]
    assert result["license_number"] == data["license_number"]
    assert result["commission_percentage"] == data["commission_percentage"]
    assert result["is_active"] is True
    assert "id" in result
    assert "created_at" in result
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_create_professional_user_not_found(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test creating professional with non-existent user."""
    # Make auth_user an ADMIN
    auth_user.role = "admin"
    await db_session.commit()

    data = {
        "user_id": 99999,
        "salon_id": test_professional_data["salon"].id,
        "specialties": ["haircut"],
        "commission_percentage": 50.0,
    }

    response = await authenticated_client.post("/v1/professionals", json=data)

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_professional_salon_not_found(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test creating professional with non-existent salon."""
    # Make auth_user an ADMIN
    auth_user.role = "admin"
    await db_session.commit()

    data = {
        "user_id": test_professional_data["user"].id,
        "salon_id": 99999,
        "specialties": ["haircut"],
        "commission_percentage": 50.0,
    }

    response = await authenticated_client.post("/v1/professionals", json=data)

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_professional_duplicate_user(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test creating professional for user that already has a professional profile."""
    from backend.app.db.models.professional import Professional

    # Make auth_user an ADMIN
    auth_user.role = "admin"
    await db_session.commit()

    # Create existing professional
    existing = Professional(
        user_id=test_professional_data["user"].id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
    )
    db_session.add(existing)
    await db_session.commit()

    data = {
        "user_id": test_professional_data["user"].id,
        "salon_id": test_professional_data["salon"].id,
        "specialties": ["coloring"],
        "commission_percentage": 50.0,
    }

    response = await authenticated_client.post("/v1/professionals", json=data)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_professional_forbidden_client(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test that CLIENT role cannot create professionals."""
    # auth_user is CLIENT by default
    assert auth_user.role == "client"

    data = {
        "user_id": test_professional_data["user"].id,
        "salon_id": test_professional_data["salon"].id,
        "specialties": ["haircut"],
        "commission_percentage": 50.0,
    }

    response = await authenticated_client.post("/v1/professionals", json=data)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_professionals(
    authenticated_client: AsyncClient,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test listing professionals."""
    from backend.app.db.models.professional import Professional

    # Create professionals
    prof1 = Professional(
        user_id=test_professional_data["user"].id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
    )
    db_session.add(prof1)
    await db_session.commit()

    response = await authenticated_client.get(
        f"/v1/professionals?salon_id={test_professional_data['salon'].id}"
    )

    assert response.status_code == 200
    result = response.json()
    assert "professionals" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result
    assert len(result["professionals"]) >= 1
    assert result["professionals"][0]["salon_id"] == test_professional_data["salon"].id


@pytest.mark.asyncio
async def test_get_professional_by_id(
    authenticated_client: AsyncClient,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test getting professional by ID."""
    from backend.app.db.models.professional import Professional

    # Create professional
    professional = Professional(
        user_id=test_professional_data["user"].id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut", "coloring"],
        bio="Test bio",
        commission_percentage=55.0,
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(professional)
    await db_session.commit()

    response = await authenticated_client.get(f"/v1/professionals/{professional.id}")

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == professional.id
    assert result["user_id"] == professional.user_id
    assert result["salon_id"] == professional.salon_id
    assert result["specialties"] == professional.specialties
    assert result["bio"] == professional.bio
    assert result["commission_percentage"] == professional.commission_percentage


@pytest.mark.asyncio
async def test_get_professional_not_found(authenticated_client: AsyncClient):
    """Test getting non-existent professional."""
    response = await authenticated_client.get("/v1/professionals/99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_professional_by_admin(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test updating professional as ADMIN."""
    from backend.app.db.models.professional import Professional

    # Make auth_user an ADMIN
    auth_user.role = "admin"
    await db_session.commit()

    # Create professional
    professional = Professional(
        user_id=test_professional_data["user"].id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(professional)
    await db_session.commit()

    update_data = {
        "specialties": ["haircut", "coloring", "styling"],
        "bio": "Updated bio",
        "commission_percentage": 60.0,
    }

    response = await authenticated_client.patch(
        f"/v1/professionals/{professional.id}", json=update_data
    )

    assert response.status_code == 200
    result = response.json()
    assert result["specialties"] == update_data["specialties"]
    assert result["bio"] == update_data["bio"]
    assert result["commission_percentage"] == update_data["commission_percentage"]


@pytest.mark.asyncio
async def test_update_professional_own_profile(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test professional updating their own profile."""
    from backend.app.db.models.professional import Professional

    # Make auth_user a PROFESSIONAL
    auth_user.role = "professional"
    await db_session.commit()

    # Create professional for auth_user
    professional = Professional(
        user_id=auth_user.id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(professional)
    await db_session.commit()

    update_data = {
        "specialties": ["haircut", "coloring"],
        "bio": "My updated bio",
    }

    response = await authenticated_client.patch(
        f"/v1/professionals/{professional.id}", json=update_data
    )

    assert response.status_code == 200
    result = response.json()
    assert result["specialties"] == update_data["specialties"]
    assert result["bio"] == update_data["bio"]


@pytest.mark.asyncio
async def test_update_professional_forbidden_other_profile(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test professional cannot update other professional's profile."""
    from backend.app.db.models.professional import Professional

    # Make auth_user a PROFESSIONAL
    auth_user.role = "professional"
    await db_session.commit()

    # Create professional for different user
    professional = Professional(
        user_id=test_professional_data["user"].id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(professional)
    await db_session.commit()

    update_data = {"bio": "Trying to hack"}

    response = await authenticated_client.patch(
        f"/v1/professionals/{professional.id}", json=update_data
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_professional_commission_forbidden_for_professional(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test professional cannot change their own commission percentage."""
    from backend.app.db.models.professional import Professional

    # Make auth_user a PROFESSIONAL
    auth_user.role = "professional"
    await db_session.commit()

    # Create professional for auth_user
    professional = Professional(
        user_id=auth_user.id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(professional)
    await db_session.commit()

    update_data = {"commission_percentage": 90.0}

    response = await authenticated_client.patch(
        f"/v1/professionals/{professional.id}", json=update_data
    )

    assert response.status_code == 403
    assert "commission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_deactivate_professional(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test deactivating a professional."""
    from backend.app.db.models.professional import Professional

    # Make auth_user an ADMIN
    auth_user.role = "admin"
    await db_session.commit()

    # Create professional
    professional = Professional(
        user_id=test_professional_data["user"].id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
        is_active=True,
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(professional)
    await db_session.commit()

    response = await authenticated_client.delete(f"/v1/professionals/{professional.id}")

    assert response.status_code == 204

    # Verify professional is deactivated
    await db_session.refresh(professional)
    assert professional.is_active is False


@pytest.mark.asyncio
async def test_deactivate_professional_not_found(
    authenticated_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
):
    """Test deactivating non-existent professional."""
    # Make auth_user an ADMIN
    auth_user.role = "admin"
    await db_session.commit()

    response = await authenticated_client.delete("/v1/professionals/99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_professional_forbidden_client(
    authenticated_client: AsyncClient,
    auth_user: User,
    test_professional_data: dict,
    db_session: AsyncSession,
):
    """Test that CLIENT cannot deactivate professionals."""
    from backend.app.db.models.professional import Professional

    # auth_user is CLIENT by default
    assert auth_user.role == "client"

    # Create professional
    professional = Professional(
        user_id=test_professional_data["user"].id,
        salon_id=test_professional_data["salon"].id,
        specialties=["haircut"],
        commission_percentage=50.0,
    )
    db_session.add(professional)
    await db_session.flush()
    await db_session.refresh(professional)
    await db_session.commit()

    response = await authenticated_client.delete(f"/v1/professionals/{professional.id}")

    assert response.status_code == 403
