"""Professional API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ProfessionalCreateRequest(BaseModel):
    """Schema for creating a new professional."""

    user_id: int = Field(
        ...,
        gt=0,
        description="ID of the user account for this professional",
        examples=[1],
    )
    salon_id: int = Field(
        ...,
        gt=0,
        description="ID of the salon where professional works",
        examples=[1],
    )
    specialties: list[str] = Field(
        default_factory=list,
        description="List of specialties (e.g., haircut, manicure, massage)",
        examples=[["haircut", "coloring", "styling"]],
    )
    bio: str | None = Field(
        default=None,
        max_length=500,
        description="Professional biography and experience",
        examples=["Experienced hair stylist with 10 years in the industry"],
    )
    license_number: str | None = Field(
        default=None,
        max_length=50,
        description="Professional license/registration number",
        examples=["ABC-12345"],
    )
    commission_percentage: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Commission percentage (0-100) for this professional",
        examples=[50.0],
    )

    @field_validator("specialties")
    @classmethod
    def validate_specialties(cls, v: list[str]) -> list[str]:
        """Validate specialties list."""
        if not v:
            return []
        # Remove duplicates and empty strings
        return [s.strip() for s in v if s.strip()]


class ProfessionalUpdateRequest(BaseModel):
    """Schema for updating a professional."""

    specialties: list[str] | None = Field(
        default=None,
        description="List of specialties",
        examples=[["haircut", "coloring"]],
    )
    bio: str | None = Field(
        default=None,
        max_length=500,
        description="Professional biography",
        examples=["Updated bio with new certifications"],
    )
    license_number: str | None = Field(
        default=None,
        max_length=50,
        description="Professional license number",
        examples=["XYZ-67890"],
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether professional is accepting bookings",
        examples=[True],
    )
    commission_percentage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Commission percentage (0-100)",
        examples=[55.0],
    )

    @field_validator("specialties")
    @classmethod
    def validate_specialties(cls, v: list[str] | None) -> list[str] | None:
        """Validate specialties list."""
        if v is None:
            return None
        # Remove duplicates and empty strings
        return [s.strip() for s in v if s.strip()]


class ProfessionalResponse(BaseModel):
    """Schema for professional response."""

    id: int = Field(..., description="Professional ID", examples=[1])
    user_id: int = Field(..., description="User account ID", examples=[1])
    salon_id: int = Field(..., description="Salon ID", examples=[1])
    specialties: list[str] = Field(
        default_factory=list,
        description="List of specialties",
        examples=[["haircut", "coloring"]],
    )
    bio: str | None = Field(
        default=None,
        description="Professional biography",
        examples=["Experienced stylist"],
    )
    license_number: str | None = Field(
        default=None,
        description="License number",
        examples=["ABC-12345"],
    )
    is_active: bool = Field(
        ...,
        description="Active status",
        examples=[True],
    )
    commission_percentage: float = Field(
        ...,
        description="Commission percentage",
        examples=[50.0],
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )

    model_config = {"from_attributes": True}


class ProfessionalListResponse(BaseModel):
    """Schema for paginated list of professionals."""

    professionals: list[ProfessionalResponse] = Field(
        default_factory=list,
        description="List of professionals",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of professionals",
        examples=[10],
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
        examples=[1],
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Number of items per page",
        examples=[10],
    )

    model_config = {"from_attributes": True}
