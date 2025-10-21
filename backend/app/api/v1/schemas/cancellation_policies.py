"""
OpenAPI schemas for cancellation policies endpoints.

This module contains Pydantic models specifically designed for
OpenAPI documentation of cancellation policy endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class CancellationTierSchema(BaseModel):
    """Schema for cancellation policy tier."""

    hours_before: int = Field(
        ...,
        ge=0,
        description="Hours before appointment when this tier applies",
        example=24
    )
    fee_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage fee to charge (0-100)",
        example=50.0
    )
    fee_fixed: Decimal = Field(
        ...,
        ge=0,
        description="Fixed fee amount to charge",
        example=25.00
    )
    description: str = Field(
        ...,
        max_length=200,
        description="Description of this tier",
        example="50% fee for cancellations within 24 hours"
    )


class CancellationPolicyCreateSchema(BaseModel):
    """Schema for creating a cancellation policy."""

    salon_id: int = Field(
        ...,
        gt=0,
        description="ID of the salon this policy applies to",
        example=1
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Policy name",
        example="Standard Cancellation Policy"
    )
    description: str = Field(
        ...,
        max_length=500,
        description="Policy description",
        example="Tiered cancellation policy with increasing fees"
    )
    tiers: List[CancellationTierSchema] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of cancellation tiers (ordered by hours_before)",
        example=[
            {
                "hours_before": 48,
                "fee_percentage": 0.0,
                "fee_fixed": 0.0,
                "description": "Free cancellation 48+ hours before"
            },
            {
                "hours_before": 24,
                "fee_percentage": 25.0,
                "fee_fixed": 0.0,
                "description": "25% fee for 24-48 hours before"
            },
            {
                "hours_before": 0,
                "fee_percentage": 100.0,
                "fee_fixed": 0.0,
                "description": "Full fee for less than 24 hours"
            }
        ]
    )


class CancellationPolicyResponseSchema(BaseModel):
    """Schema for cancellation policy response."""

    id: int = Field(..., description="Policy ID", example=1)
    salon_id: int = Field(..., description="Salon ID", example=1)
    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    status: str = Field(..., description="Policy status", example="active")
    tiers: List[CancellationTierSchema] = Field(..., description="Policy tiers")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: int = Field(..., description="User who created the policy")
    updated_by: Optional[int] = Field(None, description="User who last updated the policy")


class CancellationFeeCalculationSchema(BaseModel):
    """Schema for cancellation fee calculation request."""

    booking_id: int = Field(
        ...,
        gt=0,
        description="Booking ID to calculate fee for",
        example=123
    )
    cancellation_time: Optional[datetime] = Field(
        None,
        description="When the cancellation would occur (defaults to now)",
        example="2025-01-27T14:30:00Z"
    )


class CancellationFeeResponseSchema(BaseModel):
    """Schema for cancellation fee calculation response."""

    booking_id: int = Field(..., description="Booking ID")
    service_price: Decimal = Field(..., description="Original service price")
    hours_before_appointment: float = Field(..., description="Hours between cancellation and appointment")
    applicable_tier: CancellationTierSchema = Field(..., description="Applied cancellation tier")
    fee_percentage: float = Field(..., description="Fee percentage applied")
    fee_fixed: Decimal = Field(..., description="Fixed fee applied")
    total_fee: Decimal = Field(..., description="Total cancellation fee")
    refund_amount: Decimal = Field(..., description="Amount to be refunded")
    calculation_details: dict = Field(
        ...,
        description="Detailed calculation breakdown",
        example={
            "original_price": 100.00,
            "percentage_fee": 25.00,
            "fixed_fee": 0.00,
            "total_fee": 25.00,
            "refund": 75.00
        }
    )


class PolicyApplicationLogSchema(BaseModel):
    """Schema for policy application log."""

    id: int = Field(..., description="Log entry ID")
    booking_id: int = Field(..., description="Booking ID")
    policy_id: int = Field(..., description="Policy ID used")
    tier_applied: CancellationTierSchema = Field(..., description="Tier that was applied")
    calculated_fee: Decimal = Field(..., description="Fee that was calculated")
    applied_at: datetime = Field(..., description="When policy was applied")
    applied_by: int = Field(..., description="User who triggered the application")


class CancellationPolicyListSchema(BaseModel):
    """Schema for cancellation policy list response."""

    policies: List[CancellationPolicyResponseSchema] = Field(..., description="List of policies")
    total: int = Field(..., description="Total number of policies")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    has_next: bool = Field(..., description="Whether there are more pages")
