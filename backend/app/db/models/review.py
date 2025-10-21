"""Review and rating system models for service quality evaluation."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, String, Float, Text, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base


class ReviewStatus(str, Enum):
    """Review status options."""

    PENDING = "pending"           # Waiting for approval
    APPROVED = "approved"         # Public and visible
    REJECTED = "rejected"         # Hidden due to policy violation
    HIDDEN = "hidden"            # Hidden by admin


class ReviewModerationReason(str, Enum):
    """Reasons for review moderation actions."""

    INAPPROPRIATE_CONTENT = "inappropriate_content"
    SPAM = "spam"
    FAKE_REVIEW = "fake_review"
    HARASSMENT = "harassment"
    OFF_TOPIC = "off_topic"
    DUPLICATE = "duplicate"
    OTHER = "other"


class Review(Base):
    """Customer reviews and ratings for completed bookings."""

    __tablename__ = "reviews"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[UUID] = mapped_column(String(36), default=uuid4, unique=True, index=True)

    # Relationships
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    professional_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    salon_id: Mapped[int] = mapped_column(Integer, ForeignKey("salons.id"), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id"), nullable=False, index=True)

    # Review content
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 scale
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Review metadata
    status: Mapped[ReviewStatus] = mapped_column(String(20), default=ReviewStatus.PENDING.value, nullable=False, index=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # True if from actual booking

    # Helpfulness metrics
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Moderation
    moderated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    moderation_reason: Mapped[Optional[ReviewModerationReason]] = mapped_column(String(50), nullable=True)
    moderation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Response from professional/salon
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_review_booking"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        CheckConstraint("helpful_count >= 0", name="ck_review_helpful_positive"),
        CheckConstraint("not_helpful_count >= 0", name="ck_review_not_helpful_positive"),
        Index("ix_reviews_rating", "rating"),
        Index("ix_reviews_created_at", "created_at"),
        Index("ix_reviews_salon_rating", "salon_id", "rating"),
        Index("ix_reviews_professional_rating", "professional_id", "rating"),
        Index("ix_reviews_service_rating", "service_id", "rating"),
        Index("ix_reviews_status_created", "status", "created_at"),
    )

    # Relationships
    booking = relationship("Booking", back_populates="review")
    client = relationship("User", foreign_keys=[client_id], back_populates="client_reviews")
    professional = relationship("User", foreign_keys=[professional_id], back_populates="professional_reviews")
    salon = relationship("Salon", back_populates="reviews")
    service = relationship("Service", back_populates="reviews")
    moderator = relationship("User", foreign_keys=[moderated_by], viewonly=True)
    responder = relationship("User", foreign_keys=[response_by], viewonly=True)

    # Review helpfulness votes
    helpfulness_votes = relationship("ReviewHelpfulness", back_populates="review", cascade="all, delete-orphan")

    # Review flags
    flags = relationship("ReviewFlag", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, booking_id={self.booking_id}, rating={self.rating}, status={self.status})>"

    @property
    def can_be_edited(self) -> bool:
        """Check if review can still be edited (within 24 hours)."""
        if not self.created_at:
            return False

        time_limit = datetime.now(timezone.utc) - self.created_at
        return time_limit.total_seconds() < 24 * 3600  # 24 hours in seconds

    @property
    def helpfulness_ratio(self) -> float:
        """Calculate helpfulness ratio (helpful / total votes)."""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0.0
        return self.helpful_count / total_votes

    @property
    def is_moderated(self) -> bool:
        """Check if review has been moderated."""
        return self.moderated_at is not None


class ReviewHelpfulness(Base):
    """Track user votes on review helpfulness."""

    __tablename__ = "review_helpfulness"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Relationships
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("reviews.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Vote
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)  # True = helpful, False = not helpful

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("review_id", "user_id", name="uq_review_helpfulness_user"),
        Index("ix_review_helpfulness_review", "review_id"),
        Index("ix_review_helpfulness_user", "user_id"),
    )

    # Relationships
    review = relationship("Review", back_populates="helpfulness_votes")
    user = relationship("User", back_populates="review_helpfulness_votes")

    def __repr__(self) -> str:
        return f"<ReviewHelpfulness(review_id={self.review_id}, user_id={self.user_id}, helpful={self.is_helpful})>"


class ReviewFlag(Base):
    """Track user reports on inappropriate reviews."""

    __tablename__ = "review_flags"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Relationships
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("reviews.id"), nullable=False)
    reporter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Flag details
    reason: Mapped[ReviewModerationReason] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("review_id", "reporter_id", name="uq_review_flag_reporter"),
        Index("ix_review_flags_review", "review_id"),
        Index("ix_review_flags_reporter", "reporter_id"),
        Index("ix_review_flags_resolved", "is_resolved"),
        Index("ix_review_flags_reason", "reason"),
    )

    # Relationships
    review = relationship("Review", back_populates="flags")
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="review_flags")
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self) -> str:
        return f"<ReviewFlag(review_id={self.review_id}, reporter_id={self.reporter_id}, reason={self.reason})>"
