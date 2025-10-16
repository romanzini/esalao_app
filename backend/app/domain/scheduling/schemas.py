"""Scheduling domain schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TimeSlot(BaseModel):
    """Represents an available time slot for booking."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_time": "2025-10-16T09:00:00",
                "end_time": "2025-10-16T10:00:00",
                "available": True,
            }
        }
    }

    start_time: datetime = Field(..., description="Start time of the slot")
    end_time: datetime = Field(..., description="End time of the slot")
    available: bool = Field(default=True, description="Whether the slot is available")


class SlotRequest(BaseModel):
    """Request to calculate available slots."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "professional_id": 1,
                "date": "2025-10-16",
                "service_id": 1,
            }
        }
    }

    professional_id: int = Field(..., gt=0, description="ID of the professional")
    date: datetime = Field(..., description="Date to check availability")
    service_id: int = Field(..., gt=0, description="ID of the service")


class SlotResponse(BaseModel):
    """Response with available time slots."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "professional_id": 1,
                "date": "2025-10-16",
                "service_id": 1,
                "service_duration_minutes": 60,
                "slots": [
                    {
                        "start_time": "2025-10-16T09:00:00",
                        "end_time": "2025-10-16T10:00:00",
                        "available": True,
                    },
                    {
                        "start_time": "2025-10-16T10:00:00",
                        "end_time": "2025-10-16T11:00:00",
                        "available": True,
                    },
                ],
                "total_slots": 2,
            }
        }
    }

    professional_id: int = Field(..., description="ID of the professional")
    date: str = Field(..., description="Date in ISO format")
    service_id: int = Field(..., description="ID of the service")
    service_duration_minutes: int = Field(..., description="Duration of the service in minutes")
    slots: list[TimeSlot] = Field(default_factory=list, description="List of available time slots")
    total_slots: int = Field(..., description="Total number of available slots")
