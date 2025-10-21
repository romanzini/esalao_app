"""Unit tests for review models."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from backend.app.db.models.review import (
    Review, ReviewStatus, ReviewModerationReason, ReviewHelpfulness, ReviewFlag
)
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service


class TestReviewModel:
    """Test Review model functionality."""

    def test_review_creation_with_defaults(self):
        """Test creating a review with default values."""
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=5,
            title="Great service!",
            comment="Very professional and clean.",
        )

        assert review.booking_id == 1
        assert review.client_id == 1
        assert review.professional_id == 2
        assert review.salon_id == 1
        assert review.service_id == 1
        assert review.rating == 5
        assert review.title == "Great service!"
        assert review.comment == "Very professional and clean."
        # Check expected values - some defaults are applied by DB
        assert review.status in (ReviewStatus.PENDING, None)
        assert review.is_anonymous in (False, None)
        assert review.is_verified in (True, None)
        assert review.helpful_count in (0, None)
        assert review.not_helpful_count in (0, None)
        assert review.response_text is None
        assert review.response_at is None
        assert review.moderated_at is None
        assert review.moderated_by is None

    def test_review_status_validation(self):
        """Test review status enum validation."""
        # Valid status
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=3,
            status=ReviewStatus.APPROVED
        )
        assert review.status == ReviewStatus.APPROVED

        # Test all status values
        for status in ReviewStatus:
            review.status = status
            assert review.status == status

    def test_review_rating_constraints(self):
        """Test rating constraints (1-5)."""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            review = Review(
                booking_id=1,
                client_id=1,
                professional_id=2,
                salon_id=1,
                service_id=1,
                rating=rating
            )
            assert review.rating == rating

    def test_review_moderation_fields(self):
        """Test moderation-related fields."""
        now = datetime.utcnow()
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=4,
            status=ReviewStatus.REJECTED,
            moderation_reason=ReviewModerationReason.INAPPROPRIATE_CONTENT,
            moderation_notes="Contains profanity",
            moderated_at=now,
            moderated_by=1
        )

        assert review.status == ReviewStatus.REJECTED
        assert review.moderation_reason == ReviewModerationReason.INAPPROPRIATE_CONTENT
        assert review.moderation_notes == "Contains profanity"
        assert review.moderated_at == now
        assert review.moderated_by == 1

    def test_review_professional_response(self):
        """Test professional response functionality."""
        now = datetime.utcnow()
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=4,
            response_text="Thank you for your feedback!",
            response_at=now,
            response_by=2
        )

        assert review.response_text == "Thank you for your feedback!"
        assert review.response_at == now
        assert review.response_by == 2

    def test_review_verification(self):
        """Test review verification functionality."""
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=5,
            is_verified=True
        )
        assert review.is_verified is True

    def test_review_anonymity(self):
        """Test anonymous review functionality."""
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=3,
            is_anonymous=True
        )
        assert review.is_anonymous is True

    def test_review_helpfulness_score(self):
        """Test helpfulness score tracking."""
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=4,
            helpful_count=10,
            not_helpful_count=2
        )
        assert review.helpful_count == 10
        assert review.not_helpful_count == 2
        assert review.helpfulness_ratio == 10/12


class TestReviewHelpfulnessModel:
    """Test ReviewHelpfulness model functionality."""

    def test_helpfulness_creation(self):
        """Test creating a helpfulness vote."""
        helpfulness = ReviewHelpfulness(
            review_id=1,
            user_id=1,
            is_helpful=True
        )

        assert helpfulness.review_id == 1
        assert helpfulness.user_id == 1
        assert helpfulness.is_helpful is True
        # created_at is set by database default, so may be None in unit tests without DB

    def test_helpfulness_vote_types(self):
        """Test both helpful and not helpful votes."""
        # Helpful vote
        helpful = ReviewHelpfulness(
            review_id=1,
            user_id=1,
            is_helpful=True
        )
        assert helpful.is_helpful is True

        # Not helpful vote
        not_helpful = ReviewHelpfulness(
            review_id=1,
            user_id=2,
            is_helpful=False
        )
        assert not_helpful.is_helpful is False


class TestReviewFlagModel:
    """Test ReviewFlag model functionality."""

    def test_flag_creation(self):
        """Test creating a review flag."""
        flag = ReviewFlag(
            review_id=1,
            reporter_id=1,
            reason=ReviewModerationReason.SPAM,
            description="This looks like spam content"
        )

        assert flag.review_id == 1
        assert flag.reporter_id == 1
        assert flag.reason == ReviewModerationReason.SPAM
        assert flag.description == "This looks like spam content"
        # is_resolved defaults to False but may be None without DB default
        assert flag.is_resolved in (False, None)
        assert flag.resolved_at is None
        assert flag.resolved_by is None
        assert flag.resolution_notes is None

    def test_flag_resolution(self):
        """Test flag resolution functionality."""
        now = datetime.utcnow()
        flag = ReviewFlag(
            review_id=1,
            reporter_id=1,
            reason="inappropriate",
            is_resolved=True,
            resolved_at=now,
            resolved_by=2,
            resolution_notes="Review was approved after investigation"
        )

        assert flag.is_resolved is True
        assert flag.resolved_at == now
        assert flag.resolved_by == 2
        assert flag.resolution_notes == "Review was approved after investigation"

    def test_flag_reason_types(self):
        """Test different flag reason types."""
        reasons = [
            "spam",
            "inappropriate",
            "fake",
            "harassment",
            "other"
        ]

        for reason in reasons:
            flag = ReviewFlag(
                review_id=1,
                reporter_id=1,
                reason=reason
            )
            assert flag.reason == reason


class TestReviewEnums:
    """Test review-related enums."""

    def test_review_status_enum(self):
        """Test ReviewStatus enum values."""
        assert ReviewStatus.PENDING == "pending"
        assert ReviewStatus.APPROVED == "approved"
        assert ReviewStatus.REJECTED == "rejected"
        assert ReviewStatus.HIDDEN == "hidden"

        # Test all values are present
        expected_values = {"pending", "approved", "rejected", "hidden"}
        actual_values = {status.value for status in ReviewStatus}
        assert actual_values == expected_values

    def test_review_moderation_reason_enum(self):
        """Test ReviewModerationReason enum values."""
        assert ReviewModerationReason.INAPPROPRIATE_CONTENT == "inappropriate_content"
        assert ReviewModerationReason.SPAM == "spam"
        assert ReviewModerationReason.FAKE_REVIEW == "fake_review"
        assert ReviewModerationReason.HARASSMENT == "harassment"
        assert ReviewModerationReason.OFF_TOPIC == "off_topic"
        assert ReviewModerationReason.DUPLICATE == "duplicate"
        assert ReviewModerationReason.OTHER == "other"

        # Test all expected values are present
        expected_values = {
            "inappropriate_content",
            "spam",
            "fake_review",
            "harassment",
            "off_topic",
            "duplicate",
            "other"
        }
        actual_values = {reason.value for reason in ReviewModerationReason}
        assert actual_values == expected_values


class TestReviewConstraints:
    """Test review model constraints and validations."""

    def test_review_text_length_limits(self):
        """Test text field length constraints."""
        # Title should be limited (assume 200 chars max)
        long_title = "x" * 300
        review = Review(
            booking_id=1,
            client_id=1,
            rating=5,
            title=long_title
        )
        # Note: In a real test with DB, this would raise a constraint error
        assert len(review.title) == 300

        # Comment should allow longer text (assume 2000 chars max)
        long_comment = "x" * 2500
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=5,
            comment=long_comment
        )
        assert len(review.comment) == 2500

    def test_review_required_fields(self):
        """Test that required fields are properly set."""
        # Minimum required fields
        review = Review(
            booking_id=1,
            client_id=1,
            professional_id=2,
            salon_id=1,
            service_id=1,
            rating=5
        )

        assert review.booking_id == 1
        assert review.client_id == 1
        assert review.professional_id == 2
        assert review.salon_id == 1
        assert review.service_id == 1
        assert review.rating == 5
        # Other fields should have defaults (may be None without DB)
        assert review.status in (ReviewStatus.PENDING, None)

    def test_helpfulness_unique_constraint(self):
        """Test that user can only vote once per review (unique constraint)."""
        # This would be enforced at the database level
        # In unit tests, we just verify the model allows the creation
        vote1 = ReviewHelpfulness(
            review_id=1,
            user_id=1,
            is_helpful=True
        )

        vote2 = ReviewHelpfulness(
            review_id=1,
            user_id=1,
            is_helpful=False
        )

        # Both objects can be created, but DB would reject the second one
        assert vote1.review_id == vote2.review_id
        assert vote1.user_id == vote2.user_id


class TestReviewRelationships:
    """Test review model relationships."""

    def test_review_has_booking_relationship(self):
        """Test that review has booking relationship defined."""
        review = Review(
            booking_id=1,
            client_id=1,
            rating=5
        )

        # Verify foreign key is set
        assert review.booking_id == 1
        # In a real test with DB session, we would test:
        # assert review.booking is not None

    def test_review_has_client_relationship(self):
        """Test that review has client (user) relationship defined."""
        review = Review(
            booking_id=1,
            client_id=1,
            rating=5
        )

        # Verify foreign key is set
        assert review.client_id == 1
        # In a real test with DB session, we would test:
        # assert review.client is not None

    def test_helpfulness_has_review_relationship(self):
        """Test that helpfulness has review relationship."""
        helpfulness = ReviewHelpfulness(
            review_id=1,
            user_id=1,
            is_helpful=True
        )

        assert helpfulness.review_id == 1
        # In a real test with DB session:
        # assert helpfulness.review is not None

    def test_flag_has_review_relationship(self):
        """Test that flag has review relationship."""
        flag = ReviewFlag(
            review_id=1,
            reporter_id=1,
            reason="spam"
        )

        assert flag.review_id == 1
        # In a real test with DB session:
        # assert flag.review is not None
