"""Review API schemas for validation and serialization."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict

from backend.app.db.models.review import ReviewStatus, ReviewModerationReason


# Request schemas
class ReviewCreateRequest(BaseModel):
    """Schema for creating a new review."""

    booking_id: int = Field(..., description="ID of the completed booking")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    title: Optional[str] = Field(None, max_length=200, description="Optional review title")
    comment: Optional[str] = Field(None, max_length=2000, description="Optional review comment")
    is_anonymous: bool = Field(False, description="Whether to publish review anonymously")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v and not v.strip():
            return None
        return v.strip() if v else None

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v):
        if v and not v.strip():
            return None
        return v.strip() if v else None


class ReviewUpdateRequest(BaseModel):
    """Schema for updating an existing review."""

    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5 stars")
    title: Optional[str] = Field(None, max_length=200, description="Review title")
    comment: Optional[str] = Field(None, max_length=2000, description="Review comment")
    is_anonymous: Optional[bool] = Field(None, description="Whether to publish review anonymously")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v and not v.strip():
            return None
        return v.strip() if v else None

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v):
        if v and not v.strip():
            return None
        return v.strip() if v else None


class ReviewModerationRequest(BaseModel):
    """Schema for moderating a review."""

    status: ReviewStatus = Field(..., description="New review status")
    reason: Optional[ReviewModerationReason] = Field(None, description="Moderation reason")
    notes: Optional[str] = Field(None, max_length=1000, description="Moderation notes")


class ProfessionalResponseRequest(BaseModel):
    """Schema for professional/salon response to review."""

    response_text: str = Field(..., max_length=1000, description="Response to the review")

    @field_validator("response_text")
    @classmethod
    def validate_response_text(cls, v):
        if not v.strip():
            raise ValueError("Response text cannot be empty")
        return v.strip()


class ReviewHelpfulnessRequest(BaseModel):
    """Schema for voting on review helpfulness."""

    is_helpful: bool = Field(..., description="True if helpful, False if not helpful")


class ReviewFlagRequest(BaseModel):
    """Schema for flagging a review."""

    reason: ReviewModerationReason = Field(..., description="Reason for flagging")
    description: Optional[str] = Field(None, max_length=500, description="Additional description")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v and not v.strip():
            return None
        return v.strip() if v else None


class BulkModerationRequest(BaseModel):
    """Schema for bulk moderating reviews."""

    review_ids: List[int] = Field(..., min_length=1, max_length=50, description="List of review IDs")
    status: ReviewStatus = Field(..., description="New status for all reviews")
    reason: Optional[ReviewModerationReason] = Field(None, description="Moderation reason")
    notes: Optional[str] = Field(None, max_length=1000, description="Moderation notes")


# Response schemas
class UserBasicResponse(BaseModel):
    """Basic user information for reviews."""

    id: int
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class SalonBasicResponse(BaseModel):
    """Basic salon information for reviews."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ServiceBasicResponse(BaseModel):
    """Basic service information for reviews."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class BookingBasicResponse(BaseModel):
    """Basic booking information for reviews."""

    id: int
    scheduled_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewResponse(BaseModel):
    """Schema for review response."""

    id: int
    uuid: UUID
    booking_id: int
    rating: int
    title: Optional[str]
    comment: Optional[str]
    status: ReviewStatus
    is_anonymous: bool
    is_verified: bool
    helpful_count: int
    not_helpful_count: int
    response_text: Optional[str]
    response_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    # Relationships (shown based on privacy settings)
    client: Optional[UserBasicResponse]
    professional: UserBasicResponse
    salon: SalonBasicResponse
    service: ServiceBasicResponse
    booking: Optional[BookingBasicResponse]
    responder: Optional[UserBasicResponse]

    # Computed properties
    can_be_edited: bool = Field(description="Whether review can still be edited")
    helpfulness_ratio: float = Field(description="Ratio of helpful votes")
    is_moderated: bool = Field(description="Whether review has been moderated")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("client", mode="before")
    @classmethod
    def handle_anonymous_client(cls, v, info):
        """Hide client info for anonymous reviews."""
        values = info.data if hasattr(info, 'data') else {}
        is_anonymous = values.get('is_anonymous', False)
        if is_anonymous:
            return None
        return v


class ReviewListResponse(BaseModel):
    """Schema for paginated review list response."""

    reviews: List[ReviewResponse]
    total: int
    page: int
    size: int
    has_next: bool

    model_config = ConfigDict(from_attributes=True)


class ReviewStatsResponse(BaseModel):
    """Schema for review statistics response."""

    total_reviews: int = Field(description="Total number of reviews")
    average_rating: float = Field(description="Average rating")
    rating_distribution: Dict[str, int] = Field(description="Distribution of ratings 1-5")

    model_config = ConfigDict(from_attributes=True)


class ReviewFlagResponse(BaseModel):
    """Schema for review flag response."""

    id: int
    review_id: int
    reason: ReviewModerationReason
    description: Optional[str]
    is_resolved: bool
    resolution_notes: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime

    # Relationships
    reporter: UserBasicResponse
    resolver: Optional[UserBasicResponse]

    model_config = ConfigDict(from_attributes=True)


class ReviewModerationResponse(BaseModel):
    """Schema for review moderation response."""

    id: int
    status: ReviewStatus
    moderation_reason: Optional[ReviewModerationReason]
    moderation_notes: Optional[str]
    moderated_at: Optional[datetime]
    moderator: Optional[UserBasicResponse]

    model_config = ConfigDict(from_attributes=True)


class ReviewTrendsResponse(BaseModel):
    """Schema for review trends response."""

    current_stats: ReviewStatsResponse
    recent_count: int = Field(description="Number of recent reviews")
    recent_average: float = Field(description="Average rating of recent reviews")

    model_config = ConfigDict(from_attributes=True)


# Query parameter schemas
class ReviewListParams(BaseModel):
    """Query parameters for listing reviews."""

    salon_id: Optional[int] = Field(None, description="Filter by salon ID")
    professional_id: Optional[int] = Field(None, description="Filter by professional ID")
    service_id: Optional[int] = Field(None, description="Filter by service ID")
    client_id: Optional[int] = Field(None, description="Filter by client ID")
    status: Optional[ReviewStatus] = Field(None, description="Filter by review status")
    min_rating: Optional[int] = Field(None, ge=1, le=5, description="Minimum rating filter")
    max_rating: Optional[int] = Field(None, ge=1, le=5, description="Maximum rating filter")
    with_comments_only: bool = Field(False, description="Show only reviews with comments")
    verified_only: bool = Field(False, description="Show only verified reviews")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed_fields = [
            "created_at", "updated_at", "rating", "helpful_count",
            "not_helpful_count", "helpfulness_ratio"
        ]
        if v not in allowed_fields:
            raise ValueError(f"Invalid sort field. Allowed: {allowed_fields}")
        return v

    @field_validator("max_rating")
    @classmethod
    def validate_rating_range(cls, v, info):
        """Ensure max_rating >= min_rating."""
        values = info.data if hasattr(info, 'data') else {}
        min_rating = values.get('min_rating')
        if min_rating is not None and v is not None and v < min_rating:
            raise ValueError("max_rating must be >= min_rating")
        return v


class ModerationListParams(BaseModel):
    """Query parameters for moderation lists."""

    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(50, ge=1, le=100, description="Page size")


# Statistics request schemas
class StatsRequest(BaseModel):
    """Schema for statistics request."""

    salon_id: Optional[int] = Field(None, description="Filter by salon ID")
    professional_id: Optional[int] = Field(None, description="Filter by professional ID")
    service_id: Optional[int] = Field(None, description="Filter by service ID")


class TrendsRequest(BaseModel):
    """Schema for trends request."""

    salon_id: Optional[int] = Field(None, description="Filter by salon ID")
    professional_id: Optional[int] = Field(None, description="Filter by professional ID")
    days: int = Field(30, ge=1, le=365, description="Number of days for trends")


# Error response schemas
class ReviewErrorResponse(BaseModel):
    """Schema for review error responses."""

    error: str = Field(description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")

    model_config = ConfigDict(from_attributes=True)
