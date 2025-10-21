"""Multi-service booking API endpoints."""

import logging
from datetime import datetime
from typing import List, Optional, Generic, TypeVar

T = TypeVar('T')

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.rbac import get_current_user, require_role
from backend.app.db.session import get_db
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.user import User
from backend.app.db.models.professional import Professional
from backend.app.db.models.multi_service_booking import MultiServiceBookingStatus
from backend.app.api.v1.schemas.multi_service_booking import (
    MultiServiceBookingCreate,
    MultiServiceBookingResponse,
    MultiServiceBookingUpdate,
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    PackageSuggestionResponse,
    PricingCalculationResponse
)
from backend.app.services.multi_service_booking import MultiServiceBookingService

logger = logging.getLogger(__name__)
router = APIRouter()


class PagedResponse(BaseModel, Generic[T]):
    """Generic paged response model."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


@router.post("/check-availability", response_model=AvailabilityCheckResponse)
async def check_package_availability(
    request: AvailabilityCheckRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check availability for a package of services."""
    try:
        service = MultiServiceBookingService(session)

        # Convert services data to the format expected by the service
        services_data = [
            {
                "service_id": s.service_id,
                "professional_id": s.professional_id,
                "scheduled_at": s.scheduled_at,
                "notes": s.notes
            }
            for s in request.services
        ]

        availability = await service.check_package_availability(
            services_data=services_data,
            max_gap_minutes=request.max_gap_minutes
        )

        return AvailabilityCheckResponse(**availability)

    except Exception as e:
        logger.error(f"Error checking package availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to check availability: {str(e)}"
        )


@router.post("/", response_model=MultiServiceBookingResponse)
async def create_multi_service_booking(
    booking_data: MultiServiceBookingCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new multi-service booking."""
    try:
        service = MultiServiceBookingService(session)

        # Convert services data
        services_data = [
            {
                "service_id": s.service_id,
                "professional_id": s.professional_id,
                "scheduled_at": s.scheduled_at,
                "notes": s.notes
            }
            for s in booking_data.services
        ]

        # Create the booking
        multi_booking = await service.create_multi_service_booking(
            client_id=current_user.id,
            package_name=booking_data.package_name,
            services_data=services_data,
            package_notes=booking_data.notes
        )

        await session.commit()

        # Get the complete booking with relationships
        complete_booking = await service.multi_booking_repo.get_by_id(multi_booking.id)

        return MultiServiceBookingResponse.from_orm(complete_booking)

    except ValueError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating multi-service booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create multi-service booking"
        )


@router.get("/", response_model=PagedResponse[MultiServiceBookingResponse])
async def list_multi_service_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[MultiServiceBookingStatus] = None,
    client_id: Optional[int] = None,
    professional_id: Optional[int] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List multi-service bookings with filtering and pagination."""
    try:
        service = MultiServiceBookingService(session)

        # Apply role-based filtering
        if current_user.role == "CLIENT":
            client_id = current_user.id
        elif current_user.role == "PROFESSIONAL" and not client_id and not professional_id:
            # If professional and no specific filters, show their bookings
            professional_id = current_user.professional_profile.id if current_user.professional_profile else None

        bookings, total = await service.multi_booking_repo.list_with_pagination(
            page=page,
            page_size=page_size,
            status=status,
            client_id=client_id,
            professional_id=professional_id
        )

        return PagedResponse(
            items=[MultiServiceBookingResponse.from_orm(booking) for booking in bookings],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )

    except Exception as e:
        logger.error(f"Error listing multi-service bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list multi-service bookings"
        )


@router.get("/{booking_id}", response_model=MultiServiceBookingResponse)
async def get_multi_service_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific multi-service booking by ID."""
    try:
        service = MultiServiceBookingService(session)
        booking = await service.multi_booking_repo.get_by_id(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Multi-service booking not found"
            )

        # Check access permissions
        if current_user.role == "CLIENT" and booking.client_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this booking"
            )
        elif current_user.role == "PROFESSIONAL":
            # Check if professional is involved in any of the services
            professional_id = current_user.professional_profile.id if current_user.professional_profile else None
            if not any(b.professional_id == professional_id for b in booking.individual_bookings):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this booking"
                )

        return MultiServiceBookingResponse.from_orm(booking)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting multi-service booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get multi-service booking"
        )


@router.put("/{booking_id}", response_model=MultiServiceBookingResponse)
async def update_multi_service_booking(
    booking_id: int,
    update_data: MultiServiceBookingUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a multi-service booking."""
    try:
        service = MultiServiceBookingService(session)
        booking = await service.multi_booking_repo.get_by_id(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Multi-service booking not found"
            )

        # Check permissions
        if current_user.role == "CLIENT" and booking.client_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this booking"
            )

        # Update allowed fields
        update_dict = update_data.dict(exclude_unset=True)

        for field, value in update_dict.items():
            if hasattr(booking, field):
                setattr(booking, field, value)

        booking.updated_at = datetime.utcnow()
        await session.flush()
        await session.commit()

        updated_booking = await service.multi_booking_repo.get_by_id(booking_id)
        return MultiServiceBookingResponse.from_orm(updated_booking)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating multi-service booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update multi-service booking"
        )


@router.post("/{booking_id}/confirm", response_model=MultiServiceBookingResponse)
async def confirm_multi_service_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a multi-service booking."""
    try:
        service = MultiServiceBookingService(session)
        booking = await service.multi_booking_repo.get_by_id(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Multi-service booking not found"
            )

        # Only professionals involved or admins can confirm
        if current_user.role == "CLIENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clients cannot confirm bookings"
            )
        elif current_user.role == "PROFESSIONAL":
            professional_id = current_user.professional_profile.id if current_user.professional_profile else None
            if not any(b.professional_id == professional_id for b in booking.individual_bookings):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to confirm this booking"
                )

        confirmed_booking = await service.confirm_multi_service_booking(booking_id)
        await session.commit()

        return MultiServiceBookingResponse.from_orm(confirmed_booking)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error confirming multi-service booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm multi-service booking"
        )


@router.post("/{booking_id}/cancel", response_model=MultiServiceBookingResponse)
async def cancel_multi_service_booking(
    booking_id: int,
    cancellation_reason: str,
    partial_cancel: bool = False,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a multi-service booking."""
    try:
        service = MultiServiceBookingService(session)
        booking = await service.multi_booking_repo.get_by_id(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Multi-service booking not found"
            )

        # Check permissions
        if current_user.role == "CLIENT" and booking.client_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this booking"
            )
        elif current_user.role == "PROFESSIONAL":
            professional_id = current_user.professional_profile.id if current_user.professional_profile else None
            if not any(b.professional_id == professional_id for b in booking.individual_bookings):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to cancel this booking"
                )

        cancelled_booking = await service.cancel_multi_service_booking(
            booking_id,
            cancellation_reason,
            current_user.id,
            partial_cancel
        )
        await session.commit()

        return MultiServiceBookingResponse.from_orm(cancelled_booking)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error cancelling multi-service booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel multi-service booking"
        )


@router.get("/packages/suggestions", response_model=List[PackageSuggestionResponse])
async def get_package_suggestions(
    professional_id: Optional[int] = None,
    duration_preference: Optional[str] = Query(None, regex="^(short|medium|long)$"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get package suggestions based on preferences."""
    try:
        service = MultiServiceBookingService(session)

        suggestions = await service.get_package_suggestions(
            client_id=current_user.id if current_user.role == "CLIENT" else None,
            professional_id=professional_id,
            duration_preference=duration_preference
        )

        return [PackageSuggestionResponse(**suggestion) for suggestion in suggestions]

    except Exception as e:
        logger.error(f"Error getting package suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get package suggestions"
        )


@router.post("/pricing/calculate", response_model=PricingCalculationResponse)
async def calculate_package_pricing(
    request: AvailabilityCheckRequest,
    discount_percentage: float = Query(10.0, ge=0, le=50),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate pricing for a package with potential discounts."""
    try:
        service = MultiServiceBookingService(session)

        services_data = [
            {
                "service_id": s.service_id,
                "professional_id": s.professional_id,
                "scheduled_at": s.scheduled_at
            }
            for s in request.services
        ]

        pricing = await service.calculate_package_discount(
            services_data=services_data,
            discount_percentage=discount_percentage
        )

        return PricingCalculationResponse(**pricing)

    except Exception as e:
        logger.error(f"Error calculating package pricing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to calculate pricing: {str(e)}"
        )


# Admin-only endpoints
@router.get("/admin/stats", response_model=dict)
async def get_multi_service_stats(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get multi-service booking statistics (admin only)."""
    try:
        service = MultiServiceBookingService(session)
        stats = await service.multi_booking_repo.get_booking_statistics()

        return {
            "total_packages": stats.get("total_bookings", 0),
            "confirmed_packages": stats.get("confirmed_bookings", 0),
            "cancelled_packages": stats.get("cancelled_bookings", 0),
            "completed_packages": stats.get("completed_bookings", 0),
            "total_revenue": float(stats.get("total_revenue", 0)),
            "average_package_value": float(stats.get("average_booking_value", 0)),
            "average_services_per_package": stats.get("average_services_count", 0)
        }

    except Exception as e:
        logger.error(f"Error getting multi-service stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )
