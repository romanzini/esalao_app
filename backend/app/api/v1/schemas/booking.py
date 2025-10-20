"""Booking API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.db.models.booking import BookingStatus
from backend.app.domain.policies.no_show import NoShowReason


class BookingCreateRequest(BaseModel):
    """Request to create a new booking."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "professional_id": 1,
                "service_id": 1,
                "scheduled_at": "2025-10-20T09:00:00",
                "notes": "First time client, please call 30 min before",
            }
        }
    }

    professional_id: int = Field(..., gt=0, description="ID of the professional")
    service_id: int = Field(..., gt=0, description="ID of the service")
    scheduled_at: datetime = Field(..., description="Scheduled date and time")
    notes: str | None = Field(None, max_length=500, description="Optional booking notes")


class BookingStatusUpdate(BaseModel):
    """Request to update booking status."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "confirmed",
                "cancellation_reason": None,
            }
        }
    }

    status: BookingStatus = Field(..., description="New booking status")
    cancellation_reason: str | None = Field(
        None,
        max_length=500,
        description="Reason for cancellation (required if status is cancelled)",
    )


class CancellationFeeRequest(BaseModel):
    """Request to calculate cancellation fee."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "cancellation_time": "2025-10-19T15:00:00",
            }
        }
    }

    cancellation_time: datetime | None = Field(
        None,
        description="When cancellation would occur (default: now)",
    )


class CancellationFeeResponse(BaseModel):
    """Response with cancellation fee calculation."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "fee_amount": 15.00,
                "tier_name": "Standard (24-72h)",
                "allows_refund": True,
                "policy_name": "Default Platform Policy",
                "advance_hours": 48,
                "refund_amount": 35.00,
            }
        }
    }

    fee_amount: float = Field(..., description="Cancellation fee amount (BRL)")
    tier_name: str = Field(..., description="Applied tier name")
    allows_refund: bool = Field(..., description="Whether refund is allowed")
    policy_name: str = Field(..., description="Policy name used")
    advance_hours: int = Field(..., description="Hours of advance notice")
    refund_amount: float = Field(..., description="Amount to be refunded (BRL)")


class BookingCancellationRequest(BaseModel):
    """Request to cancel a booking."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "reason": "Client emergency",
                "cancellation_time": "2025-10-19T15:00:00",
            }
        }
    }

    reason: str = Field(..., max_length=500, description="Cancellation reason")
    cancellation_time: datetime | None = Field(
        None,
        description="When cancellation occurs (default: now)",
    )


class BookingCancellationResponse(BaseModel):
    """Response after booking cancellation."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Booking cancelled with Standard (24-72h) fee",
                "cancellation_fee": 15.00,
                "refund_amount": 35.00,
                "payment_required": False,
                "policy_applied": "Default Platform Policy",
            }
        }
    }

    success: bool = Field(..., description="Whether cancellation succeeded")
    message: str = Field(..., description="Cancellation result message")
    cancellation_fee: float = Field(..., description="Fee charged (BRL)")
    refund_amount: float = Field(..., description="Amount refunded (BRL)")
    payment_required: bool = Field(..., description="If additional payment needed")
    policy_applied: str = Field(..., description="Policy name used")


class BookingResponse(BaseModel):
    """Response with booking details."""

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "client_id": 1,
                "professional_id": 1,
                "service_id": 1,
                "scheduled_at": "2025-10-20T09:00:00",
                "duration_minutes": 60,
                "status": "confirmed",
                "service_price": 50.00,
                "deposit_amount": None,
                "notes": "First time client",
                "cancellation_reason": None,
                "cancelled_at": None,
                "created_at": "2025-10-15T10:00:00",
                "updated_at": "2025-10-15T10:00:00",
            }
        }
    }

    id: int = Field(..., description="Booking ID")
    client_id: int = Field(..., description="Client user ID")
    professional_id: int = Field(..., description="Professional ID")
    service_id: int = Field(..., description="Service ID")
    scheduled_at: datetime = Field(..., description="Scheduled date and time")
    duration_minutes: int = Field(..., description="Service duration in minutes")
    status: BookingStatus = Field(..., description="Current booking status")
    service_price: float = Field(..., description="Service price (BRL)")
    deposit_amount: float | None = Field(None, description="Deposit amount (BRL)")
    notes: str | None = Field(None, description="Booking notes")
    cancellation_reason: str | None = Field(None, description="Cancellation reason")
    cancelled_at: datetime | None = Field(None, description="Cancellation timestamp")
    cancellation_fee_amount: float | None = Field(None, description="Cancellation fee (BRL)")
    cancellation_policy_id: int | None = Field(None, description="Applied policy ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class BookingListResponse(BaseModel):
    """Response with list of bookings."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "bookings": [
                    {
                        "id": 1,
                        "client_id": 1,
                        "professional_id": 1,
                        "service_id": 1,
                        "scheduled_at": "2025-10-20T09:00:00",
                        "duration_minutes": 60,
                        "status": "confirmed",
                        "service_price": 50.00,
                        "created_at": "2025-10-15T10:00:00",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
            }
        }
    }

    bookings: list[BookingResponse] = Field(default_factory=list, description="List of bookings")
    total: int = Field(..., description="Total number of bookings")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=10, description="Number of items per page")


# No-Show Management Schemas

class NoShowEvaluationRequest(BaseModel):
    """Request to evaluate booking for no-show."""

    evaluation_time: Optional[datetime] = Field(
        default=None,
        description="Time to evaluate against (defaults to current time)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "evaluation_time": "2024-01-15T10:30:00Z"
            }
        }
    }


class NoShowEvaluationResponse(BaseModel):
    """Response from no-show evaluation."""

    booking_id: int = Field(..., description="Booking ID evaluated")
    should_mark_no_show: bool = Field(..., description="Whether booking should be marked as no-show")
    reason: Optional[NoShowReason] = Field(None, description="Reason for no-show if applicable")
    fee_amount: float = Field(..., description="Calculated no-show fee")
    fee_calculation: Dict[str, Any] = Field(default_factory=dict, description="Fee calculation details")

    # Timing details
    detection_time: datetime = Field(..., description="Time when evaluation was performed")
    grace_period_expired: bool = Field(..., description="Whether grace period has expired")
    minutes_late: int = Field(..., description="Minutes late from scheduled time")

    # Policy info
    policy_id: int = Field(..., description="Policy ID used for evaluation")
    auto_detected: bool = Field(..., description="Whether this was auto-detected")

    # Dispute info
    can_dispute: bool = Field(..., description="Whether marking can be disputed")
    dispute_deadline: Optional[datetime] = Field(None, description="Deadline for disputing")
    recommended_action: str = Field(..., description="Recommended next action")

    model_config = {
        "json_schema_extra": {
            "example": {
                "booking_id": 123,
                "should_mark_no_show": True,
                "reason": "client_no_show",
                "fee_amount": 25.0,
                "fee_calculation": {
                    "base_price": 50.0,
                    "rule": {"base_percentage": 50.0},
                    "final_amount": 25.0
                },
                "detection_time": "2024-01-15T10:30:00Z",
                "grace_period_expired": True,
                "minutes_late": 30,
                "policy_id": 1,
                "auto_detected": True,
                "can_dispute": True,
                "dispute_deadline": "2024-01-16T10:30:00Z",
                "recommended_action": "mark_no_show"
            }
        }
    }


class NoShowMarkRequest(BaseModel):
    """Request to mark booking as no-show."""

    reason: NoShowReason = Field(..., description="Reason for marking as no-show")
    manual_fee_amount: Optional[float] = Field(
        None,
        ge=0,
        description="Manual fee override (uses policy calculation if not provided)"
    )
    reason_notes: Optional[str] = Field(
        None,
        max_length=200,
        description="Additional notes about the no-show"
    )
    marked_at: Optional[datetime] = Field(
        None,
        description="Time when marked (defaults to current time)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "reason": "client_no_show",
                "manual_fee_amount": 30.0,
                "reason_notes": "Client did not arrive and did not respond to calls",
                "marked_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class NoShowMarkResponse(BaseModel):
    """Response from marking booking as no-show."""

    booking_id: int = Field(..., description="Booking ID marked")
    marked_at: datetime = Field(..., description="When booking was marked as no-show")
    marked_by_id: int = Field(..., description="User ID who marked the no-show")
    reason: str = Field(..., description="Reason for no-show")
    fee_amount: float = Field(..., description="Fee amount applied")
    status: BookingStatus = Field(..., description="Updated booking status")
    message: str = Field(..., description="Success message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "booking_id": 123,
                "marked_at": "2024-01-15T10:30:00Z",
                "marked_by_id": 456,
                "reason": "client_no_show",
                "fee_amount": 25.0,
                "status": "no_show",
                "message": "Booking marked as no-show successfully"
            }
        }
    }


class NoShowDisputeRequest(BaseModel):
    """Request to dispute no-show marking."""

    dispute_reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Reason for disputing the no-show marking"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "dispute_reason": "I arrived on time but the professional was not available. I waited for 20 minutes."
            }
        }
    }


class NoShowDisputeResponse(BaseModel):
    """Response from disputing no-show."""

    booking_id: int = Field(..., description="Booking ID disputed")
    disputed_at: datetime = Field(..., description="When dispute was filed")
    disputed_by_id: int = Field(..., description="User ID who filed dispute")
    dispute_reason: str = Field(..., description="Reason for dispute")
    status: str = Field(..., description="Dispute status")
    message: str = Field(..., description="Response message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "booking_id": 123,
                "disputed_at": "2024-01-15T11:00:00Z",
                "disputed_by_id": 789,
                "dispute_reason": "I arrived on time but the professional was not available",
                "status": "dispute_filed",
                "message": "Dispute filed successfully and will be reviewed"
            }
        }
    }


class NoShowStatisticsResponse(BaseModel):
    """Response with no-show statistics."""

    period: Dict[str, datetime] = Field(..., description="Statistics period")
    totals: Dict[str, Any] = Field(..., description="Total counts and rates")
    financial: Dict[str, float] = Field(..., description="Financial impact data")
    reasons: Dict[str, int] = Field(..., description="Breakdown by reason")
    filters: Dict[str, Any] = Field(..., description="Applied filters")

    model_config = {
        "json_schema_extra": {
            "example": {
                "period": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-31T23:59:59Z"
                },
                "totals": {
                    "bookings": 150,
                    "no_shows": 15,
                    "no_show_rate": 10.0
                },
                "financial": {
                    "total_fees_charged": 375.0,
                    "average_fee": 25.0
                },
                "reasons": {
                    "client_no_show": 12,
                    "professional_no_show": 2,
                    "client_late_excessive": 1
                },
                "filters": {
                    "unit_id": None,
                    "professional_id": None
                }
            }
        }
    }
