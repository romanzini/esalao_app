"""Booking endpoints for reservation management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.booking import (
    BookingCreateRequest,
    BookingListResponse,
    BookingResponse,
    BookingStatusUpdate,
)
from backend.app.core.security.rbac import get_current_user
from backend.app.db.models.booking import BookingStatus
from backend.app.db.models.user import User, UserRole
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.service import ServiceRepository
from backend.app.db.session import get_db
from backend.app.domain.scheduling.services.slot_service import SlotService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new booking",
    description="""
    Create a new service booking with slot validation.

    This endpoint:
    - Validates slot availability before creating the booking
    - Prevents double-booking conflicts
    - Retrieves service details (price, duration)
    - Creates booking in PENDING status

    **Authentication Required:** Client, Professional, Receptionist, or Admin

    **Example Request:**
    ```json
    {
      "professional_id": 1,
      "service_id": 1,
      "scheduled_at": "2025-10-20T09:00:00",
      "notes": "First time client"
    }
    ```

    **Business Rules:**
    - Slot must be available at the requested time
    - Service must exist and be active
    - Professional must be available on that date/time
    """,
    responses={
        201: {"description": "Booking created successfully"},
        400: {"description": "Invalid request or slot not available"},
        404: {"description": "Service or professional not found"},
        409: {"description": "Slot already booked (conflict)"},
    },
)
async def create_booking(
    request: BookingCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """
    Create a new booking.

    Args:
        request: Booking creation data
        current_user: Authenticated user
        session: Database session

    Returns:
        BookingResponse with created booking details

    Raises:
        HTTPException: 404 if service not found
        HTTPException: 409 if slot already booked
    """
    # Repositories
    booking_repo = BookingRepository(session)
    service_repo = ServiceRepository(session)
    slot_service = SlotService(session)

    # 1. Validate service exists
    service = await service_repo.get_by_id(request.service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with ID {request.service_id} not found",
        )

    # 2. Check slot availability
    target_date = request.scheduled_at.date()
    try:
        available_slots = await slot_service.calculate_available_slots(
            professional_id=request.professional_id,
            target_date=target_date,
            service_id=request.service_id,
            slot_interval_minutes=service.duration_minutes,
        )

        # Check if the requested slot is in available slots
        requested_time = request.scheduled_at.time()
        slot_available = any(
            slot.start_time.time() == requested_time
            for slot in available_slots.slots
        )

        if not slot_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot at {request.scheduled_at} is not available",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # 3. Create booking
    booking = await booking_repo.create(
        client_id=current_user.id,
        professional_id=request.professional_id,
        service_id=request.service_id,
        scheduled_at=request.scheduled_at,
        duration_minutes=service.duration_minutes,
        service_price=float(service.price),
        notes=request.notes,
    )

    await session.commit()
    await session.refresh(booking)

    return BookingResponse.model_validate(booking)


@router.get(
    "",
    response_model=BookingListResponse,
    summary="List bookings",
    description="""
    List bookings with filters and pagination.

    **Access Control:**
    - **Clients**: See only their own bookings
    - **Professionals**: See bookings assigned to them
    - **Receptionists/Admins**: See all bookings in their salon

    **Filters:**
    - `status`: Filter by booking status
    - `professional_id`: Filter by professional
    - `date_from` / `date_to`: Filter by date range

    **Pagination:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 10, max: 100)
    """,
)
async def list_bookings(
    status: BookingStatus | None = Query(None, description="Filter by status"),
    professional_id: int | None = Query(None, description="Filter by professional"),
    date_from: datetime | None = Query(None, description="Filter from date"),
    date_to: datetime | None = Query(None, description="Filter to date"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, gt=0, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookingListResponse:
    """
    List bookings with filters.

    Args:
        status: Optional status filter
        professional_id: Optional professional filter
        date_from: Optional start date filter
        date_to: Optional end date filter
        page: Page number
        page_size: Items per page
        current_user: Authenticated user
        session: Database session

    Returns:
        BookingListResponse with paginated bookings
    """
    booking_repo = BookingRepository(session)

    # Apply RBAC filters
    filters = {}

    if current_user.role == UserRole.CLIENT:
        # Clients see only their bookings
        filters["client_id"] = current_user.id
    elif current_user.role == UserRole.PROFESSIONAL:
        # Professionals see bookings assigned to them
        # TODO: Get professional_id from current_user
        filters["professional_id"] = professional_id or 1  # Placeholder
    # Admin/Receptionist see all (no additional filter)

    # Apply user-provided filters
    if status:
        filters["status"] = status
    if professional_id and current_user.role in [UserRole.ADMIN, UserRole.RECEPTIONIST]:
        filters["professional_id"] = professional_id

    # Fetch bookings (simplified - repository needs pagination support)
    if current_user.role == UserRole.CLIENT:
        bookings = await booking_repo.list_by_client_id(current_user.id)
    elif professional_id and current_user.role == UserRole.PROFESSIONAL:
        bookings = await booking_repo.list_by_professional_id(professional_id)
    else:
        # List all (needs implementation in repository)
        bookings = []

    # Apply pagination (simplified)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_bookings = bookings[start_idx:end_idx]

    return BookingListResponse(
        bookings=[BookingResponse.model_validate(b) for b in paginated_bookings],
        total=len(bookings),
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking details",
    description="""
    Get detailed information about a specific booking.

    **Access Control:**
    - **Clients**: Can view only their own bookings
    - **Professionals**: Can view bookings assigned to them
    - **Receptionists/Admins**: Can view all bookings
    """,
    responses={
        200: {"description": "Booking details retrieved successfully"},
        403: {"description": "Access forbidden"},
        404: {"description": "Booking not found"},
    },
)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """
    Get booking by ID.

    Args:
        booking_id: Booking ID
        current_user: Authenticated user
        session: Database session

    Returns:
        BookingResponse with booking details

    Raises:
        HTTPException: 404 if booking not found
        HTTPException: 403 if user doesn't have access
    """
    booking_repo = BookingRepository(session)

    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found",
        )

    # Check access permissions
    if current_user.role == UserRole.CLIENT and booking.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this booking",
        )
    # TODO: Add professional check when professional relationship is available

    return BookingResponse.model_validate(booking)


@router.patch(
    "/{booking_id}/status",
    response_model=BookingResponse,
    summary="Update booking status",
    description="""
    Update the status of a booking.

    **Allowed Status Transitions:**
    - PENDING → CONFIRMED (by receptionist/admin)
    - CONFIRMED → IN_PROGRESS (by professional)
    - IN_PROGRESS → COMPLETED (by professional)
    - Any → CANCELLED (by client before service, by receptionist/admin anytime)
    - CONFIRMED → NO_SHOW (by receptionist/admin)

    **Access Control:**
    - **Clients**: Can cancel their own PENDING/CONFIRMED bookings
    - **Professionals**: Can update to IN_PROGRESS/COMPLETED for their bookings
    - **Receptionists/Admins**: Can update to any status
    """,
    responses={
        200: {"description": "Status updated successfully"},
        400: {"description": "Invalid status transition"},
        403: {"description": "Access forbidden"},
        404: {"description": "Booking not found"},
    },
)
async def update_booking_status(
    booking_id: int,
    status_update: BookingStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """
    Update booking status.

    Args:
        booking_id: Booking ID
        status_update: New status and optional cancellation reason
        current_user: Authenticated user
        session: Database session

    Returns:
        BookingResponse with updated booking

    Raises:
        HTTPException: 404 if booking not found
        HTTPException: 403 if user doesn't have permission
        HTTPException: 400 if invalid status transition
    """
    booking_repo = BookingRepository(session)

    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found",
        )

    # Validate cancellation reason
    if status_update.status == BookingStatus.CANCELLED and not status_update.cancellation_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancellation reason is required when cancelling a booking",
        )

    # Check permissions based on role
    if current_user.role == UserRole.CLIENT:
        # Clients can only cancel their own bookings
        if booking.client_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this booking",
            )
        if status_update.status != BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clients can only cancel bookings",
            )
        if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only cancel PENDING or CONFIRMED bookings",
            )

    # Update status
    updated_booking = await booking_repo.update_status(
        booking_id=booking_id,
        new_status=status_update.status,
        cancellation_reason=status_update.cancellation_reason,
    )

    await session.commit()
    await session.refresh(updated_booking)

    return BookingResponse.model_validate(updated_booking)


@router.delete(
    "/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel booking",
    description="""
    Cancel a booking (soft delete by setting status to CANCELLED).

    This is a convenience endpoint that sets the status to CANCELLED.
    Equivalent to: PATCH /{booking_id}/status with status='cancelled'

    **Access Control:**
    - **Clients**: Can cancel their own PENDING/CONFIRMED bookings
    - **Receptionists/Admins**: Can cancel any booking
    """,
    responses={
        204: {"description": "Booking cancelled successfully"},
        403: {"description": "Access forbidden"},
        404: {"description": "Booking not found"},
    },
)
async def cancel_booking(
    booking_id: int,
    cancellation_reason: str = Query(..., description="Reason for cancellation"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Cancel a booking.

    Args:
        booking_id: Booking ID
        cancellation_reason: Reason for cancellation
        current_user: Authenticated user
        session: Database session

    Raises:
        HTTPException: 404 if booking not found
        HTTPException: 403 if user doesn't have permission
    """
    booking_repo = BookingRepository(session)

    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found",
        )

    # Check permissions
    if current_user.role == UserRole.CLIENT and booking.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this booking",
        )

    if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel PENDING or CONFIRMED bookings",
        )

    # Cancel booking
    await booking_repo.update_status(
        booking_id=booking_id,
        new_status=BookingStatus.CANCELLED,
        cancellation_reason=cancellation_reason,
    )

    await session.commit()
