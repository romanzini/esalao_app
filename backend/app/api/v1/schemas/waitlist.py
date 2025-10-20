"""Waitlist API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.db.models.waitlist import WaitlistPriority, WaitlistStatus


class WaitlistJoinRequest(BaseModel):
    """Request to join waitlist."""

    professional_id: int = Field(..., description="ID of the professional")
    service_id: int = Field(..., description="ID of the service")
    unit_id: int = Field(..., description="ID of the unit")
    preferred_datetime: datetime = Field(..., description="Preferred appointment time")
    flexibility_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours of flexibility around preferred time (1-168)"
    )
    priority: WaitlistPriority = Field(
        default=WaitlistPriority.NORMAL,
        description="Priority level in the queue"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional notes or special requests"
    )
    notify_email: bool = Field(default=True, description="Send email notifications")
    notify_sms: bool = Field(default=False, description="Send SMS notifications")
    notify_push: bool = Field(default=True, description="Send push notifications")

    model_config = {
        "json_schema_extra": {
            "example": {
                "professional_id": 1,
                "service_id": 2,
                "unit_id": 1,
                "preferred_datetime": "2025-10-25T14:00:00Z",
                "flexibility_hours": 48,
                "priority": "normal",
                "notes": "Prefer afternoon appointments",
                "notify_email": True,
                "notify_sms": False,
                "notify_push": True
            }
        }
    }


class WaitlistJoinResponse(BaseModel):
    """Response after joining waitlist."""

    waitlist_id: int = Field(..., description="ID of the waitlist entry")
    position: int = Field(..., description="Position in the queue")
    estimated_wait_time: Optional[str] = Field(
        default=None,
        description="Estimated wait time description"
    )
    message: str = Field(..., description="Success message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "waitlist_id": 123,
                "position": 3,
                "estimated_wait_time": "1-2 days",
                "message": "Successfully joined waitlist at position 3"
            }
        }
    }


class WaitlistLeaveRequest(BaseModel):
    """Request to leave waitlist."""

    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason for leaving waitlist"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "reason": "Found another appointment time"
            }
        }
    }


class WaitlistOfferRequest(BaseModel):
    """Request to offer slot to waitlist."""

    professional_id: int = Field(..., description="Professional ID")
    service_id: int = Field(..., description="Service ID")
    slot_start: datetime = Field(..., description="Start time of available slot")
    slot_end: datetime = Field(..., description="End time of available slot")
    offer_duration_hours: int = Field(
        default=2,
        ge=1,
        le=24,
        description="How long client has to respond (1-24 hours)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "professional_id": 1,
                "service_id": 2,
                "slot_start": "2025-10-25T14:00:00Z",
                "slot_end": "2025-10-25T15:00:00Z",
                "offer_duration_hours": 2
            }
        }
    }


class WaitlistOfferResponse(BaseModel):
    """Response after offering slots."""

    offers_made: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of offers made to waitlist entries"
    )
    message: str = Field(..., description="Result message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "offers_made": [
                    {
                        "waitlist_id": 123,
                        "client_id": 456,
                        "slot_start": "2025-10-25T14:00:00Z",
                        "slot_end": "2025-10-25T15:00:00Z",
                        "offer_expires_at": "2025-10-25T16:00:00Z",
                        "position": 1,
                        "priority": "normal"
                    }
                ],
                "message": "Offered slot to 1 waitlist entry"
            }
        }
    }


class WaitlistOfferResponseRequest(BaseModel):
    """Request to respond to waitlist offer."""

    accepted: bool = Field(..., description="Whether to accept the offer")
    response_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional response notes"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "accepted": True,
                "response_notes": "Perfect timing, thank you!"
            }
        }
    }


class WaitlistOfferResponseResponse(BaseModel):
    """Response after responding to offer."""

    accepted: bool = Field(..., description="Whether offer was accepted")
    booking_id: Optional[int] = Field(
        default=None,
        description="ID of created booking if accepted"
    )
    message: str = Field(..., description="Result message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "accepted": True,
                "booking_id": 789,
                "message": "Offer accepted and booking created successfully"
            }
        }
    }


class WaitlistEntryResponse(BaseModel):
    """Individual waitlist entry details."""

    waitlist_id: int = Field(..., description="ID of waitlist entry")
    professional_id: int = Field(..., description="Professional ID")
    professional_name: str = Field(..., description="Professional name")
    service_id: int = Field(..., description="Service ID")
    service_name: str = Field(..., description="Service name")
    preferred_datetime: datetime = Field(..., description="Preferred appointment time")
    flexibility_hours: int = Field(..., description="Hours of flexibility")
    status: WaitlistStatus = Field(..., description="Current status")
    current_position: Optional[int] = Field(
        default=None,
        description="Current position in queue (for active entries)"
    )
    priority: WaitlistPriority = Field(..., description="Priority level")
    joined_at: datetime = Field(..., description="When joined waitlist")
    notes: Optional[str] = Field(default=None, description="Client notes")

    # Offer details (if applicable)
    offered_slot_start: Optional[datetime] = Field(
        default=None,
        description="Start time of offered slot"
    )
    offered_slot_end: Optional[datetime] = Field(
        default=None,
        description="End time of offered slot"
    )
    offer_expires_at: Optional[datetime] = Field(
        default=None,
        description="When offer expires"
    )
    offered_at: Optional[datetime] = Field(
        default=None,
        description="When offer was made"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "waitlist_id": 123,
                "professional_id": 1,
                "professional_name": "Dr. Silva",
                "service_id": 2,
                "service_name": "Corte de Cabelo",
                "preferred_datetime": "2025-10-25T14:00:00Z",
                "flexibility_hours": 24,
                "status": "active",
                "current_position": 2,
                "priority": "normal",
                "joined_at": "2025-10-20T10:00:00Z",
                "notes": "Prefer afternoon appointments"
            }
        }
    }


class WaitlistStatusResponse(BaseModel):
    """Client's waitlist status response."""

    entries: List[WaitlistEntryResponse] = Field(
        default_factory=list,
        description="List of waitlist entries"
    )
    total_active: int = Field(..., description="Total active waitlist entries")

    model_config = {
        "json_schema_extra": {
            "example": {
                "entries": [
                    {
                        "waitlist_id": 123,
                        "professional_id": 1,
                        "professional_name": "Dr. Silva",
                        "service_id": 2,
                        "service_name": "Corte de Cabelo",
                        "preferred_datetime": "2025-10-25T14:00:00Z",
                        "flexibility_hours": 24,
                        "status": "active",
                        "current_position": 2,
                        "priority": "normal",
                        "joined_at": "2025-10-20T10:00:00Z",
                        "notes": "Prefer afternoon appointments"
                    }
                ],
                "total_active": 1
            }
        }
    }


class WaitlistStatisticsResponse(BaseModel):
    """Waitlist statistics response."""

    period: Dict[str, Any] = Field(..., description="Statistics period")
    total_entries: int = Field(..., description="Total waitlist entries")
    status_breakdown: Dict[str, int] = Field(..., description="Count by status")
    active_entries: int = Field(..., description="Currently active entries")
    pending_offers: int = Field(..., description="Pending offers awaiting response")
    conversion_rate: float = Field(..., description="Offer acceptance rate (%)")
    average_wait_hours: float = Field(..., description="Average wait time in hours")
    filters: Dict[str, Any] = Field(..., description="Applied filters")

    model_config = {
        "json_schema_extra": {
            "example": {
                "period": {
                    "start": "2025-10-01T00:00:00Z",
                    "end": "2025-10-31T23:59:59Z"
                },
                "total_entries": 45,
                "status_breakdown": {
                    "active": 12,
                    "offered": 3,
                    "accepted": 18,
                    "declined": 8,
                    "expired": 4
                },
                "active_entries": 12,
                "pending_offers": 3,
                "conversion_rate": 69.2,
                "average_wait_hours": 18.5,
                "filters": {
                    "professional_id": 1,
                    "service_id": None,
                    "unit_id": None
                }
            }
        }
    }
