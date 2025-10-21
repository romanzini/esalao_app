"""Repository for managing review operations."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import and_, or_, desc, asc, func, case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from backend.app.db.models.review import Review, ReviewHelpfulness, ReviewFlag, ReviewStatus, ReviewModerationReason
from backend.app.db.models.booking import BookingStatus
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.booking import Booking


class ReviewRepository:
    """Repository for managing review data operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_review(
        self,
        booking_id: int,
        client_id: int,
        professional_id: int,
        salon_id: int,
        service_id: int,
        rating: int,
        title: Optional[str] = None,
        comment: Optional[str] = None,
        is_anonymous: bool = False,
    ) -> Review:
        """Create a new review."""
        review = Review(
            booking_id=booking_id,
            client_id=client_id,
            professional_id=professional_id,
            salon_id=salon_id,
            service_id=service_id,
            rating=rating,
            title=title,
            comment=comment,
            is_anonymous=is_anonymous,
            status=ReviewStatus.PENDING,
            is_verified=True,  # True because it's from actual booking
        )

        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    # Alias methods for compatibility with tests
    async def create(self, **kwargs) -> Review:
        """Alias for create_review."""
        return await self.create_review(**kwargs)

    async def get_by_id(self, review_id: int) -> Optional[Review]:
        """Alias for get_review_by_id."""
        return await self.get_review_by_id(review_id)

    async def get_by_booking_id(self, booking_id: int) -> Optional[Review]:
        """Alias for get_review_by_booking_id."""
        return await self.get_review_by_booking_id(booking_id)

    async def update(self, review_id: int, **kwargs) -> Optional[Review]:
        """Alias for update_review."""
        return await self.update_review(review_id=review_id, **kwargs)

    async def delete(self, review_id: int) -> bool:
        """Delete a review."""
        review = await self.get_review_by_id(review_id)
        if not review:
            return False

        await self.session.delete(review)
        await self.session.commit()
        return True

    async def count_reviews(self, **filters) -> int:
        """Count reviews with filters."""
        query = select(func.count(Review.id))

        # Apply filters
        if filters.get('salon_id'):
            query = query.where(Review.salon_id == filters['salon_id'])
        if filters.get('professional_id'):
            query = query.where(Review.professional_id == filters['professional_id'])
        if filters.get('status'):
            query = query.where(Review.status == filters['status'])
        if filters.get('rating'):
            query = query.where(Review.rating == filters['rating'])
        if filters.get('is_verified') is not None:
            query = query.where(Review.is_verified == filters['is_verified'])
        if filters.get('has_professional_response') is not None:
            query = query.where(Review.professional_response.isnot(None) if filters['has_professional_response'] else Review.professional_response.is_(None))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_rating_distribution(self, salon_id: Optional[int] = None, professional_id: Optional[int] = None) -> Dict[int, int]:
        """Get rating distribution for salon or professional."""
        query = select(Review.rating, func.count(Review.id).label('count')).where(
            Review.status == ReviewStatus.APPROVED
        ).group_by(Review.rating)

        if salon_id:
            query = query.where(Review.salon_id == salon_id)
        if professional_id:
            query = query.where(Review.professional_id == professional_id)

        result = await self.session.execute(query)
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        for rating, count in result.all():
            distribution[rating] = count

        return distribution

    async def get_helpfulness_stats(self, review_id: int) -> Dict[str, int]:
        """Get helpfulness statistics for a review."""
        query = select(
            func.sum(case((ReviewHelpfulness.is_helpful == True, 1), else_=0)).label('helpful_count'),
            func.sum(case((ReviewHelpfulness.is_helpful == False, 1), else_=0)).label('not_helpful_count'),
            func.count(ReviewHelpfulness.id).label('total_votes')
        ).where(ReviewHelpfulness.review_id == review_id)

        result = await self.session.execute(query)
        row = result.first()

        return {
            'helpful_count': row.helpful_count or 0,
            'not_helpful_count': row.not_helpful_count or 0,
            'total_votes': row.total_votes or 0
        }

    async def get_flags_for_review(self, review_id: int) -> List[ReviewFlag]:
        """Get all flags for a review."""
        query = select(ReviewFlag).where(
            ReviewFlag.review_id == review_id
        ).options(
            selectinload(ReviewFlag.flagged_by)
        ).order_by(ReviewFlag.created_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_unresolved_flags(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[ReviewFlag]:
        """Get unresolved flags."""
        query = select(ReviewFlag).where(
            ReviewFlag.is_resolved == False
        ).options(
            selectinload(ReviewFlag.review),
            selectinload(ReviewFlag.flagged_by)
        ).order_by(
            ReviewFlag.created_at.desc()
        ).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_review_by_id(self, review_id: int) -> Optional[Review]:
        """Get review by ID with all relationships."""
        result = await self.session.execute(
            select(Review)
            .options(
                selectinload(Review.client),
                selectinload(Review.professional),
                selectinload(Review.salon),
                selectinload(Review.service),
                selectinload(Review.booking),
                selectinload(Review.moderator),
                selectinload(Review.responder),
                selectinload(Review.helpfulness_votes),
                selectinload(Review.flags),
            )
            .where(Review.id == review_id)
        )
        return result.scalar_one_or_none()

    async def get_review_by_booking_id(self, booking_id: int) -> Optional[Review]:
        """Get review by booking ID."""
        result = await self.session.execute(
            select(Review)
            .options(selectinload(Review.client))
            .where(Review.booking_id == booking_id)
        )
        return result.scalar_one_or_none()

    async def can_create_review(self, booking_id: int, client_id: int) -> bool:
        """Check if a review can be created for this booking."""
        # Check if booking exists and is completed
        booking_result = await self.session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.id == booking_id,
                    Booking.client_id == client_id,
                    Booking.status == BookingStatus.COMPLETED
                )
            )
        )
        booking = booking_result.scalar_one_or_none()
        if not booking:
            return False

        # Check if review already exists
        existing_review = await self.get_review_by_booking_id(booking_id)
        return existing_review is None

    async def update_review(
        self,
        review_id: int,
        client_id: int,
        rating: Optional[int] = None,
        title: Optional[str] = None,
        comment: Optional[str] = None,
        is_anonymous: Optional[bool] = None,
    ) -> Optional[Review]:
        """Update review if within edit window and by original author."""
        review = await self.get_review_by_id(review_id)

        if not review or review.client_id != client_id:
            return None

        # Check if still within edit window (24 hours)
        if not review.can_be_edited:
            return None

        if rating is not None:
            review.rating = rating
        if title is not None:
            review.title = title
        if comment is not None:
            review.comment = comment
        if is_anonymous is not None:
            review.is_anonymous = is_anonymous

        review.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        return review

    async def moderate_review(
        self,
        review_id: int,
        moderator_id: int,
        status: ReviewStatus,
        reason: Optional[ReviewModerationReason] = None,
        notes: Optional[str] = None,
    ) -> Optional[Review]:
        """Moderate a review (admin only)."""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None

        review.status = status
        review.moderated_by = moderator_id
        review.moderation_reason = reason
        review.moderation_notes = notes
        review.moderated_at = datetime.now(timezone.utc)

        await self.session.flush()
        return review

    async def add_professional_response(
        self,
        review_id: int,
        responder_id: int,
        response_text: str,
    ) -> Optional[Review]:
        """Add professional/salon response to review."""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None

        review.response_text = response_text
        review.response_by = responder_id
        review.response_at = datetime.now(timezone.utc)

        await self.session.flush()
        return review

    async def vote_helpfulness(
        self,
        review_id: int,
        user_id: int,
        is_helpful: bool,
    ) -> bool:
        """Vote on review helpfulness."""
        # Check if user already voted
        existing_vote = await self.session.execute(
            select(ReviewHelpfulness)
            .where(
                and_(
                    ReviewHelpfulness.review_id == review_id,
                    ReviewHelpfulness.user_id == user_id
                )
            )
        )
        vote = existing_vote.scalar_one_or_none()

        if vote:
            # Update existing vote
            old_helpful = vote.is_helpful
            vote.is_helpful = is_helpful

            # Update review counters
            review = await self.get_review_by_id(review_id)
            if review:
                if old_helpful and not is_helpful:
                    review.helpful_count -= 1
                    review.not_helpful_count += 1
                elif not old_helpful and is_helpful:
                    review.helpful_count += 1
                    review.not_helpful_count -= 1
        else:
            # Create new vote
            vote = ReviewHelpfulness(
                review_id=review_id,
                user_id=user_id,
                is_helpful=is_helpful,
            )
            self.session.add(vote)

            # Update review counters
            review = await self.get_review_by_id(review_id)
            if review:
                if is_helpful:
                    review.helpful_count += 1
                else:
                    review.not_helpful_count += 1

        await self.session.flush()
        return True

    async def flag_review(
        self,
        review_id: int,
        reporter_id: int,
        reason: ReviewModerationReason,
        description: Optional[str] = None,
    ) -> ReviewFlag:
        """Flag a review for moderation."""
        # Check if user already flagged this review
        existing_flag = await self.session.execute(
            select(ReviewFlag)
            .where(
                and_(
                    ReviewFlag.review_id == review_id,
                    ReviewFlag.reporter_id == reporter_id
                )
            )
        )
        flag = existing_flag.scalar_one_or_none()

        if flag:
            return flag

        flag = ReviewFlag(
            review_id=review_id,
            reporter_id=reporter_id,
            reason=reason,
            description=description,
        )

        self.session.add(flag)

        # Auto-flag review if it gets multiple reports
        flag_count = await self.session.execute(
            select(func.count(ReviewFlag.id))
            .where(
                and_(
                    ReviewFlag.review_id == review_id,
                    ReviewFlag.is_resolved == False
                )
            )
        )
        count = flag_count.scalar()

        if count >= 3:  # Auto-flag after 3 reports
            review = await self.get_review_by_id(review_id)
            if review and review.status != ReviewStatus.FLAGGED:
                review.status = ReviewStatus.FLAGGED

        await self.session.flush()
        return flag

    async def resolve_flag(
        self,
        flag_id: int,
        resolver_id: int,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ReviewFlag]:
        """Resolve a review flag."""
        result = await self.session.execute(
            select(ReviewFlag)
            .where(ReviewFlag.id == flag_id)
        )
        flag = result.scalar_one_or_none()

        if not flag:
            return None

        flag.is_resolved = True
        flag.resolved_by = resolver_id
        flag.resolution_notes = resolution_notes
        flag.resolved_at = datetime.now(timezone.utc)

        await self.session.flush()
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
        query = select(Review).options(
            selectinload(Review.client),
            selectinload(Review.professional),
            selectinload(Review.salon),
            selectinload(Review.service),
        )

        # Apply filters
        conditions = []

        if salon_id is not None:
            conditions.append(Review.salon_id == salon_id)
        if professional_id is not None:
            conditions.append(Review.professional_id == professional_id)
        if service_id is not None:
            conditions.append(Review.service_id == service_id)
        if client_id is not None:
            conditions.append(Review.client_id == client_id)
        if status is not None:
            conditions.append(Review.status == status)
        if min_rating is not None:
            conditions.append(Review.rating >= min_rating)
        if max_rating is not None:
            conditions.append(Review.rating <= max_rating)
        if with_comments_only:
            conditions.append(Review.comment.isnot(None))
            conditions.append(Review.comment != "")
        if verified_only:
            conditions.append(Review.is_verified == True)

        if conditions:
            query = query.where(and_(*conditions))

        # Apply sorting
        sort_column = getattr(Review, sort_by, Review.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Get total count
        count_query = select(func.count(Review.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        reviews = result.scalars().all()

        return list(reviews), total

    async def get_rating_statistics(
        self,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get rating statistics for salon, professional, or service."""
        query = select(
            func.count(Review.id).label("total_reviews"),
            func.avg(Review.rating).label("average_rating"),
            func.count(case((Review.rating == 1, 1))).label("rating_1"),
            func.count(case((Review.rating == 2, 1))).label("rating_2"),
            func.count(case((Review.rating == 3, 1))).label("rating_3"),
            func.count(case((Review.rating == 4, 1))).label("rating_4"),
            func.count(case((Review.rating == 5, 1))).label("rating_5"),
        ).where(Review.status == ReviewStatus.APPROVED)

        conditions = []
        if salon_id is not None:
            conditions.append(Review.salon_id == salon_id)
        if professional_id is not None:
            conditions.append(Review.professional_id == professional_id)
        if service_id is not None:
            conditions.append(Review.service_id == service_id)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        stats = result.first()

        return {
            "total_reviews": stats.total_reviews or 0,
            "average_rating": float(stats.average_rating or 0),
            "rating_distribution": {
                "1": stats.rating_1 or 0,
                "2": stats.rating_2 or 0,
                "3": stats.rating_3 or 0,
                "4": stats.rating_4 or 0,
                "5": stats.rating_5 or 0,
            }
        }

    async def get_pending_reviews_for_moderation(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Review], int]:
        """Get reviews pending moderation."""
        return await self.list_reviews(
            status=ReviewStatus.PENDING,
            limit=limit,
            offset=offset,
            sort_by="created_at",
            sort_order="asc",
        )

    async def get_flagged_reviews(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Review], int]:
        """Get flagged reviews for moderation."""
        return await self.list_reviews(
            status=ReviewStatus.FLAGGED,
            limit=limit,
            offset=offset,
            sort_by="created_at",
            sort_order="asc",
        )

    async def bulk_moderate_reviews(
        self,
        review_ids: List[int],
        moderator_id: int,
        status: ReviewStatus,
        reason: Optional[ReviewModerationReason] = None,
        notes: Optional[str] = None,
    ) -> List[Review]:
        """Bulk moderate multiple reviews."""
        reviews = []

        for review_id in review_ids:
            review = await self.moderate_review(
                review_id=review_id,
                moderator_id=moderator_id,
                status=status,
                reason=reason,
                notes=notes,
            )
            if review:
                reviews.append(review)

        return reviews

    async def get_recent_reviews(
        self,
        days: int = 7,
        limit: int = 10,
        salon_id: Optional[int] = None,
    ) -> List[Review]:
        """Get recent reviews for dashboard."""
        since_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(Review).options(
            selectinload(Review.client),
            selectinload(Review.professional),
            selectinload(Review.salon),
            selectinload(Review.service),
        ).where(
            and_(
                Review.created_at >= since_date,
                Review.status == ReviewStatus.APPROVED
            )
        )

        if salon_id:
            query = query.where(Review.salon_id == salon_id)

        query = query.order_by(desc(Review.created_at)).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
