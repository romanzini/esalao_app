"""Booking API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models.booking import BookingStatus


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
