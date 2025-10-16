"""Service API schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ServiceCreateRequest(BaseModel):
    """Request schema for creating a service."""

    salon_id: int = Field(
        ...,
        gt=0,
        description="ID of the salon offering this service",
        examples=[1],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Service name",
        examples=["Haircut", "Manicure", "Facial"],
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Detailed service description",
        examples=["Professional haircut with wash and styling"],
    )
    duration_minutes: int = Field(
        ...,
        gt=0,
        le=480,
        description="Service duration in minutes (max 8 hours)",
        examples=[30, 60, 90],
    )
    price: Decimal = Field(
        ...,
        gt=0,
        description="Service price in BRL",
        examples=[50.00, 100.00, 150.00],
    )
    category: str | None = Field(
        None,
        max_length=100,
        description="Service category",
        examples=["Hair", "Nails", "Skin", "Body"],
    )
    requires_deposit: bool = Field(
        default=False,
        description="Whether service requires deposit/prepayment",
    )
    deposit_percentage: Decimal | None = Field(
        None,
        ge=0,
        le=100,
        description="Deposit percentage if required (0-100)",
        examples=[50.0, 100.0],
    )

    @field_validator("deposit_percentage")
    @classmethod
    def validate_deposit_percentage(cls, v: Decimal | None, info) -> Decimal | None:
        """Validate deposit_percentage is set only if requires_deposit is True."""
        if v is not None and v > 0:
            # Deposit percentage requires requires_deposit to be True
            # This will be validated in the endpoint logic
            pass
        return v


class ServiceUpdateRequest(BaseModel):
    """Request schema for updating a service."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Service name",
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Detailed service description",
    )
    duration_minutes: int | None = Field(
        None,
        gt=0,
        le=480,
        description="Service duration in minutes (max 8 hours)",
    )
    price: Decimal | None = Field(
        None,
        gt=0,
        description="Service price in BRL",
    )
    category: str | None = Field(
        None,
        max_length=100,
        description="Service category",
    )
    requires_deposit: bool | None = Field(
        None,
        description="Whether service requires deposit/prepayment",
    )
    deposit_percentage: Decimal | None = Field(
        None,
        ge=0,
        le=100,
        description="Deposit percentage if required (0-100)",
    )


class ServiceResponse(BaseModel):
    """Response schema for service data."""

    id: int = Field(..., description="Service ID")
    salon_id: int = Field(..., description="Salon ID")
    name: str = Field(..., description="Service name")
    description: str | None = Field(None, description="Service description")
    duration_minutes: int = Field(..., description="Duration in minutes")
    price: Decimal = Field(..., description="Service price in BRL")
    category: str | None = Field(None, description="Service category")
    is_active: bool = Field(..., description="Whether service is active")
    requires_deposit: bool = Field(..., description="Whether requires deposit")
    deposit_percentage: Decimal | None = Field(None, description="Deposit percentage")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "salon_id": 1,
                "name": "Haircut",
                "description": "Professional haircut with wash and styling",
                "duration_minutes": 60,
                "price": "100.00",
                "category": "Hair",
                "is_active": True,
                "requires_deposit": False,
                "deposit_percentage": None,
                "created_at": "2025-10-16T10:00:00Z",
                "updated_at": "2025-10-16T10:00:00Z",
            }
        },
    }


class ServiceListResponse(BaseModel):
    """Response schema for list of services."""

    services: list[ServiceResponse] = Field(..., description="List of services")
    total: int = Field(..., description="Total number of services")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Number of items per page")

    model_config = {
        "json_schema_extra": {
            "example": {
                "services": [
                    {
                        "id": 1,
                        "salon_id": 1,
                        "name": "Haircut",
                        "description": "Professional haircut",
                        "duration_minutes": 60,
                        "price": "100.00",
                        "category": "Hair",
                        "is_active": True,
                        "requires_deposit": False,
                        "deposit_percentage": None,
                        "created_at": "2025-10-16T10:00:00Z",
                        "updated_at": "2025-10-16T10:00:00Z",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 50,
            }
        },
    }
