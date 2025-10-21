"""Review API endpoints for customer reviews and ratings."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.review import (
    ReviewCreateRequest, ReviewUpdateRequest, ReviewModerationRequest,
    ProfessionalResponseRequest, ReviewHelpfulnessRequest, ReviewFlagRequest,
    BulkModerationRequest, ReviewListParams, ModerationListParams,
    StatsRequest, TrendsRequest,
    ReviewResponse, ReviewListResponse, ReviewStatsResponse,
    ReviewFlagResponse, ReviewModerationResponse, ReviewTrendsResponse,
    ReviewErrorResponse,
)
from backend.app.core.security.rbac import (
    get_current_user, require_admin, require_professional_or_staff
)
from backend.app.db.session import get_db
from backend.app.db.repositories.review import ReviewRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.loyalty import LoyaltyRepository
from backend.app.services.review import ReviewService
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.review import ReviewStatus, ReviewModerationReason
from backend.app.core.exceptions import ValidationError, AuthorizationError, NotFoundError


router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    """Get review service with dependencies."""
    review_repo = ReviewRepository(db)
    booking_repo = BookingRepository(db)
    loyalty_repo = LoyaltyRepository(db)
    return ReviewService(review_repo, booking_repo, loyalty_repo)


@router.post(
    "/",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new review",
    description="Create a review for a completed booking. Only clients can review their own bookings.",
)
async def create_review(
    request: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Create a new review for a completed booking."""
    try:
        review = await service.create_review(
            booking_id=request.booking_id,
            client_id=current_user.id,
            rating=request.rating,
            title=request.title,
            comment=request.comment,
            is_anonymous=request.is_anonymous,
        )
        return ReviewResponse.model_validate(review)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create review: {str(e)}"
        )


@router.put(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Update a review",
    description="Update a review within 24 hours of creation. Only the original author can edit.",
)
async def update_review(
    review_id: int = Path(..., description="Review ID"),
    request: ReviewUpdateRequest = ...,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Update an existing review."""
    try:
        review = await service.update_review(
            review_id=review_id,
            client_id=current_user.id,
            rating=request.rating,
            title=request.title,
            comment=request.comment,
            is_anonymous=request.is_anonymous,
        )
        return ReviewResponse.model_validate(review)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update review: {str(e)}"
        )


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Get review by ID",
    description="Get a specific review by its ID.",
)
async def get_review(
    review_id: int = Path(..., description="Review ID"),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Get a specific review by ID."""
    review = await service.get_review_by_id(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    return ReviewResponse.model_validate(review)


@router.get(
    "/",
    response_model=ReviewListResponse,
    summary="List reviews",
    description="List reviews with filtering and pagination options.",
)
async def list_reviews(
    params: ReviewListParams = Depends(),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    """List reviews with filtering and pagination."""
    try:
        reviews, total = await service.list_reviews(
            salon_id=params.salon_id,
            professional_id=params.professional_id,
            service_id=params.service_id,
            client_id=params.client_id,
            status=params.status,
            min_rating=params.min_rating,
            max_rating=params.max_rating,
            with_comments_only=params.with_comments_only,
            verified_only=params.verified_only,
            limit=params.size,
            offset=(params.page - 1) * params.size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )

        return ReviewListResponse(
            reviews=[ReviewResponse.model_validate(r) for r in reviews],
            total=total,
            page=params.page,
            size=params.size,
            has_next=total > params.page * params.size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reviews: {str(e)}"
        )


@router.get(
    "/booking/{booking_id}",
    response_model=Optional[ReviewResponse],
    summary="Get review by booking ID",
    description="Get review associated with a specific booking.",
)
async def get_review_by_booking(
    booking_id: int = Path(..., description="Booking ID"),
    service: ReviewService = Depends(get_review_service),
) -> Optional[ReviewResponse]:
    """Get review by booking ID."""
    review = await service.get_review_by_booking_id(booking_id)
    if review:
        return ReviewResponse.model_validate(review)
    return None


@router.post(
    "/{review_id}/response",
    response_model=ReviewResponse,
    summary="Add professional response",
    description="Add a response to a review. Only professionals and salon owners can respond.",
)
async def add_professional_response(
    review_id: int = Path(..., description="Review ID"),
    request: ProfessionalResponseRequest = ...,
    current_user: User = Depends(require_professional_or_staff),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Add professional or salon owner response to a review."""
    try:
        review = await service.add_professional_response(
            review_id=review_id,
            responder_id=current_user.id,
            responder_role=current_user.role,
            response_text=request.response_text,
        )
        return ReviewResponse.model_validate(review)
    except (ValidationError, AuthorizationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )


@router.post(
    "/{review_id}/helpfulness",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Vote on review helpfulness",
    description="Vote whether a review is helpful or not.",
)
async def vote_helpfulness(
    review_id: int = Path(..., description="Review ID"),
    request: ReviewHelpfulnessRequest = ...,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    """Vote on review helpfulness."""
    try:
        await service.vote_helpfulness(
            review_id=review_id,
            user_id=current_user.id,
            is_helpful=request.is_helpful,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )


@router.post(
    "/{review_id}/flag",
    response_model=ReviewFlagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Flag review for moderation",
    description="Flag a review as inappropriate for admin review.",
)
async def flag_review(
    review_id: int = Path(..., description="Review ID"),
    request: ReviewFlagRequest = ...,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewFlagResponse:
    """Flag a review for moderation."""
    try:
        flag = await service.flag_review(
            review_id=review_id,
            reporter_id=current_user.id,
            reason=request.reason,
            description=request.description,
        )
        return ReviewFlagResponse.model_validate(flag)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )


@router.get(
    "/statistics",
    response_model=ReviewStatsResponse,
    summary="Get review statistics",
    description="Get aggregated review statistics for salon, professional, or service.",
)
async def get_review_statistics(
    salon_id: Optional[int] = Query(None, description="Filter by salon ID"),
    professional_id: Optional[int] = Query(None, description="Filter by professional ID"),
    service_id: Optional[int] = Query(None, description="Filter by service ID"),
    service: ReviewService = Depends(get_review_service),
) -> ReviewStatsResponse:
    """Get review statistics."""
    try:
        stats = await service.get_rating_statistics(
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id,
        )
        return ReviewStatsResponse.model_validate(stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get(
    "/trends",
    response_model=ReviewTrendsResponse,
    summary="Get review trends",
    description="Get review trends over time for analysis.",
)
async def get_review_trends(
    salon_id: Optional[int] = Query(None, description="Filter by salon ID"),
    professional_id: Optional[int] = Query(None, description="Filter by professional ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days for trends"),
    service: ReviewService = Depends(get_review_service),
) -> ReviewTrendsResponse:
    """Get review trends over time."""
    try:
        trends = await service.get_review_trends(
            salon_id=salon_id,
            professional_id=professional_id,
            days=days,
        )
        return ReviewTrendsResponse.model_validate(trends)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trends: {str(e)}"
        )


# Admin endpoints for moderation
@router.post(
    "/{review_id}/moderate",
    response_model=ReviewModerationResponse,
    summary="Moderate a review",
    description="Moderate a review (admin only). Change status, add moderation notes.",
)
async def moderate_review(
    review_id: int = Path(..., description="Review ID"),
    request: ReviewModerationRequest = ...,
    current_user: User = Depends(require_admin),
    service: ReviewService = Depends(get_review_service),
) -> ReviewModerationResponse:
    """Moderate a review (admin only)."""
    try:
        review = await service.moderate_review(
            review_id=review_id,
            moderator_id=current_user.id,
            moderator_role=current_user.role,
            status=request.status,
            reason=request.reason,
            notes=request.notes,
        )
        return ReviewModerationResponse.model_validate(review)
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )


@router.get(
    "/moderation/pending",
    response_model=ReviewListResponse,
    summary="Get pending reviews",
    description="Get reviews pending moderation (admin only).",
)
async def get_pending_reviews(
    params: ModerationListParams = Depends(),
    current_user: User = Depends(require_admin),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    """Get reviews pending moderation."""
    try:
        reviews, total = await service.get_pending_reviews_for_moderation(
            limit=params.size,
            offset=(params.page - 1) * params.size,
        )

        return ReviewListResponse(
            reviews=[ReviewResponse.model_validate(r) for r in reviews],
            total=total,
            page=params.page,
            size=params.size,
            has_next=total > params.page * params.size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending reviews: {str(e)}"
        )


@router.get(
    "/moderation/flagged",
    response_model=ReviewListResponse,
    summary="Get flagged reviews",
    description="Get reviews flagged for moderation (admin only).",
)
async def get_flagged_reviews(
    params: ModerationListParams = Depends(),
    current_user: User = Depends(require_admin),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    """Get flagged reviews for moderation."""
    try:
        reviews, total = await service.get_flagged_reviews(
            limit=params.size,
            offset=(params.page - 1) * params.size,
        )

        return ReviewListResponse(
            reviews=[ReviewResponse.model_validate(r) for r in reviews],
            total=total,
            page=params.page,
            size=params.size,
            has_next=total > params.page * params.size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get flagged reviews: {str(e)}"
        )


@router.post(
    "/moderation/bulk",
    response_model=List[ReviewModerationResponse],
    summary="Bulk moderate reviews",
    description="Moderate multiple reviews at once (admin only).",
)
async def bulk_moderate_reviews(
    request: BulkModerationRequest,
    current_user: User = Depends(require_admin),
    service: ReviewService = Depends(get_review_service),
) -> List[ReviewModerationResponse]:
    """Bulk moderate multiple reviews."""
    try:
        reviews = await service.bulk_moderate_reviews(
            review_ids=request.review_ids,
            moderator_id=current_user.id,
            moderator_role=current_user.role,
            status=request.status,
            reason=request.reason,
            notes=request.notes,
        )
        return [ReviewModerationResponse.model_validate(r) for r in reviews]
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/flags/{flag_id}/resolve",
    response_model=ReviewFlagResponse,
    summary="Resolve a review flag",
    description="Resolve a review flag (admin only).",
)
async def resolve_review_flag(
    flag_id: int = Path(..., description="Flag ID"),
    notes: Optional[str] = Query(None, description="Resolution notes"),
    current_user: User = Depends(require_admin),
    service: ReviewService = Depends(get_review_service),
) -> ReviewFlagResponse:
    """Resolve a review flag."""
    try:
        flag = await service.resolve_flag(
            flag_id=flag_id,
            resolver_id=current_user.id,
            resolver_role=current_user.role,
            notes=notes,
        )
        return ReviewFlagResponse.model_validate(flag)
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flag not found"
        )


@router.get(
    "/recent",
    response_model=List[ReviewResponse],
    summary="Get recent reviews",
    description="Get recent reviews for dashboard display.",
)
async def get_recent_reviews(
    days: int = Query(7, ge=1, le=30, description="Number of days"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of reviews"),
    salon_id: Optional[int] = Query(None, description="Filter by salon ID"),
    service: ReviewService = Depends(get_review_service),
) -> List[ReviewResponse]:
    """Get recent reviews for dashboard."""
    try:
        reviews = await service.get_recent_reviews(
            days=days,
            limit=limit,
            salon_id=salon_id,
        )
        return [ReviewResponse.model_validate(r) for r in reviews]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent reviews: {str(e)}"
        )
