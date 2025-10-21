"""Schemas for overbooking API endpoints."""

from datetime import datetime, time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

from backend.app.db.models.overbooking import OverbookingScope, OverbookingTimeframe


class OverbookingConfigBase(BaseModel):
    """Base schema for overbooking configuration."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    description: Optional[str] = Field(None, max_length=500, description="Configuration description")
    scope: OverbookingScope = Field(..., description="Configuration scope")
    max_overbooking_percentage: float = Field(..., ge=0, le=100, description="Maximum overbooking percentage (0-100)")
    timeframe: OverbookingTimeframe = Field(default=OverbookingTimeframe.HOURLY, description="Timeframe for overbooking")
    start_time: Optional[time] = Field(None, description="Start time for overbooking")
    end_time: Optional[time] = Field(None, description="End time for overbooking")
    min_historical_bookings: int = Field(default=10, ge=1, description="Minimum historical bookings required")
    historical_period_days: int = Field(default=30, ge=7, le=365, description="Historical period in days")
    min_no_show_rate: float = Field(default=5.0, ge=0, le=100, description="Minimum no-show rate (%)")
    max_no_show_rate: float = Field(default=50.0, ge=0, le=100, description="Maximum no-show rate (%)")
    is_active: bool = Field(default=True, description="Whether configuration is active")
    effective_from: Optional[datetime] = Field(None, description="Effective from date")
    effective_until: Optional[datetime] = Field(None, description="Effective until date")

    @validator('end_time')
    def validate_time_range(cls, v, values):
        """Validate that end_time is after start_time."""
        start_time = values.get('start_time')
        if start_time and v and v <= start_time:
            raise ValueError('end_time must be after start_time')
        return v

    @validator('max_no_show_rate')
    def validate_no_show_rates(cls, v, values):
        """Validate that max_no_show_rate is greater than min_no_show_rate."""
        min_rate = values.get('min_no_show_rate')
        if min_rate and v <= min_rate:
            raise ValueError('max_no_show_rate must be greater than min_no_show_rate')
        return v

    @validator('effective_until')
    def validate_effective_period(cls, v, values):
        """Validate that effective_until is after effective_from."""
        effective_from = values.get('effective_from')
        if effective_from and v and v <= effective_from:
            raise ValueError('effective_until must be after effective_from')
        return v


class OverbookingConfigCreate(OverbookingConfigBase):
    """Schema for creating overbooking configuration."""
    
    salon_id: Optional[int] = Field(None, description="Salon ID (required for salon scope)")
    professional_id: Optional[int] = Field(None, description="Professional ID (required for professional scope)")
    service_id: Optional[int] = Field(None, description="Service ID (required for service scope)")

    @validator('salon_id', always=True)
    def validate_salon_scope(cls, v, values):
        """Validate salon_id is provided for salon scope."""
        scope = values.get('scope')
        if scope == OverbookingScope.SALON and not v:
            raise ValueError('salon_id is required for salon scope')
        elif scope != OverbookingScope.SALON and v:
            raise ValueError('salon_id should only be provided for salon scope')
        return v

    @validator('professional_id', always=True)
    def validate_professional_scope(cls, v, values):
        """Validate professional_id is provided for professional scope."""
        scope = values.get('scope')
        if scope == OverbookingScope.PROFESSIONAL and not v:
            raise ValueError('professional_id is required for professional scope')
        elif scope != OverbookingScope.PROFESSIONAL and v:
            raise ValueError('professional_id should only be provided for professional scope')
        return v

    @validator('service_id', always=True)
    def validate_service_scope(cls, v, values):
        """Validate service_id is provided for service scope."""
        scope = values.get('scope')
        if scope == OverbookingScope.SERVICE and not v:
            raise ValueError('service_id is required for service scope')
        elif scope != OverbookingScope.SERVICE and v:
            raise ValueError('service_id should only be provided for service scope')
        return v


class OverbookingConfigUpdate(BaseModel):
    """Schema for updating overbooking configuration."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    max_overbooking_percentage: Optional[float] = Field(None, ge=0, le=100)
    timeframe: Optional[OverbookingTimeframe] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    min_historical_bookings: Optional[int] = Field(None, ge=1)
    historical_period_days: Optional[int] = Field(None, ge=7, le=365)
    min_no_show_rate: Optional[float] = Field(None, ge=0, le=100)
    max_no_show_rate: Optional[float] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class OverbookingConfigResponse(OverbookingConfigBase):
    """Schema for overbooking configuration response."""
    
    id: int
    salon_id: Optional[int] = None
    professional_id: Optional[int] = None
    service_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CapacityInfo(BaseModel):
    """Schema for capacity information."""
    
    base_capacity: int = Field(..., description="Base capacity without overbooking")
    overbooking_enabled: bool = Field(..., description="Whether overbooking is enabled")
    max_capacity: int = Field(..., description="Maximum capacity including overbooking")
    current_bookings: int = Field(..., description="Current number of bookings")
    available_slots: int = Field(..., description="Available slots for booking")
    overbooking_slots: int = Field(..., description="Additional slots from overbooking")
    no_show_rate: float = Field(..., description="Historical no-show rate percentage")
    config_used: Optional[Dict] = Field(None, description="Configuration used for calculation")
    warnings: List[str] = Field(default=[], description="Warnings about capacity calculation")


class CapacityCheckRequest(BaseModel):
    """Request schema for capacity check."""
    
    professional_id: int = Field(..., description="Professional ID")
    target_datetime: datetime = Field(..., description="Target datetime for booking")
    service_duration_minutes: int = Field(..., gt=0, description="Service duration in minutes")
    salon_id: Optional[int] = Field(None, description="Salon ID")
    service_id: Optional[int] = Field(None, description="Service ID")
    base_capacity: int = Field(default=1, gt=0, description="Base capacity")


class CapacityCheckResponse(BaseModel):
    """Response schema for capacity check."""
    
    can_accept_booking: bool = Field(..., description="Whether booking can be accepted")
    capacity_info: CapacityInfo = Field(..., description="Detailed capacity information")


class OverbookingStatusRequest(BaseModel):
    """Request schema for overbooking status."""
    
    professional_id: int = Field(..., description="Professional ID")
    target_date: str = Field(..., description="Target date (YYYY-MM-DD)")
    salon_id: Optional[int] = Field(None, description="Salon ID")
    service_id: Optional[int] = Field(None, description="Service ID")


class OverbookingStatusResponse(BaseModel):
    """Response schema for overbooking status."""
    
    date: str = Field(..., description="Target date")
    professional_id: int = Field(..., description="Professional ID")
    overbooking_enabled: bool = Field(..., description="Whether overbooking is enabled")
    config: Optional[Dict] = Field(None, description="Overbooking configuration used")
    total_bookings: int = Field(..., description="Total bookings for the date")
    bookings_by_status: Dict[str, int] = Field(..., description="Bookings grouped by status")
    potential_conflicts: int = Field(..., description="Number of potential conflicts")


class NoShowStatistics(BaseModel):
    """Schema for no-show statistics."""
    
    total_bookings: int = Field(..., description="Total bookings in period")
    no_show_bookings: int = Field(..., description="Number of no-show bookings")
    no_show_rate: float = Field(..., description="No-show rate percentage")
    period_start: str = Field(..., description="Start of analysis period")
    period_end: str = Field(..., description="End of analysis period")


class OverbookingAnalyticsResponse(BaseModel):
    """Response schema for overbooking analytics."""
    
    professional_id: int
    salon_id: Optional[int] = None
    service_id: Optional[int] = None
    no_show_statistics: NoShowStatistics
    overbooking_recommendation: Dict = Field(..., description="Recommended overbooking settings")
    current_config: Optional[OverbookingConfigResponse] = None