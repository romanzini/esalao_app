"""Professional management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.professional import (
    ProfessionalCreateRequest,
    ProfessionalListResponse,
    ProfessionalResponse,
    ProfessionalUpdateRequest,
)
from backend.app.core.security.rbac import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.db.repositories.professional import ProfessionalRepository
from backend.app.db.repositories.salon import SalonRepository
from backend.app.db.repositories.user import UserRepository

router = APIRouter(prefix="/professionals", tags=["professionals"])


@router.post(
    "",
    response_model=ProfessionalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new professional",
    description="Create a new professional profile linked to a user account and salon",
    responses={
        201: {
            "description": "Professional created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 2,
                        "salon_id": 1,
                        "specialties": ["haircut", "coloring"],
                        "bio": "Experienced stylist with 10 years",
                        "license_number": "ABC-12345",
                        "is_active": True,
                        "commission_percentage": 50.0,
                        "created_at": "2025-10-16T10:00:00Z",
                        "updated_at": "2025-10-16T10:00:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid input or user/salon not found"},
        403: {"description": "Not authorized to create professionals"},
        409: {"description": "Professional already exists for this user"},
    },
)
async def create_professional(
    data: ProfessionalCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfessionalResponse:
    """
    Create a new professional.

    Required permissions: ADMIN or RECEPTIONIST role.
    """
    # RBAC: Only ADMIN and RECEPTIONIST can create professionals
    if current_user.role not in ["ADMIN", "RECEPTIONIST"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and receptionists can create professionals",
        )

    user_repo = UserRepository(db)
    salon_repo = SalonRepository(db)
    prof_repo = ProfessionalRepository(db)

    # Validate user exists
    user = await user_repo.get_by_id(data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with ID {data.user_id} not found",
        )

    # Validate salon exists
    salon = await salon_repo.get_by_id(data.salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Salon with ID {data.salon_id} not found",
        )

    # Check if professional already exists for this user
    existing = await prof_repo.get_by_user_id(data.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Professional already exists for user ID {data.user_id}",
        )

    # Create professional
    professional = await prof_repo.create(
        user_id=data.user_id,
        salon_id=data.salon_id,
        specialties=data.specialties,
        bio=data.bio,
        license_number=data.license_number,
        commission_percentage=data.commission_percentage,
    )

    return ProfessionalResponse.model_validate(professional)


@router.get(
    "",
    response_model=ProfessionalListResponse,
    summary="List professionals",
    description="List professionals with optional filtering by salon",
    responses={
        200: {
            "description": "List of professionals",
            "content": {
                "application/json": {
                    "example": {
                        "professionals": [
                            {
                                "id": 1,
                                "user_id": 2,
                                "salon_id": 1,
                                "specialties": ["haircut"],
                                "bio": "Expert stylist",
                                "license_number": None,
                                "is_active": True,
                                "commission_percentage": 50.0,
                                "created_at": "2025-10-16T10:00:00Z",
                                "updated_at": "2025-10-16T10:00:00Z",
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 10,
                    }
                }
            },
        },
    },
)
async def list_professionals(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    salon_id: Annotated[int | None, Query(description="Filter by salon ID", ge=1)] = None,
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Items per page", ge=1, le=100)] = 10,
) -> ProfessionalListResponse:
    """
    List professionals with optional filtering.

    Available to all authenticated users.
    """
    prof_repo = ProfessionalRepository(db)

    if salon_id:
        # Filter by salon
        professionals = await prof_repo.list_by_salon_id(salon_id)
    else:
        # Get all professionals (implement pagination if needed)
        professionals = await prof_repo.list_by_salon_id(0)  # Placeholder

    # TODO: Implement proper pagination in repository
    total = len(professionals)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_professionals = professionals[start:end]

    return ProfessionalListResponse(
        professionals=[
            ProfessionalResponse.model_validate(p) for p in paginated_professionals
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{professional_id}",
    response_model=ProfessionalResponse,
    summary="Get professional by ID",
    description="Get detailed information about a specific professional",
    responses={
        200: {
            "description": "Professional details",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 2,
                        "salon_id": 1,
                        "specialties": ["haircut", "coloring"],
                        "bio": "Experienced stylist",
                        "license_number": "ABC-12345",
                        "is_active": True,
                        "commission_percentage": 50.0,
                        "created_at": "2025-10-16T10:00:00Z",
                        "updated_at": "2025-10-16T10:00:00Z",
                    }
                }
            },
        },
        404: {"description": "Professional not found"},
    },
)
async def get_professional(
    professional_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfessionalResponse:
    """
    Get professional by ID.

    Available to all authenticated users.
    """
    prof_repo = ProfessionalRepository(db)

    professional = await prof_repo.get_by_id(professional_id)
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Professional with ID {professional_id} not found",
        )

    return ProfessionalResponse.model_validate(professional)


@router.patch(
    "/{professional_id}",
    response_model=ProfessionalResponse,
    summary="Update professional",
    description="Update professional information (partial update)",
    responses={
        200: {
            "description": "Professional updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 2,
                        "salon_id": 1,
                        "specialties": ["haircut", "coloring", "styling"],
                        "bio": "Updated bio",
                        "license_number": "ABC-12345",
                        "is_active": True,
                        "commission_percentage": 55.0,
                        "created_at": "2025-10-16T10:00:00Z",
                        "updated_at": "2025-10-16T11:00:00Z",
                    }
                }
            },
        },
        403: {"description": "Not authorized to update this professional"},
        404: {"description": "Professional not found"},
    },
)
async def update_professional(
    professional_id: int,
    data: ProfessionalUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfessionalResponse:
    """
    Update professional information.

    Required permissions:
    - ADMIN: Can update any professional
    - RECEPTIONIST: Can update professionals in their salon
    - PROFESSIONAL: Can update their own profile (limited fields)
    """
    prof_repo = ProfessionalRepository(db)

    # Get professional
    professional = await prof_repo.get_by_id(professional_id)
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Professional with ID {professional_id} not found",
        )

    # RBAC: Check permissions
    if current_user.role == "ADMIN":
        # Admin can update any professional
        pass
    elif current_user.role == "RECEPTIONIST":
        # Receptionist can update professionals in their salon
        # TODO: Implement salon membership check
        pass
    elif current_user.role == "PROFESSIONAL":
        # Professional can only update their own profile
        if professional.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own professional profile",
            )
        # Professionals cannot change commission_percentage
        if data.commission_percentage is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Professionals cannot change their commission percentage",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update professionals",
        )

    # Prepare update data
    update_data = data.model_dump(exclude_unset=True)

    # Update professional
    updated = await prof_repo.update(professional_id, **update_data)

    return ProfessionalResponse.model_validate(updated)


@router.delete(
    "/{professional_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate professional",
    description="Deactivate a professional (soft delete by setting is_active=False)",
    responses={
        204: {"description": "Professional deactivated successfully"},
        403: {"description": "Not authorized to deactivate professionals"},
        404: {"description": "Professional not found"},
    },
)
async def deactivate_professional(
    professional_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Deactivate a professional (soft delete).

    Required permissions: ADMIN or RECEPTIONIST role.
    """
    # RBAC: Only ADMIN and RECEPTIONIST can deactivate professionals
    if current_user.role not in ["ADMIN", "RECEPTIONIST"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and receptionists can deactivate professionals",
        )

    prof_repo = ProfessionalRepository(db)

    # Get professional
    professional = await prof_repo.get_by_id(professional_id)
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Professional with ID {professional_id} not found",
        )

    # Soft delete by setting is_active=False
    await prof_repo.update(professional_id, is_active=False)

    return None
