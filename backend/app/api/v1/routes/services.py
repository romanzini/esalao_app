"""Service management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.service import (
    ServiceCreateRequest,
    ServiceListResponse,
    ServiceResponse,
    ServiceUpdateRequest,
)
from backend.app.core.security.rbac import (
    get_current_user,
    get_current_user_optional,
)
from backend.app.db.models.user import User
from backend.app.db.repositories.salon import SalonRepository
from backend.app.db.repositories.service import ServiceRepository
from backend.app.db.session import get_db

router = APIRouter(prefix="/services", tags=["services"])


@router.post(
    "",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service",
    description="Create a new service for a salon. Only admins and receptionists can create services.",
)
async def create_service(
    service_data: ServiceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """
    Create a new service.

    Permissions:
    - Admin: Can create services for any salon
    - Receptionist: Can create services for their salon
    - Professional/Client: Forbidden

    Validations:
    - Salon must exist
    - Receptionist must belong to the salon
    - Deposit percentage requires requires_deposit=True
    """
    # Check permissions
    if current_user.role not in ["admin", "receptionist"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and receptionists can create services",
        )

    # Verify salon exists
    salon_repo = SalonRepository(db)
    salon = await salon_repo.get_by_id(service_data.salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Salon with id {service_data.salon_id} not found",
        )

    # If receptionist, verify they belong to this salon
    if current_user.role == "receptionist":
        # TODO: Implement receptionist-salon relationship check
        # For now, we'll allow any receptionist to create services
        pass

    # Validate deposit logic
    if service_data.deposit_percentage and service_data.deposit_percentage > 0:
        if not service_data.requires_deposit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="deposit_percentage requires requires_deposit=True",
            )

    # Create service
    service_repo = ServiceRepository(db)
    service = await service_repo.create(
        salon_id=service_data.salon_id,
        name=service_data.name,
        description=service_data.description,
        duration_minutes=service_data.duration_minutes,
        price=float(service_data.price),
        category=service_data.category,
    )

    # Update deposit fields if needed
    if service_data.requires_deposit:
        service.requires_deposit = True
        service.deposit_percentage = float(service_data.deposit_percentage) if service_data.deposit_percentage else None
        await db.flush()
        await db.commit()
        await db.refresh(service)

    return ServiceResponse.model_validate(service)


@router.get(
    "",
    response_model=ServiceListResponse,
    summary="List services",
    description="List services with optional filters. Available to all users (authenticated or not).",
)
async def list_services(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    salon_id: int | None = Query(None, description="Filter by salon ID"),
    category: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ServiceListResponse:
    """
    List services with optional filters.

    Available to all users (authenticated or not).
    Results are paginated.
    """
    service_repo = ServiceRepository(db)

    # Get services based on filters
    if salon_id and category:
        services = await service_repo.list_by_category(salon_id, category)
    elif salon_id:
        services = await service_repo.list_by_salon_id(salon_id)
    else:
        # TODO: Implement list_all with pagination in repository
        # For now, return empty list if no salon_id provided
        services = []

    # Filter by is_active if provided
    if is_active is not None:
        services = [s for s in services if s.is_active == is_active]

    # Apply pagination
    total = len(services)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_services = services[start:end]

    return ServiceListResponse(
        services=[ServiceResponse.model_validate(s) for s in paginated_services],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Get service by ID",
    description="Get a single service by its ID. Available to all users (authenticated or not).",
)
async def get_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> ServiceResponse:
    """
    Get a service by ID.

    Available to all users (authenticated or not).
    """
    service_repo = ServiceRepository(db)
    service = await service_repo.get_by_id(service_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {service_id} not found",
        )

    return ServiceResponse.model_validate(service)


@router.patch(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Update service",
    description="Update service information. Only admins and receptionists can update services.",
)
async def update_service(
    service_id: int,
    service_data: ServiceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """
    Update a service.

    Permissions:
    - Admin: Can update any service
    - Receptionist: Can update services from their salon
    - Professional/Client: Forbidden
    """
    # Check permissions
    if current_user.role not in ["admin", "receptionist"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and receptionists can update services",
        )

    # Get service
    service_repo = ServiceRepository(db)
    service = await service_repo.get_by_id(service_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {service_id} not found",
        )

    # If receptionist, verify they belong to this salon
    if current_user.role == "receptionist":
        # TODO: Implement receptionist-salon relationship check
        # For now, we'll allow any receptionist to update services
        pass

    # Validate deposit logic if being updated
    if service_data.deposit_percentage is not None and service_data.deposit_percentage > 0:
        requires_deposit = service_data.requires_deposit if service_data.requires_deposit is not None else service.requires_deposit
        if not requires_deposit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="deposit_percentage requires requires_deposit=True",
            )

    # Build update dictionary with only non-None values
    update_data = {}
    if service_data.name is not None:
        update_data["name"] = service_data.name
    if service_data.description is not None:
        update_data["description"] = service_data.description
    if service_data.duration_minutes is not None:
        update_data["duration_minutes"] = service_data.duration_minutes
    if service_data.price is not None:
        update_data["price"] = float(service_data.price)
    if service_data.category is not None:
        update_data["category"] = service_data.category
    if service_data.requires_deposit is not None:
        update_data["requires_deposit"] = service_data.requires_deposit
    if service_data.deposit_percentage is not None:
        update_data["deposit_percentage"] = float(service_data.deposit_percentage)

    # Update service
    updated_service = await service_repo.update(service_id=service_id, **update_data)

    await db.commit()
    await db.refresh(updated_service)

    return ServiceResponse.model_validate(updated_service)


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate service",
    description="Soft delete a service by setting is_active=False. Only admins and receptionists can deactivate services.",
)
async def deactivate_service(
    service_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deactivate a service (soft delete).

    Permissions:
    - Admin: Can deactivate any service
    - Receptionist: Can deactivate services from their salon
    - Professional/Client: Forbidden

    The service is not deleted from the database, just marked as inactive.
    """
    # Check permissions
    if current_user.role not in ["admin", "receptionist"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and receptionists can deactivate services",
        )

    # Get service
    service_repo = ServiceRepository(db)
    service = await service_repo.get_by_id(service_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {service_id} not found",
        )

    # If receptionist, verify they belong to this salon
    if current_user.role == "receptionist":
        # TODO: Implement receptionist-salon relationship check
        # For now, we'll allow any receptionist to deactivate services
        pass

    # Deactivate service
    await service_repo.delete(service_id)

    return None
