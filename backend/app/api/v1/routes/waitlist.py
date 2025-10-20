"""Waitlist endpoints for queue management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.waitlist import (
    WaitlistJoinRequest,
    WaitlistJoinResponse,
    WaitlistLeaveRequest,
    WaitlistOfferRequest,
    WaitlistOfferResponse,
    WaitlistOfferResponseRequest,
    WaitlistOfferResponseResponse,
    WaitlistStatusResponse,
    WaitlistStatisticsResponse,
)
from backend.app.core.security.rbac import get_current_user
from backend.app.db.models.user import User, UserRole
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.db.repositories.waitlist import WaitlistRepository
from backend.app.db.session import get_db
from backend.app.domain.scheduling.services.slot_service import SlotService
from backend.app.services.waitlist import WaitlistService

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post(
    "/join",
    response_model=WaitlistJoinResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join waitlist",
    description="""
    Add client to waitlist for a specific professional/service/time.

    This endpoint:
    - Validates the requested slot and client
    - Adds client to appropriate queue position
    - Returns position and estimated wait time
    - Prevents duplicate waitlist entries
    """,
)
async def join_waitlist(
    request: WaitlistJoinRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Join waitlist for a service slot."""

    # Only clients can join waitlists
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can join waitlists",
        )

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        waitlist_entry = await waitlist_service.join_waitlist(
            client_id=current_user.id,
            professional_id=request.professional_id,
            service_id=request.service_id,
            unit_id=request.unit_id,
            preferred_datetime=request.preferred_datetime,
            flexibility_hours=request.flexibility_hours,
            priority=request.priority,
            notes=request.notes,
            notify_email=request.notify_email,
            notify_sms=request.notify_sms,
            notify_push=request.notify_push,
        )

        return WaitlistJoinResponse(
            waitlist_id=waitlist_entry.id,
            position=waitlist_entry.position,
            estimated_wait_time=f"Position {waitlist_entry.position} in queue",
            message=f"Successfully joined waitlist at position {waitlist_entry.position}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{waitlist_id}",
    summary="Leave waitlist",
    description="""
    Remove client from waitlist and reposition remaining entries.

    This endpoint:
    - Validates client owns the waitlist entry
    - Removes entry from queue
    - Updates positions for remaining clients
    - Only allows leaving active or offered entries
    """,
)
async def leave_waitlist(
    waitlist_id: int,
    request: WaitlistLeaveRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Leave waitlist."""

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        success = await waitlist_service.leave_waitlist(
            waitlist_id=waitlist_id,
            client_id=current_user.id,
            reason=request.reason,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waitlist entry not found",
            )

        return {"message": "Successfully left waitlist"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/my-status",
    response_model=WaitlistStatusResponse,
    summary="Get my waitlist status",
    description="""
    Get current waitlist status for the authenticated client.

    This endpoint:
    - Returns all waitlist entries for the client
    - Shows current positions and offer details
    - Includes notification preferences
    - Only shows entries client has access to
    """,
)
async def get_my_waitlist_status(
    active_only: bool = Query(True, description="Only return active entries"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get client's waitlist status."""

    # Only clients can view their own status
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can view waitlist status",
        )

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        entries_data = await waitlist_service.get_client_waitlist_status(
            current_user.id, active_only
        )

        # Convert to response format
        from backend.app.api.v1.schemas.waitlist import WaitlistEntryResponse

        entries = []
        for entry_data in entries_data:
            entry = WaitlistEntryResponse(**entry_data)
            entries.append(entry)

        active_count = len([e for e in entries if e.status == "active"])

        return WaitlistStatusResponse(
            entries=entries,
            total_active=active_count,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{waitlist_id}/respond",
    response_model=WaitlistOfferResponseResponse,
    summary="Respond to waitlist offer",
    description="""
    Respond to a slot offer from waitlist.

    This endpoint:
    - Validates client owns the waitlist entry
    - Checks offer hasn't expired
    - Creates booking if accepted
    - Offers slot to next person if declined
    - Records response with notes
    """,
)
async def respond_to_offer(
    waitlist_id: int,
    request: WaitlistOfferResponseRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Respond to waitlist slot offer."""

    # Only clients can respond to offers
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can respond to offers",
        )

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        booking = await waitlist_service.respond_to_offer(
            waitlist_id=waitlist_id,
            client_id=current_user.id,
            accepted=request.accepted,
            response_notes=request.response_notes,
        )

        if request.accepted:
            message = "Offer accepted and booking created successfully"
            booking_id = booking.id if booking else None
        else:
            message = "Offer declined, slot offered to next in line"
            booking_id = None

        return WaitlistOfferResponseResponse(
            accepted=request.accepted,
            booking_id=booking_id,
            message=message,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Professional/Admin endpoints

@router.post(
    "/offer-slot",
    response_model=WaitlistOfferResponse,
    summary="Offer slot to waitlist",
    description="""
    Offer an available slot to eligible waitlist entries.

    This endpoint:
    - Finds eligible waitlist entries for the slot
    - Offers to highest priority/earliest position
    - Sets offer expiration time
    - Sends notifications to client
    - Requires PROFESSIONAL or ADMIN role
    """,
)
async def offer_slot_to_waitlist(
    request: WaitlistOfferRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Offer available slot to waitlist."""

    # Check permissions
    if current_user.role not in [UserRole.PROFESSIONAL, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professionals and admins can offer slots",
        )

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        offers_made = await waitlist_service.offer_slot_to_waitlist(
            professional_id=request.professional_id,
            service_id=request.service_id,
            slot_start=request.slot_start,
            slot_end=request.slot_end,
            offer_duration_hours=request.offer_duration_hours,
        )

        message = f"Offered slot to {len(offers_made)} waitlist entry(ies)"
        if not offers_made:
            message = "No eligible waitlist entries found for this slot"

        return WaitlistOfferResponse(
            offers_made=offers_made,
            message=message,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/professional/{professional_id}",
    summary="Get professional's waitlist",
    description="""
    Get waitlist entries for a specific professional.

    This endpoint:
    - Returns waitlist ordered by priority and position
    - Shows client details and preferences
    - Includes offer status and timing
    - Requires PROFESSIONAL or ADMIN role
    """,
)
async def get_professional_waitlist(
    professional_id: int,
    active_only: bool = Query(True, description="Only return active entries"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get waitlist for a professional."""

    # Check permissions
    if current_user.role not in [UserRole.PROFESSIONAL, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professionals and admins can view waitlists",
        )

    # Professionals can only view their own waitlist
    if current_user.role == UserRole.PROFESSIONAL and current_user.id != professional_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Professionals can only view their own waitlist",
        )

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        waitlist_entries = await waitlist_service.get_professional_waitlist(
            professional_id, active_only
        )

        return {
            "professional_id": professional_id,
            "entries": waitlist_entries,
            "total_entries": len(waitlist_entries),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/statistics",
    response_model=WaitlistStatisticsResponse,
    summary="Get waitlist statistics",
    description="""
    Get waitlist statistics for analysis and reporting.

    This endpoint:
    - Returns counts by status and conversion rates
    - Calculates average wait times
    - Supports filtering by professional, service, unit
    - Provides data for dashboard visualization
    - Requires PROFESSIONAL or ADMIN role
    """,
)
async def get_waitlist_statistics(
    professional_id: int = Query(None, description="Filter by professional ID"),
    service_id: int = Query(None, description="Filter by service ID"),
    unit_id: int = Query(None, description="Filter by unit ID"),
    start_date: datetime = Query(None, description="Start date for statistics"),
    end_date: datetime = Query(None, description="End date for statistics"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get waitlist statistics."""

    # Check permissions
    if current_user.role not in [UserRole.PROFESSIONAL, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professionals and admins can view statistics",
        )

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        stats = await waitlist_service.get_waitlist_statistics(
            professional_id=professional_id,
            service_id=service_id,
            unit_id=unit_id,
            start_date=start_date,
            end_date=end_date,
        )

        return WaitlistStatisticsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/expire-offers",
    summary="Expire old offers",
    description="""
    Manually expire offers that have passed their deadline.

    This endpoint:
    - Finds offers past their expiration time
    - Marks them as expired
    - Offers slots to next people in line
    - Returns count of expired offers
    - Requires ADMIN role
    """,
)
async def expire_old_offers(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Expire old waitlist offers."""

    # Check permissions - only admins can manually expire offers
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can expire offers",
        )

    # Initialize repositories and services
    waitlist_repo = WaitlistRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    slot_service = SlotService(session)

    waitlist_service = WaitlistService(
        waitlist_repo, booking_repo, user_repo, slot_service
    )

    try:
        expired_count = await waitlist_service.expire_old_offers()

        return {
            "expired_offers": expired_count,
            "message": f"Expired {expired_count} old offers and offered to next in line",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
