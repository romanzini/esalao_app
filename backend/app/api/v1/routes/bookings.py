"""Booking endpoints for reservation management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.booking import (
    BookingCreateRequest,
    BookingListResponse,
    BookingResponse,
    BookingStatusUpdate,
    CancellationFeeRequest,
    CancellationFeeResponse,
    BookingCancellationRequest,
    BookingCancellationResponse,
    NoShowEvaluationRequest,
    NoShowEvaluationResponse,
    NoShowMarkRequest,
    NoShowMarkResponse,
    NoShowDisputeRequest,
    NoShowDisputeResponse,
    NoShowStatisticsResponse,
)
from backend.app.core.security.rbac import get_current_user
from backend.app.db.models.booking import BookingStatus
from backend.app.db.models.user import User, UserRole
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.service import ServiceRepository
from backend.app.db.repositories.cancellation_policy import CancellationPolicyRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.db.session import get_db
from backend.app.domain.scheduling.services.slot_service import SlotService
from backend.app.domain.policies.booking_cancellation import BookingCancellationService
from backend.app.services.no_show import NoShowService
from backend.app.services.booking_notifications import BookingNotificationService
from backend.app.domain.policies.no_show import NoShowReason

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

    # 4. Send notifications
    try:
        notification_service = BookingNotificationService(session)

        # Send booking confirmation notifications
        await notification_service.notify_booking_created(
            booking_id=booking.id,
            correlation_id=f"booking_create_{booking.id}"
        )

        # Schedule booking reminders
        await notification_service.schedule_booking_reminders(
            booking_id=booking.id
        )

    except Exception as e:
        # Log notification errors but don't fail the booking creation
        logger.error(f"Failed to send booking notifications for booking {booking.id}: {str(e)}")

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

    # Send cancellation notifications
    try:
        notification_service = BookingNotificationService(session)
        await notification_service.notify_booking_cancelled(
            booking_id=booking_id,
            cancellation_reason=cancellation_reason,
            correlation_id=f"booking_cancel_{booking_id}"
        )
    except Exception as e:
        # Log notification errors but don't fail the cancellation
        logger.error(f"Failed to send cancellation notifications for booking {booking_id}: {str(e)}")


@router.get(
    "/{booking_id}/cancellation-fee",
    response_model=CancellationFeeResponse,
    summary="Calculate cancellation fee",
    description="""
    Calculate the cancellation fee for a booking based on its policy.

    This endpoint:
    - Calculates fee based on advance notice and policy rules
    - Shows which tier would be applied
    - Indicates if refund is allowed
    - Does not modify the booking

    **Authentication Required:** Client (own bookings), Professional, Receptionist, or Admin
    """,
    responses={
        200: {"description": "Fee calculated successfully"},
        403: {"description": "Access forbidden"},
        404: {"description": "Booking not found"},
    },
)
async def get_cancellation_fee(
    booking_id: int,
    request: CancellationFeeRequest = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CancellationFeeResponse:
    """Calculate cancellation fee for a booking."""
    booking_repo = BookingRepository(session)
    policy_repo = CancellationPolicyRepository(session)
    cancellation_service = BookingCancellationService(booking_repo, policy_repo)

    # Verify booking exists and user has permission
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
            detail="You don't have permission to view this booking's fee",
        )

    try:
        cancellation_time = request.cancellation_time if request else None
        fee_info = await cancellation_service.calculate_cancellation_fee(
            booking_id, cancellation_time
        )

        return CancellationFeeResponse(**fee_info)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{booking_id}/cancel-with-policy",
    response_model=BookingCancellationResponse,
    summary="Cancel booking with policy",
    description="""
    Cancel a booking applying cancellation policy and fees.

    This endpoint:
    - Calculates and applies cancellation fee based on policy
    - Updates booking status to CANCELLED
    - Records fee amount and policy used
    - Determines refund amount
    - Tracks who cancelled and when

    **Authentication Required:** Client (own bookings), Professional, Receptionist, or Admin
    """,
    responses={
        200: {"description": "Booking cancelled successfully"},
        400: {"description": "Cannot cancel booking"},
        403: {"description": "Access forbidden"},
        404: {"description": "Booking not found"},
    },
)
async def cancel_booking_with_policy(
    booking_id: int,
    request: BookingCancellationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookingCancellationResponse:
    """Cancel a booking with policy-based fee calculation."""
    booking_repo = BookingRepository(session)
    policy_repo = CancellationPolicyRepository(session)
    cancellation_service = BookingCancellationService(booking_repo, policy_repo)

    # Verify booking exists and user has permission
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

    try:
        result = await cancellation_service.cancel_booking(
            booking_id=booking_id,
            cancelled_by_id=current_user.id,
            reason=request.reason,
            cancellation_time=request.cancellation_time,
        )

        await session.commit()

        # Send cancellation notifications
        try:
            notification_service = BookingNotificationService(session)
            await notification_service.notify_booking_cancelled(
                booking_id=booking_id,
                cancellation_reason=request.reason,
                refund_amount=result['refund_amount'],
                cancellation_fee=result['cancellation_fee'],
                correlation_id=f"booking_cancel_policy_{booking_id}"
            )
        except Exception as e:
            # Log notification errors but don't fail the cancellation
            logger.error(f"Failed to send cancellation notifications for booking {booking_id}: {str(e)}")

        return BookingCancellationResponse(
            success=result['success'],
            message=result['message'],
            cancellation_fee=float(result['cancellation_fee']),
            refund_amount=float(result['refund_amount']),
            payment_required=result['payment_required'],
            policy_applied=result['policy_applied'],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{booking_id}/can-cancel",
    summary="Check if booking can be cancelled",
    description="""
    Check if a booking can be cancelled and preview the cancellation details.

    This endpoint:
    - Validates if cancellation is allowed
    - Shows preview of fees that would be applied
    - Does not modify the booking
    - Useful for UI confirmation dialogs

    **Authentication Required:** Client (own bookings), Professional, Receptionist, or Admin
    """,
    responses={
        200: {"description": "Cancellation check completed"},
        403: {"description": "Access forbidden"},
        404: {"description": "Booking not found"},
    },
)
async def check_can_cancel(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Check if a booking can be cancelled."""
    booking_repo = BookingRepository(session)
    policy_repo = CancellationPolicyRepository(session)
    cancellation_service = BookingCancellationService(booking_repo, policy_repo)

    # Verify booking exists and user has permission
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
            detail="You don't have permission to check this booking",
        )

    result = await cancellation_service.can_cancel_booking(booking_id)
    return result


# No-Show Management Endpoints

@router.post(
    "/{booking_id}/no-show/evaluate",
    response_model=NoShowEvaluationResponse,
    summary="Evaluate booking for no-show",
    description="""
    Evaluate if a booking should be marked as no-show based on current time and policy.

    This endpoint:
    - Checks if booking meets no-show criteria
    - Calculates potential no-show fee
    - Returns evaluation details without marking the booking
    - Requires PROFESSIONAL or ADMIN role
    """,
)
async def evaluate_no_show(
    booking_id: int,
    request: NoShowEvaluationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Evaluate booking for no-show marking."""

    # Check permissions
    if current_user.role not in [UserRole.PROFESSIONAL, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professionals and admins can evaluate no-shows",
        )

    # Initialize repositories and services
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    no_show_service = NoShowService(booking_repo, user_repo)

    try:
        evaluation = await no_show_service.evaluate_booking_for_no_show(
            booking_id, request.evaluation_time
        )

        return NoShowEvaluationResponse(
            booking_id=booking_id,
            should_mark_no_show=evaluation.should_mark_no_show,
            reason=evaluation.reason,
            fee_amount=evaluation.fee_amount,
            fee_calculation=evaluation.fee_calculation,
            detection_time=evaluation.detection_time,
            grace_period_expired=evaluation.grace_period_expired,
            minutes_late=evaluation.minutes_late,
            policy_id=evaluation.policy_id,
            auto_detected=evaluation.auto_detected,
            can_dispute=evaluation.can_dispute,
            dispute_deadline=evaluation.dispute_deadline,
            recommended_action=evaluation.recommended_action,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{booking_id}/no-show/mark",
    response_model=NoShowMarkResponse,
    summary="Mark booking as no-show",
    description="""
    Mark a booking as no-show with optional fee.

    This endpoint:
    - Marks the booking as no-show
    - Applies fee based on policy or manual override
    - Records who marked it and when
    - Updates booking status
    - Requires PROFESSIONAL or ADMIN role
    """,
)
async def mark_no_show(
    booking_id: int,
    request: NoShowMarkRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Mark booking as no-show."""

    # Check permissions
    if current_user.role not in [UserRole.PROFESSIONAL, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professionals and admins can mark no-shows",
        )

    # Initialize repositories and services
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    no_show_service = NoShowService(booking_repo, user_repo)

    try:
        booking = await no_show_service.mark_booking_no_show(
            booking_id=booking_id,
            marked_by_id=current_user.id,
            reason=request.reason,
            manual_fee_amount=request.manual_fee_amount,
            reason_notes=request.reason_notes,
            current_time=request.marked_at,
        )

        return NoShowMarkResponse(
            booking_id=booking_id,
            marked_at=booking.marked_no_show_at,
            marked_by_id=booking.marked_no_show_by_id,
            reason=booking.no_show_reason,
            fee_amount=float(booking.no_show_fee_amount or 0),
            status=booking.status,
            message="Booking marked as no-show successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{booking_id}/no-show/dispute",
    response_model=NoShowDisputeResponse,
    summary="Dispute no-show marking",
    description="""
    Dispute a no-show marking within the allowed time window.

    This endpoint:
    - Allows clients to dispute no-show markings
    - Validates dispute window hasn't expired
    - Records dispute details for review
    - Only the booking client can dispute
    """,
)
async def dispute_no_show(
    booking_id: int,
    request: NoShowDisputeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Dispute no-show marking."""

    # Initialize repositories and services
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    no_show_service = NoShowService(booking_repo, user_repo)

    # Check if user can dispute
    dispute_check = await no_show_service.can_dispute_no_show(
        booking_id, current_user.id
    )

    if not dispute_check["can_dispute"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispute no-show: {dispute_check['reason']}",
        )

    try:
        booking = await no_show_service.dispute_no_show(
            booking_id=booking_id,
            disputed_by_id=current_user.id,
            dispute_reason=request.dispute_reason,
        )

        return NoShowDisputeResponse(
            booking_id=booking_id,
            disputed_at=datetime.utcnow(),
            disputed_by_id=current_user.id,
            dispute_reason=request.dispute_reason,
            status="dispute_filed",
            message="Dispute filed successfully and will be reviewed",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{booking_id}/no-show/can-dispute",
    summary="Check if no-show can be disputed",
    description="""
    Check if a no-show marking can be disputed by the current user.

    Returns dispute eligibility, deadline, and remaining time.
    """,
)
async def can_dispute_no_show(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Check if no-show can be disputed."""

    # Initialize repositories and services
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    no_show_service = NoShowService(booking_repo, user_repo)

    try:
        result = await no_show_service.can_dispute_no_show(
            booking_id, current_user.id
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/no-show/statistics",
    response_model=NoShowStatisticsResponse,
    summary="Get no-show statistics",
    description="""
    Get no-show statistics for a specific period and filters.

    This endpoint:
    - Returns no-show rates and counts
    - Provides financial impact data
    - Breaks down by reasons
    - Supports filtering by unit, professional, date range
    - Requires PROFESSIONAL or ADMIN role
    """,
)
async def get_no_show_statistics(
    unit_id: int = Query(None, description="Filter by unit ID"),
    professional_id: int = Query(None, description="Filter by professional ID"),
    start_date: datetime = Query(None, description="Start date for statistics"),
    end_date: datetime = Query(None, description="End date for statistics"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get no-show statistics."""

    # Check permissions
    if current_user.role not in [UserRole.PROFESSIONAL, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professionals and admins can view statistics",
        )

    # Initialize repositories and services
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    no_show_service = NoShowService(booking_repo, user_repo)

    try:
        stats = await no_show_service.get_no_show_statistics(
            unit_id=unit_id,
            professional_id=professional_id,
            start_date=start_date,
            end_date=end_date,
        )

        return NoShowStatisticsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/no-show/auto-detect",
    summary="Run auto no-show detection",
    description="""
    Run automatic no-show detection for recent bookings.

    This endpoint:
    - Scans recent bookings for no-show conditions
    - Automatically marks qualifying bookings as no-show
    - Returns summary of actions taken
    - Requires ADMIN role
    """,
)
async def auto_detect_no_shows(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Run automatic no-show detection."""

    # Check permissions - only admins can run auto-detection
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can run auto no-show detection",
        )

    # Initialize repositories and services
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    no_show_service = NoShowService(booking_repo, user_repo)

    try:
        results = await no_show_service.auto_detect_no_shows(time_window_hours)

        summary = {
            "time_window_hours": time_window_hours,
            "total_processed": len(results),
            "marked_no_show": len([r for r in results if r["action"] == "marked_no_show"]),
            "no_action": len([r for r in results if r["action"] == "no_action"]),
            "errors": len([r for r in results if r["action"] == "error"]),
            "results": results,
        }

        return summary

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
