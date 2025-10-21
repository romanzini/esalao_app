"""Review service for managing customer reviews and ratings."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from backend.app.db.repositories.review import ReviewRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.loyalty import LoyaltyRepository
from backend.app.db.models.review import Review, ReviewFlag, ReviewStatus, ReviewModerationReason
from backend.app.db.models.user import UserRole
from backend.app.db.models.loyalty import PointEarnReason
from backend.app.core.exceptions import ValidationError, AuthorizationError, NotFoundError


class ReviewService:
    """Service for managing review operations."""

    def __init__(
        self,
        review_repo: ReviewRepository,
        booking_repo: BookingRepository,
        loyalty_repo: Optional[LoyaltyRepository] = None,
    ):
        self.review_repo = review_repo
        self.booking_repo = booking_repo
        self.loyalty_repo = loyalty_repo

    async def create_review(
        self,
        booking_id: int,
        client_id: int,
        rating: int,
        title: Optional[str] = None,
        comment: Optional[str] = None,
        is_anonymous: bool = False,
    ) -> Review:
        """Create a new review for a completed booking."""
        # Validate rating
        if not (1 <= rating <= 5):
            raise ValidationError("Rating must be between 1 and 5")

        # Check if review can be created
        if not await self.review_repo.can_create_review(booking_id, client_id):
            raise ValidationError(
                "Cannot create review: booking not found, not completed, "
                "not owned by client, or review already exists"
            )

        # Get booking details for review relationships
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise NotFoundError("Booking not found")

        # Validate title and comment length
        if title and len(title) > 200:
            raise ValidationError("Title must not exceed 200 characters")
        if comment and len(comment) > 2000:
            raise ValidationError("Comment must not exceed 2000 characters")

        # Create the review
        review = await self.review_repo.create_review(
            booking_id=booking_id,
            client_id=client_id,
            professional_id=booking.professional_id,
            salon_id=booking.salon_id,
            service_id=booking.service_id,
            rating=rating,
            title=title,
            comment=comment,
            is_anonymous=is_anonymous,
        )

        # Award loyalty points for review
        if self.loyalty_repo:
            try:
                await self.loyalty_repo.add_points(
                    user_id=client_id,
                    points=10,  # Standard points for review
                    description=f"Review for booking #{booking_id}",
                    earn_reason=PointEarnReason.REVIEW_SUBMITTED,
                    related_booking_id=booking_id,
                )
            except Exception:
                # Don't fail review creation if loyalty points fail
                pass

        return review

    async def update_review(
        self,
        review_id: int,
        client_id: int,
        rating: Optional[int] = None,
        title: Optional[str] = None,
        comment: Optional[str] = None,
        is_anonymous: Optional[bool] = None,
    ) -> Review:
        """Update a review within the edit window."""
        # Validate rating if provided
        if rating is not None and not (1 <= rating <= 5):
            raise ValidationError("Rating must be between 1 and 5")

        # Validate title and comment length
        if title and len(title) > 200:
            raise ValidationError("Title must not exceed 200 characters")
        if comment and len(comment) > 2000:
            raise ValidationError("Comment must not exceed 2000 characters")

        review = await self.review_repo.update_review(
            review_id=review_id,
            client_id=client_id,
            rating=rating,
            title=title,
            comment=comment,
            is_anonymous=is_anonymous,
        )

        if not review:
            raise ValidationError(
                "Cannot update review: not found, not owned by client, "
                "or edit window expired (24 hours)"
            )

        return review

    async def moderate_review(
        self,
        review_id: int,
        moderator_id: int,
        moderator_role: UserRole,
        status: ReviewStatus,
        reason: Optional[ReviewModerationReason] = None,
        notes: Optional[str] = None,
    ) -> Review:
        """Moderate a review (admin only)."""
        if moderator_role != UserRole.ADMIN:
            raise AuthorizationError("Only admins can moderate reviews")

        review = await self.review_repo.moderate_review(
            review_id=review_id,
            moderator_id=moderator_id,
            status=status,
            reason=reason,
            notes=notes,
        )

        if not review:
            raise NotFoundError("Review not found")

        return review

    async def add_professional_response(
        self,
        review_id: int,
        responder_id: int,
        responder_role: UserRole,
        response_text: str,
    ) -> Review:
        """Add professional/salon response to review."""
        if responder_role not in [UserRole.PROFESSIONAL, UserRole.SALON_OWNER]:
            raise AuthorizationError(
                "Only professionals and salon owners can respond to reviews"
            )

        if len(response_text) > 1000:
            raise ValidationError("Response must not exceed 1000 characters")

        # Get the review to validate responder permissions
        review = await self.review_repo.get_review_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")

        # Check if responder is the professional or salon owner
        if (responder_role == UserRole.PROFESSIONAL and
            review.professional_id != responder_id):
            raise AuthorizationError("Can only respond to your own reviews")

        # For salon owners, we'd need additional validation to check
        # if they own the salon (requires salon repository)

        response = await self.review_repo.add_professional_response(
            review_id=review_id,
            responder_id=responder_id,
            response_text=response_text,
        )

        if not response:
            raise NotFoundError("Review not found")

        return response

    async def vote_helpfulness(
        self,
        review_id: int,
        user_id: int,
        is_helpful: bool,
    ) -> bool:
        """Vote on review helpfulness."""
        # Check if review exists
        review = await self.review_repo.get_review_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")

        # Don't allow voting on own review
        if review.client_id == user_id:
            raise ValidationError("Cannot vote on your own review")

        return await self.review_repo.vote_helpfulness(
            review_id=review_id,
            user_id=user_id,
            is_helpful=is_helpful,
        )

    async def flag_review(
        self,
        review_id: int,
        reporter_id: int,
        reason: ReviewModerationReason,
        description: Optional[str] = None,
    ) -> ReviewFlag:
        """Flag a review for moderation."""
        # Check if review exists
        review = await self.review_repo.get_review_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")

        # Don't allow flagging own review
        if review.client_id == reporter_id:
            raise ValidationError("Cannot flag your own review")

        if description and len(description) > 500:
            raise ValidationError("Description must not exceed 500 characters")

        return await self.review_repo.flag_review(
            review_id=review_id,
            reporter_id=reporter_id,
            reason=reason,
            description=description,
        )

    async def resolve_flag(
        self,
        flag_id: int,
        resolver_id: int,
        resolver_role: UserRole,
        notes: Optional[str] = None,
    ) -> ReviewFlag:
        """Resolve a review flag (admin only)."""
        if resolver_role != UserRole.ADMIN:
            raise AuthorizationError("Only admins can resolve flags")

        flag = await self.review_repo.resolve_flag(
            flag_id=flag_id,
            resolver_id=resolver_id,
            notes=notes,
        )

        if not flag:
            raise NotFoundError("Flag not found")

        return flag

    async def list_reviews(
        self,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
        client_id: Optional[int] = None,
        status: Optional[ReviewStatus] = None,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        with_comments_only: bool = False,
        verified_only: bool = False,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Review], int]:
        """List reviews with filtering and pagination."""
        return await self.review_repo.list_reviews(
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id,
            client_id=client_id,
            status=status,
            min_rating=min_rating,
            max_rating=max_rating,
            with_comments_only=with_comments_only,
            verified_only=verified_only,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_review_by_id(self, review_id: int) -> Optional[Review]:
        """Get review by ID."""
        return await self.review_repo.get_review_by_id(review_id)

    async def get_review_by_booking_id(self, booking_id: int) -> Optional[Review]:
        """Get review by booking ID."""
        return await self.review_repo.get_review_by_booking_id(booking_id)

    async def get_rating_statistics(
        self,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get rating statistics."""
        return await self.review_repo.get_rating_statistics(
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id,
        )

    async def get_pending_reviews_for_moderation(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Review], int]:
        """Get reviews pending moderation (admin only)."""
        return await self.review_repo.get_pending_reviews_for_moderation(
            limit=limit,
            offset=offset,
        )

    async def get_flagged_reviews(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Review], int]:
        """Get flagged reviews for moderation (admin only)."""
        return await self.review_repo.get_flagged_reviews(
            limit=limit,
            offset=offset,
        )

    async def bulk_moderate_reviews(
        self,
        review_ids: List[int],
        moderator_id: int,
        moderator_role: UserRole,
        status: ReviewStatus,
        reason: Optional[ReviewModerationReason] = None,
        notes: Optional[str] = None,
    ) -> List[Review]:
        """Bulk moderate multiple reviews (admin only)."""
        if moderator_role != UserRole.ADMIN:
            raise AuthorizationError("Only admins can moderate reviews")

        return await self.review_repo.bulk_moderate_reviews(
            review_ids=review_ids,
            moderator_id=moderator_id,
            status=status,
            reason=reason,
            notes=notes,
        )

    async def get_recent_reviews(
        self,
        days: int = 7,
        limit: int = 10,
        salon_id: Optional[int] = None,
    ) -> List[Review]:
        """Get recent reviews for dashboard."""
        return await self.review_repo.get_recent_reviews(
            days=days,
            limit=limit,
            salon_id=salon_id,
        )

    async def auto_approve_review(self, review_id: int) -> Optional[Review]:
        """Auto-approve review if it passes content filters."""
        review = await self.review_repo.get_review_by_id(review_id)
        if not review:
            return None

        # Simple content filtering (can be enhanced with ML/AI)
        auto_approve = True

        # Check for profanity or inappropriate content
        if review.comment:
            inappropriate_words = [
                "spam", "fake", "scam", "terrible", "worst", "awful",
                # Add more words as needed
            ]
            comment_lower = review.comment.lower()
            for word in inappropriate_words:
                if word in comment_lower:
                    auto_approve = False
                    break

        # Auto-approve if rating is 4-5 and no inappropriate content
        if auto_approve and review.rating >= 4:
            return await self.review_repo.moderate_review(
                review_id=review_id,
                moderator_id=None,  # System auto-approval
                status=ReviewStatus.APPROVED,
                reason=None,
                notes="Auto-approved by system",
            )

        return review

    async def calculate_overall_rating(
        self,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
    ) -> float:
        """Calculate overall rating average."""
        stats = await self.get_rating_statistics(
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id,
        )
        return stats.get("average_rating", 0.0)

    async def get_review_trends(
        self,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get review trends over time."""
        # This would require more complex queries
        # For now, return basic statistics
        stats = await self.get_rating_statistics(
            salon_id=salon_id,
            professional_id=professional_id,
        )

        recent_reviews = await self.get_recent_reviews(
            days=days,
            limit=100,
            salon_id=salon_id,
        )

        return {
            "current_stats": stats,
            "recent_count": len(recent_reviews),
            "recent_average": (
                sum(r.rating for r in recent_reviews) / len(recent_reviews)
                if recent_reviews else 0
            ),
        }
