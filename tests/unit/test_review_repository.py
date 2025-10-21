"""Unit tests for review repository."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.db.repositories.review import ReviewRepository
from backend.app.db.models.review import (
    Review, ReviewStatus, ReviewModerationReason, ReviewHelpfulness, ReviewFlag
)
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.booking import Booking


class TestReviewRepository:
    """Test ReviewRepository functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create ReviewRepository instance with mocked session."""
        return ReviewRepository(mock_session)

    @pytest.fixture
    def sample_review(self):
        """Create a sample review for testing."""
        return Review(
            id=1,
            booking_id=1,
            client_id=1,
            rating=5,
            title="Great service!",
            comment="Very professional and clean.",
            status=ReviewStatus.APPROVED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def test_create_review(self, repository, mock_session):
        """Test creating a new review."""
        review_data = {
            "booking_id": 1,
            "client_id": 1,
            "rating": 5,
            "title": "Great service!",
            "comment": "Very professional and clean.",
        }

        created_review = await repository.create(**review_data)

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify review attributes
        assert created_review.booking_id == 1
        assert created_review.client_id == 1
        assert created_review.rating == 5
        assert created_review.title == "Great service!"
        assert created_review.comment == "Very professional and clean."

    async def test_get_by_id(self, repository, mock_session, sample_review):
        """Test getting review by ID."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_review
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        # Verify query was executed
        mock_session.execute.assert_called_once()
        assert result == sample_review

    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test getting review by ID when not found."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None

    async def test_get_by_booking_id(self, repository, mock_session, sample_review):
        """Test getting review by booking ID."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_review
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_booking_id(1)

        # Verify query was executed
        mock_session.execute.assert_called_once()
        assert result == sample_review

    async def test_update_review(self, repository, mock_session, sample_review):
        """Test updating a review."""
        # Mock getting the review
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_review
        mock_session.execute.return_value = mock_result

        update_data = {
            "rating": 4,
            "title": "Updated title",
            "comment": "Updated comment"
        }

        updated_review = await repository.update(1, **update_data)

        # Verify session operations
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify updates
        assert updated_review.rating == 4
        assert updated_review.title == "Updated title"
        assert updated_review.comment == "Updated comment"

    async def test_delete_review(self, repository, mock_session, sample_review):
        """Test deleting a review."""
        # Mock getting the review
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_review
        mock_session.execute.return_value = mock_result

        result = await repository.delete(1)

        # Verify session operations
        mock_session.delete.assert_called_once_with(sample_review)
        mock_session.commit.assert_called_once()
        assert result is True

    async def test_delete_review_not_found(self, repository, mock_session):
        """Test deleting a review that doesn't exist."""
        # Mock getting the review (not found)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.delete(999)

        # Verify no delete operation
        mock_session.delete.assert_not_called()
        assert result is False

    async def test_list_reviews_with_filters(self, repository, mock_session):
        """Test listing reviews with various filters."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Test with various filter combinations
        filters = [
            {"salon_id": 1},
            {"professional_id": 2},
            {"service_id": 3},
            {"client_id": 4},
            {"status": ReviewStatus.APPROVED},
            {"min_rating": 4},
            {"max_rating": 5},
            {"with_comments_only": True},
            {"verified_only": True},
        ]

        for filter_params in filters:
            await repository.list_reviews(**filter_params)
            mock_session.execute.assert_called()

    async def test_list_reviews_with_pagination(self, repository, mock_session):
        """Test listing reviews with pagination."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.list_reviews(limit=10, offset=20)

        # Verify query was executed with pagination
        mock_session.execute.assert_called()

    async def test_list_reviews_with_sorting(self, repository, mock_session):
        """Test listing reviews with sorting options."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Test different sorting options
        sort_options = [
            ("created_at", "asc"),
            ("created_at", "desc"),
            ("rating", "asc"),
            ("rating", "desc"),
            ("helpfulness_score", "desc"),
        ]

        for sort_by, sort_order in sort_options:
            await repository.list_reviews(sort_by=sort_by, sort_order=sort_order)
            mock_session.execute.assert_called()

    async def test_count_reviews(self, repository, mock_session):
        """Test counting reviews with filters."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result

        count = await repository.count_reviews(salon_id=1, status=ReviewStatus.APPROVED)

        # Verify query was executed
        mock_session.execute.assert_called_once()
        assert count == 42

    async def test_get_rating_statistics(self, repository, mock_session):
        """Test getting rating statistics."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (4.5, 100, 5.0, 1.0, 0.8)
        mock_session.execute.return_value = mock_result

        stats = await repository.get_rating_statistics(salon_id=1)

        # Verify query was executed
        mock_session.execute.assert_called_once()
        assert stats["average_rating"] == 4.5
        assert stats["total_reviews"] == 100
        assert stats["max_rating"] == 5.0
        assert stats["min_rating"] == 1.0
        assert stats["stddev_rating"] == 0.8

    async def test_get_rating_distribution(self, repository, mock_session):
        """Test getting rating distribution."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            (5, 50),
            (4, 30),
            (3, 15),
            (2, 3),
            (1, 2),
        ]
        mock_session.execute.return_value = mock_result

        distribution = await repository.get_rating_distribution(salon_id=1)

        # Verify query was executed
        mock_session.execute.assert_called_once()
        assert distribution == {5: 50, 4: 30, 3: 15, 2: 3, 1: 2}

    async def test_get_recent_reviews(self, repository, mock_session):
        """Test getting recent reviews."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.get_recent_reviews(days=7, limit=10)

        # Verify query was executed
        mock_session.execute.assert_called_once()

    async def test_get_pending_reviews(self, repository, mock_session):
        """Test getting pending reviews for moderation."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.get_pending_reviews_for_moderation(limit=20)

        # Verify query was executed
        mock_session.execute.assert_called_once()

    async def test_get_flagged_reviews(self, repository, mock_session):
        """Test getting flagged reviews."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.get_flagged_reviews(limit=20)

        # Verify query was executed
        mock_session.execute.assert_called_once()

    async def test_bulk_moderate_reviews(self, repository, mock_session):
        """Test bulk moderating reviews."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        review_ids = [1, 2, 3]
        status = ReviewStatus.APPROVED
        moderator_id = 1

        await repository.bulk_moderate_reviews(
            review_ids=review_ids,
            status=status,
            moderator_id=moderator_id
        )

        # Verify query was executed
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()


class TestReviewHelpfulnessRepository:
    """Test ReviewHelpfulness repository methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create ReviewRepository instance with mocked session."""
        return ReviewRepository(mock_session)

    async def test_vote_helpfulness(self, repository, mock_session):
        """Test voting on review helpfulness."""
        # Mock existing vote check (none found)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        await repository.vote_helpfulness(review_id=1, user_id=1, is_helpful=True)

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_update_existing_helpfulness_vote(self, repository, mock_session):
        """Test updating existing helpfulness vote."""
        # Mock existing vote
        existing_vote = ReviewHelpfulness(
            review_id=1,
            user_id=1,
            is_helpful=True
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = existing_vote
        mock_session.execute.return_value = mock_result

        await repository.vote_helpfulness(review_id=1, user_id=1, is_helpful=False)

        # Verify vote was updated
        assert existing_vote.is_helpful is False
        mock_session.commit.assert_called_once()

    async def test_get_helpfulness_stats(self, repository, mock_session):
        """Test getting helpfulness statistics for a review."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (15, 3)  # helpful, not_helpful
        mock_session.execute.return_value = mock_result

        stats = await repository.get_helpfulness_stats(review_id=1)

        # Verify query was executed
        mock_session.execute.assert_called_once()
        assert stats["helpful_count"] == 15
        assert stats["not_helpful_count"] == 3


class TestReviewFlagRepository:
    """Test ReviewFlag repository methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create ReviewRepository instance with mocked session."""
        return ReviewRepository(mock_session)

    async def test_flag_review(self, repository, mock_session):
        """Test flagging a review."""
        flag_data = {
            "review_id": 1,
            "reporter_id": 1,
            "reason": "spam",
            "description": "This looks like spam content"
        }

        await repository.flag_review(**flag_data)

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_resolve_flag(self, repository, mock_session):
        """Test resolving a review flag."""
        # Mock existing flag
        existing_flag = ReviewFlag(
            id=1,
            review_id=1,
            reporter_id=1,
            reason="spam",
            is_resolved=False
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = existing_flag
        mock_session.execute.return_value = mock_result

        await repository.resolve_flag(
            flag_id=1,
            resolver_id=2,
            resolution_notes="Flag reviewed and dismissed"
        )

        # Verify flag was resolved
        assert existing_flag.is_resolved is True
        assert existing_flag.resolved_by == 2
        assert existing_flag.resolution_notes == "Flag reviewed and dismissed"
        mock_session.commit.assert_called_once()

    async def test_get_flags_for_review(self, repository, mock_session):
        """Test getting flags for a specific review."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.get_flags_for_review(review_id=1)

        # Verify query was executed
        mock_session.execute.assert_called_once()

    async def test_get_unresolved_flags(self, repository, mock_session):
        """Test getting unresolved flags."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.get_unresolved_flags(limit=20)

        # Verify query was executed
        mock_session.execute.assert_called_once()
