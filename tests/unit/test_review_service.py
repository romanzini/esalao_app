"""Unit tests for review service."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from backend.app.services.review import ReviewService
from backend.app.db.repositories.review import ReviewRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.loyalty import LoyaltyRepository
from backend.app.db.models.review import (
    Review, ReviewStatus, ReviewModerationReason, ReviewHelpfulness, ReviewFlag
)
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.core.exceptions import ValidationError, PermissionError, NotFoundError


class TestReviewService:
    """Test ReviewService functionality."""

    @pytest.fixture
    def mock_review_repo(self):
        """Create a mock review repository."""
        return AsyncMock(spec=ReviewRepository)

    @pytest.fixture
    def mock_booking_repo(self):
        """Create a mock booking repository."""
        return AsyncMock(spec=BookingRepository)

    @pytest.fixture
    def mock_loyalty_repo(self):
        """Create a mock loyalty repository."""
        return AsyncMock(spec=LoyaltyRepository)

    @pytest.fixture
    def service(self, mock_review_repo, mock_booking_repo, mock_loyalty_repo):
        """Create ReviewService instance with mocked dependencies."""
        return ReviewService(mock_review_repo, mock_booking_repo, mock_loyalty_repo)

    @pytest.fixture
    def sample_booking(self):
        """Create a sample completed booking."""
        return Booking(
            id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            status=BookingStatus.COMPLETED,
            scheduled_for=datetime.utcnow() - timedelta(days=1),
            completed_at=datetime.utcnow() - timedelta(hours=1),
        )

    @pytest.fixture
    def sample_review(self):
        """Create a sample review."""
        return Review(
            id=1,
            booking_id=1,
            client_id=1,
            rating=5,
            title="Great service!",
            comment="Very professional and clean.",
            status=ReviewStatus.APPROVED,
            created_at=datetime.utcnow(),
        )

    async def test_create_review_success(self, service, mock_review_repo, mock_booking_repo, mock_loyalty_repo, sample_booking):
        """Test successfully creating a review."""
        # Mock booking exists and is completed
        mock_booking_repo.get_by_id.return_value = sample_booking

        # Mock no existing review
        mock_review_repo.get_by_booking_id.return_value = None

        # Mock review creation
        created_review = Review(
            id=1,
            booking_id=1,
            client_id=1,
            rating=5,
            title="Great service!",
            comment="Very professional and clean.",
            status=ReviewStatus.APPROVED,  # Auto-approved
        )
        mock_review_repo.create.return_value = created_review

        # Mock loyalty points award
        mock_loyalty_repo.award_points.return_value = None

        result = await service.create_review(
            booking_id=1,
            client_id=1,
            rating=5,
            title="Great service!",
            comment="Very professional and clean."
        )

        # Verify repository calls
        mock_booking_repo.get_by_id.assert_called_once_with(1)
        mock_review_repo.get_by_booking_id.assert_called_once_with(1)
        mock_review_repo.create.assert_called_once()

        # Verify loyalty points were awarded
        mock_loyalty_repo.award_points.assert_called_once_with(
            user_id=1,
            points=10,  # Default points for review
            activity_type="review_created",
            reference_id=1
        )

        assert result == created_review

    async def test_create_review_booking_not_found(self, service, mock_booking_repo):
        """Test creating review for non-existent booking."""
        # Mock booking not found
        mock_booking_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Booking not found"):
            await service.create_review(
                booking_id=999,
                client_id=1,
                rating=5
            )

    async def test_create_review_not_completed_booking(self, service, mock_booking_repo):
        """Test creating review for non-completed booking."""
        # Mock booking exists but not completed
        booking = Booking(
            id=1,
            client_id=1,
            status=BookingStatus.CONFIRMED,
        )
        mock_booking_repo.get_by_id.return_value = booking

        with pytest.raises(ValidationError, match="Can only review completed bookings"):
            await service.create_review(
                booking_id=1,
                client_id=1,
                rating=5
            )

    async def test_create_review_not_client(self, service, mock_booking_repo, sample_booking):
        """Test creating review by someone who is not the client."""
        # Mock booking exists and is completed
        mock_booking_repo.get_by_id.return_value = sample_booking

        with pytest.raises(PermissionError, match="Only the client can review their booking"):
            await service.create_review(
                booking_id=1,
                client_id=999,  # Different client
                rating=5
            )

    async def test_create_review_already_exists(self, service, mock_booking_repo, mock_review_repo, sample_booking, sample_review):
        """Test creating review when one already exists."""
        # Mock booking exists and is completed
        mock_booking_repo.get_by_id.return_value = sample_booking

        # Mock existing review
        mock_review_repo.get_by_booking_id.return_value = sample_review

        with pytest.raises(ValidationError, match="Review already exists for this booking"):
            await service.create_review(
                booking_id=1,
                client_id=1,
                rating=5
            )

    async def test_create_review_invalid_rating(self, service, mock_booking_repo, mock_review_repo, sample_booking):
        """Test creating review with invalid rating."""
        # Mock booking exists and is completed
        mock_booking_repo.get_by_id.return_value = sample_booking
        mock_review_repo.get_by_booking_id.return_value = None

        # Test invalid ratings
        invalid_ratings = [0, 6, -1, 10]
        for rating in invalid_ratings:
            with pytest.raises(ValidationError, match="Rating must be between 1 and 5"):
                await service.create_review(
                    booking_id=1,
                    client_id=1,
                    rating=rating
                )

    async def test_update_review_success(self, service, mock_review_repo, sample_review):
        """Test successfully updating a review."""
        # Mock review exists and is recent
        sample_review.created_at = datetime.utcnow() - timedelta(hours=1)  # Recent
        mock_review_repo.get_by_id.return_value = sample_review

        # Mock update
        updated_review = sample_review
        updated_review.rating = 4
        updated_review.title = "Updated title"
        mock_review_repo.update.return_value = updated_review

        result = await service.update_review(
            review_id=1,
            client_id=1,
            rating=4,
            title="Updated title"
        )

        # Verify repository calls
        mock_review_repo.get_by_id.assert_called_once_with(1)
        mock_review_repo.update.assert_called_once()

        assert result == updated_review

    async def test_update_review_not_found(self, service, mock_review_repo):
        """Test updating non-existent review."""
        # Mock review not found
        mock_review_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="Review not found"):
            await service.update_review(
                review_id=999,
                client_id=1,
                rating=4
            )

    async def test_update_review_not_client(self, service, mock_review_repo, sample_review):
        """Test updating review by someone who is not the client."""
        # Mock review exists
        mock_review_repo.get_by_id.return_value = sample_review

        with pytest.raises(PermissionError, match="Only the client can update their review"):
            await service.update_review(
                review_id=1,
                client_id=999,  # Different client
                rating=4
            )

    async def test_update_review_too_old(self, service, mock_review_repo, sample_review):
        """Test updating review that is too old."""
        # Mock review exists but is old
        sample_review.created_at = datetime.utcnow() - timedelta(days=2)  # Too old
        mock_review_repo.get_by_id.return_value = sample_review

        with pytest.raises(ValidationError, match="Reviews can only be updated within 24 hours"):
            await service.update_review(
                review_id=1,
                client_id=1,
                rating=4
            )

    async def test_moderate_review_success(self, service, mock_review_repo, sample_review):
        """Test successfully moderating a review."""
        # Mock review exists
        mock_review_repo.get_by_id.return_value = sample_review

        # Mock update
        moderated_review = sample_review
        moderated_review.status = ReviewStatus.REJECTED
        moderated_review.moderation_reason = ReviewModerationReason.SPAM
        mock_review_repo.update.return_value = moderated_review

        result = await service.moderate_review(
            review_id=1,
            moderator_id=2,
            moderator_role=UserRole.ADMIN,
            status=ReviewStatus.REJECTED,
            reason=ReviewModerationReason.SPAM,
            notes="Detected as spam"
        )

        # Verify repository calls
        mock_review_repo.get_by_id.assert_called_once_with(1)
        mock_review_repo.update.assert_called_once()

        assert result == moderated_review

    async def test_moderate_review_invalid_moderator(self, service, mock_review_repo, sample_review):
        """Test moderating review with invalid moderator role."""
        # Mock review exists
        mock_review_repo.get_by_id.return_value = sample_review

        with pytest.raises(PermissionError, match="Only admins can moderate reviews"):
            await service.moderate_review(
                review_id=1,
                moderator_id=2,
                moderator_role=UserRole.CLIENT,  # Invalid role
                status=ReviewStatus.REJECTED
            )

    async def test_add_professional_response_success(self, service, mock_review_repo, sample_review):
        """Test successfully adding professional response."""
        # Mock review exists and is approved
        sample_review.status = ReviewStatus.APPROVED
        mock_review_repo.get_by_id.return_value = sample_review

        # Mock update
        responded_review = sample_review
        responded_review.professional_response = "Thank you for your feedback!"
        mock_review_repo.update.return_value = responded_review

        result = await service.add_professional_response(
            review_id=1,
            responder_id=2,
            responder_role=UserRole.PROFESSIONAL,
            response_text="Thank you for your feedback!"
        )

        # Verify repository calls
        mock_review_repo.get_by_id.assert_called_once_with(1)
        mock_review_repo.update.assert_called_once()

        assert result == responded_review

    async def test_add_professional_response_not_approved(self, service, mock_review_repo, sample_review):
        """Test adding response to non-approved review."""
        # Mock review exists but is not approved
        sample_review.status = ReviewStatus.PENDING
        mock_review_repo.get_by_id.return_value = sample_review

        with pytest.raises(ValidationError, match="Can only respond to approved reviews"):
            await service.add_professional_response(
                review_id=1,
                responder_id=2,
                responder_role=UserRole.PROFESSIONAL,
                response_text="Thank you!"
            )

    async def test_add_professional_response_invalid_role(self, service, mock_review_repo, sample_review):
        """Test adding response with invalid role."""
        # Mock review exists and is approved
        sample_review.status = ReviewStatus.APPROVED
        mock_review_repo.get_by_id.return_value = sample_review

        with pytest.raises(PermissionError, match="Only professionals and salon owners can respond"):
            await service.add_professional_response(
                review_id=1,
                responder_id=2,
                responder_role=UserRole.CLIENT,  # Invalid role
                response_text="Thank you!"
            )

    async def test_vote_helpfulness_success(self, service, mock_review_repo, sample_review):
        """Test successfully voting on review helpfulness."""
        # Mock review exists
        mock_review_repo.get_by_id.return_value = sample_review

        # Mock vote creation
        mock_review_repo.vote_helpfulness.return_value = None

        await service.vote_helpfulness(
            review_id=1,
            user_id=2,
            is_helpful=True
        )

        # Verify repository calls
        mock_review_repo.get_by_id.assert_called_once_with(1)
        mock_review_repo.vote_helpfulness.assert_called_once_with(
            review_id=1,
            user_id=2,
            is_helpful=True
        )

    async def test_vote_helpfulness_own_review(self, service, mock_review_repo, sample_review):
        """Test voting on own review (should be prevented)."""
        # Mock review exists
        mock_review_repo.get_by_id.return_value = sample_review

        with pytest.raises(ValidationError, match="Cannot vote on your own review"):
            await service.vote_helpfulness(
                review_id=1,
                user_id=1,  # Same as review client_id
                is_helpful=True
            )

    async def test_flag_review_success(self, service, mock_review_repo, sample_review):
        """Test successfully flagging a review."""
        # Mock review exists
        mock_review_repo.get_by_id.return_value = sample_review

        # Mock flag creation
        created_flag = ReviewFlag(
            id=1,
            review_id=1,
            reporter_id=2,
            reason="spam",
            description="This looks like spam"
        )
        mock_review_repo.flag_review.return_value = created_flag

        result = await service.flag_review(
            review_id=1,
            reporter_id=2,
            reason="spam",
            description="This looks like spam"
        )

        # Verify repository calls
        mock_review_repo.get_by_id.assert_called_once_with(1)
        mock_review_repo.flag_review.assert_called_once()

        assert result == created_flag

    async def test_flag_own_review(self, service, mock_review_repo, sample_review):
        """Test flagging own review (should be prevented)."""
        # Mock review exists
        mock_review_repo.get_by_id.return_value = sample_review

        with pytest.raises(ValidationError, match="Cannot flag your own review"):
            await service.flag_review(
                review_id=1,
                reporter_id=1,  # Same as review client_id
                reason="spam"
            )

    async def test_get_rating_statistics(self, service, mock_review_repo):
        """Test getting rating statistics."""
        # Mock statistics
        mock_stats = {
            "average_rating": 4.5,
            "total_reviews": 100,
            "rating_distribution": {5: 50, 4: 30, 3: 15, 2: 3, 1: 2}
        }
        mock_review_repo.get_rating_statistics.return_value = mock_stats

        result = await service.get_rating_statistics(salon_id=1)

        # Verify repository call
        mock_review_repo.get_rating_statistics.assert_called_once_with(
            salon_id=1,
            professional_id=None,
            service_id=None
        )

        assert result == mock_stats

    async def test_list_reviews(self, service, mock_review_repo, sample_review):
        """Test listing reviews with filters."""
        # Mock reviews and count
        mock_reviews = [sample_review]
        mock_count = 1
        mock_review_repo.list_reviews.return_value = mock_reviews
        mock_review_repo.count_reviews.return_value = mock_count

        reviews, total = await service.list_reviews(
            salon_id=1,
            status=ReviewStatus.APPROVED,
            limit=10,
            offset=0
        )

        # Verify repository calls
        mock_review_repo.list_reviews.assert_called_once()
        mock_review_repo.count_reviews.assert_called_once()

        assert reviews == mock_reviews
        assert total == mock_count

    async def test_bulk_moderate_reviews(self, service, mock_review_repo, sample_review):
        """Test bulk moderating reviews."""
        # Mock reviews
        mock_reviews = [sample_review for _ in range(3)]
        mock_review_repo.bulk_moderate_reviews.return_value = mock_reviews

        result = await service.bulk_moderate_reviews(
            review_ids=[1, 2, 3],
            moderator_id=1,
            moderator_role=UserRole.ADMIN,
            status=ReviewStatus.APPROVED
        )

        # Verify repository call
        mock_review_repo.bulk_moderate_reviews.assert_called_once()

        assert result == mock_reviews

    async def test_bulk_moderate_invalid_moderator(self, service, mock_review_repo):
        """Test bulk moderating with invalid moderator role."""
        with pytest.raises(PermissionError, match="Only admins can moderate reviews"):
            await service.bulk_moderate_reviews(
                review_ids=[1, 2, 3],
                moderator_id=1,
                moderator_role=UserRole.CLIENT,  # Invalid role
                status=ReviewStatus.APPROVED
            )

    async def test_auto_approve_high_rating(self, service, mock_review_repo, mock_booking_repo, mock_loyalty_repo, sample_booking):
        """Test auto-approval of high rating reviews."""
        # Mock booking exists and is completed
        mock_booking_repo.get_by_id.return_value = sample_booking

        # Mock no existing review
        mock_review_repo.get_by_booking_id.return_value = None

        # Mock review creation with high rating
        created_review = Review(
            id=1,
            booking_id=1,
            client_id=1,
            rating=5,  # High rating
            status=ReviewStatus.APPROVED,  # Should be auto-approved
        )
        mock_review_repo.create.return_value = created_review

        # Mock loyalty points award
        mock_loyalty_repo.award_points.return_value = None

        result = await service.create_review(
            booking_id=1,
            client_id=1,
            rating=5  # High rating should auto-approve
        )

        # Verify auto-approval
        assert result.status == ReviewStatus.APPROVED

    async def test_pending_status_low_rating(self, service, mock_review_repo, mock_booking_repo, mock_loyalty_repo, sample_booking):
        """Test that low rating reviews are set to pending."""
        # Mock booking exists and is completed
        mock_booking_repo.get_by_id.return_value = sample_booking

        # Mock no existing review
        mock_review_repo.get_by_booking_id.return_value = None

        # Mock review creation with low rating
        created_review = Review(
            id=1,
            booking_id=1,
            client_id=1,
            rating=2,  # Low rating
            status=ReviewStatus.PENDING,  # Should be pending
        )
        mock_review_repo.create.return_value = created_review

        # Mock loyalty points award
        mock_loyalty_repo.award_points.return_value = None

        result = await service.create_review(
            booking_id=1,
            client_id=1,
            rating=2  # Low rating should require moderation
        )

        # Verify pending status
        assert result.status == ReviewStatus.PENDING
