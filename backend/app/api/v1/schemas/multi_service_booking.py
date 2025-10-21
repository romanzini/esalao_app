"""Multi-service booking API schemas."""

from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel, Field, validator

from backend.app.db.models.multi_service_booking import MultiServiceBookingStatus
from backend.app.api.v1.schemas.booking import BookingResponse


class ServiceRequest(BaseModel):
    """Individual service request within a multi-service package."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "service_id": 1,
                "professional_id": 1,
                "scheduled_at": "2025-10-20T09:00:00",
                "notes": "First service in package"
            }
        }
    }

    service_id: int = Field(..., gt=0, description="ID of the service")
    professional_id: int = Field(..., gt=0, description="ID of the professional for this service")
    scheduled_at: datetime = Field(..., description="Scheduled date and time for this service")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes for this specific service")


class MultiServiceBookingCreateRequest(BaseModel):
    """Request to create a multi-service booking package."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "package_name": "Complete Beauty Package",
                "services": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "scheduled_at": "2025-10-20T09:00:00",
                        "notes": "Haircut first"
                    },
                    {
                        "service_id": 2,
                        "professional_id": 1,
                        "scheduled_at": "2025-10-20T10:00:00",
                        "notes": "Hair color after cut"
                    }
                ],
                "notes": "Client has allergies to certain products"
            }
        }
    }

    package_name: str = Field(..., min_length=3, max_length=200, description="Name for the service package")
    services: List[ServiceRequest] = Field(..., min_items=2, max_items=10, description="List of services in the package")
    notes: Optional[str] = Field(None, max_length=1000, description="General notes for the entire package")

    @validator("services")
    def validate_services_order(cls, services):
        """Validate that services are ordered chronologically."""
        if len(services) < 2:
            return services

        # Check chronological order
        for i in range(1, len(services)):
            if services[i].scheduled_at <= services[i-1].scheduled_at:
                raise ValueError("Services must be scheduled in chronological order")

        return services

    @validator("services")
    def validate_no_overlaps(cls, services):
        """Validate that there are no overlapping service times."""
        if len(services) < 2:
            return services

        # For now, just ensure minimum 15-minute gap
        for i in range(1, len(services)):
            time_diff = (services[i].scheduled_at - services[i-1].scheduled_at).total_seconds() / 60
            if time_diff < 15:  # Minimum 15 minutes between services
                raise ValueError("Services must have at least 15 minutes between them")

        return services


class MultiServiceBookingStatusUpdate(BaseModel):
    """Request to update multi-service booking status."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "confirmed",
                "cancellation_reason": None
            }
        }
    }

    status: MultiServiceBookingStatus = Field(..., description="New booking status")
    cancellation_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for cancellation (required if status is cancelled)"
    )

    @validator("cancellation_reason")
    def validate_cancellation_reason(cls, v, values):
        """Require cancellation reason when cancelling."""
        status = values.get("status")
        if status in (MultiServiceBookingStatus.CANCELLED, MultiServiceBookingStatus.PARTIALLY_CANCELLED):
            if not v or not v.strip():
                raise ValueError("Cancellation reason is required when cancelling a booking")
        return v


class MultiServiceBookingResponse(BaseModel):
    """Response with multi-service booking details."""

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "client_id": 1,
                "primary_professional_id": 1,
                "package_name": "Complete Beauty Package",
                "status": "confirmed",
                "total_price": 150.00,
                "total_duration_minutes": 120,
                "total_services_count": 2,
                "starts_at": "2025-10-20T09:00:00",
                "ends_at": "2025-10-20T11:00:00",
                "notes": "Client has allergies",
                "individual_bookings": [],
                "created_at": "2025-10-15T10:00:00",
                "updated_at": "2025-10-15T10:00:00"
            }
        }
    }

    id: int = Field(..., description="Multi-service booking ID")
    client_id: int = Field(..., description="Client user ID")
    primary_professional_id: int = Field(..., description="Primary professional ID")
    package_name: str = Field(..., description="Package name")
    status: MultiServiceBookingStatus = Field(..., description="Current package status")
    total_price: float = Field(..., description="Total price for all services (BRL)")
    total_duration_minutes: int = Field(..., description="Total duration in minutes")
    total_services_count: int = Field(..., description="Number of services in package")
    starts_at: datetime = Field(..., description="Start time of first service")
    ends_at: datetime = Field(..., description="End time of last service")
    notes: Optional[str] = Field(None, description="Package notes")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    individual_bookings: List[BookingResponse] = Field(default_factory=list, description="Individual service bookings")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.individual_bookings:
            return 0.0

        completed_count = sum(
            1 for booking in self.individual_bookings
            if booking.status in ["completed", "no_show"]
        )

        return (completed_count / len(self.individual_bookings)) * 100

    @property
    def next_service(self) -> Optional[BookingResponse]:
        """Get the next service to be completed."""
        if not self.individual_bookings:
            return None

        # Find the first service that is not completed or cancelled
        for booking in sorted(self.individual_bookings, key=lambda b: b.scheduled_at):
            if booking.status in ["pending", "confirmed", "in_progress"]:
                return booking

        return None


class MultiServiceBookingListResponse(BaseModel):
    """Response with list of multi-service bookings."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "bookings": [
                    {
                        "id": 1,
                        "package_name": "Complete Beauty Package",
                        "status": "confirmed",
                        "total_price": 150.00,
                        "total_services_count": 2,
                        "starts_at": "2025-10-20T09:00:00",
                        "completion_percentage": 50.0
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10
            }
        }
    }

    bookings: List[MultiServiceBookingResponse] = Field(default_factory=list, description="List of multi-service bookings")
    total: int = Field(..., description="Total number of bookings")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=10, description="Number of items per page")


class PackageStatisticsResponse(BaseModel):
    """Response with package booking statistics."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_packages": 25,
                "status_breakdown": {
                    "completed": 15,
                    "confirmed": 8,
                    "cancelled": 2
                },
                "total_revenue": 3750.00,
                "average_package_value": 150.00,
                "most_popular_services": [
                    {"service_name": "Haircut + Color", "count": 12},
                    {"service_name": "Manicure + Pedicure", "count": 8}
                ]
            }
        }
    }

    total_packages: int = Field(..., description="Total number of packages")
    status_breakdown: dict = Field(..., description="Count by status")
    total_revenue: float = Field(..., description="Total revenue from packages")
    average_package_value: float = Field(..., description="Average package value")
    most_popular_services: Optional[List[dict]] = Field(None, description="Most popular service combinations")


class ServiceAvailabilityRequest(BaseModel):
    """Request to check availability for multiple services."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "services": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "preferred_start_time": "2025-10-20T09:00:00"
                    },
                    {
                        "service_id": 2,
                        "professional_id": 1,
                        "preferred_start_time": "2025-10-20T10:00:00"
                    }
                ],
                "max_gap_minutes": 30
            }
        }
    }

    services: List[dict] = Field(..., min_items=2, description="Services to check availability for")
    max_gap_minutes: int = Field(default=30, description="Maximum gap allowed between services")


class ServiceAvailabilityResponse(BaseModel):
    """Response with availability for multiple services."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "is_available": True,
                "suggested_times": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "suggested_time": "2025-10-20T09:00:00",
                        "duration_minutes": 60
                    },
                    {
                        "service_id": 2,
                        "professional_id": 1,
                        "suggested_time": "2025-10-20T10:00:00",
                        "duration_minutes": 90
                    }
                ],
                "total_duration_minutes": 150,
                "total_price": 150.00,
                "conflicts": []
            }
        }
    }

    is_available: bool = Field(..., description="Whether all services can be scheduled as requested")
    suggested_times: List[dict] = Field(..., description="Suggested times for each service")
    total_duration_minutes: int = Field(..., description="Total duration for all services")
    total_price: float = Field(..., description="Total price for all services")
    conflicts: List[str] = Field(default_factory=list, description="List of conflicts or issues")
    alternative_suggestions: Optional[List[dict]] = Field(None, description="Alternative time suggestions if requested times not available")


# Aliases for consistent naming
MultiServiceBookingCreate = MultiServiceBookingCreateRequest
MultiServiceBookingUpdate = MultiServiceBookingStatusUpdate
AvailabilityCheckRequest = ServiceAvailabilityRequest
AvailabilityCheckResponse = ServiceAvailabilityResponse


class PackageSuggestionResponse(BaseModel):
    """Response with package suggestion details."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Complete Hair Package",
                "description": "Haircut, wash, and styling",
                "estimated_duration": 120,
                "estimated_price": 150.0,
                "popularity_score": 95,
                "services": ["Haircut", "Hair Wash", "Hair Styling"]
            }
        }
    }

    name: str = Field(..., description="Package name")
    description: str = Field(..., description="Package description")
    estimated_duration: int = Field(..., description="Estimated duration in minutes")
    estimated_price: float = Field(..., description="Estimated price")
    popularity_score: int = Field(..., description="Popularity score (0-100)")
    services: List[str] = Field(..., description="List of service names in the package")


class PricingCalculationResponse(BaseModel):
    """Response with pricing calculation details."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_individual_price": 100.0,
                "discount_percentage": 10.0,
                "discount_amount": 10.0,
                "package_price": 90.0,
                "savings": 10.0,
                "service_details": [
                    {"service_id": 1, "name": "Haircut", "individual_price": 50.0},
                    {"service_id": 2, "name": "Hair Wash", "individual_price": 50.0}
                ]
            }
        }
    }

    total_individual_price: float = Field(..., description="Total price if booked individually")
    discount_percentage: float = Field(..., description="Discount percentage applied")
    discount_amount: float = Field(..., description="Discount amount")
    package_price: float = Field(..., description="Final package price")
    savings: float = Field(..., description="Total savings")
    service_details: List[dict] = Field(..., description="Details of each service")
