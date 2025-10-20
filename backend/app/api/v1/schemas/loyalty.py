"""API schemas for loyalty system endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from backend.app.db.models.loyalty import (
    LoyaltyTier, PointTransactionType, PointEarnReason, PointRedemptionType
)


# Request Schemas
class LoyaltyAccountCreateRequest(BaseModel):
    """Request to create loyalty account."""

    user_id: int = Field(..., description="User ID to create account for")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123
            }
        }


class PointAwardRequest(BaseModel):
    """Request to award custom points."""

    user_id: int = Field(..., description="User ID to award points to")
    points: int = Field(..., gt=0, description="Number of points to award")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for awarding points")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "points": 500,
                "reason": "Compensation for service issue"
            }
        }


class PointRedemptionRequest(BaseModel):
    """Request to redeem points for discount."""

    points_to_redeem: int = Field(..., gt=0, description="Number of points to redeem")
    booking_id: Optional[int] = Field(None, description="Associated booking ID")

    @validator('points_to_redeem')
    def validate_points_minimum(cls, v):
        if v < 100:  # Minimum 100 points = $1
            raise ValueError('Minimum redemption is 100 points')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "points_to_redeem": 1000,
                "booking_id": 456
            }
        }


class RewardRedemptionRequest(BaseModel):
    """Request to redeem a specific reward."""

    reward_id: int = Field(..., description="ID of reward to redeem")

    class Config:
        json_schema_extra = {
            "example": {
                "reward_id": 789
            }
        }


class TierUpgradeRequest(BaseModel):
    """Request to upgrade user tier (admin)."""

    user_id: int = Field(..., description="User ID to upgrade")
    new_tier: LoyaltyTier = Field(..., description="New tier to assign")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "new_tier": "gold"
            }
        }


class AccountSuspensionRequest(BaseModel):
    """Request to suspend loyalty account."""

    user_id: int = Field(..., description="User ID to suspend")
    suspended_until: Optional[datetime] = Field(None, description="Suspension end date (null for indefinite)")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "suspended_until": "2025-12-31T23:59:59Z"
            }
        }


class RewardCreateRequest(BaseModel):
    """Request to create new loyalty reward."""

    name: str = Field(..., min_length=1, max_length=200, description="Reward name")
    description: Optional[str] = Field(None, max_length=1000, description="Reward description")
    redemption_type: PointRedemptionType = Field(..., description="Type of redemption")
    point_cost: int = Field(..., gt=0, description="Points required to redeem")
    monetary_value: Optional[Decimal] = Field(None, description="Equivalent monetary value")
    is_active: bool = Field(True, description="Whether reward is active")
    available_from: Optional[datetime] = Field(None, description="Availability start date")
    available_until: Optional[datetime] = Field(None, description="Availability end date")
    max_redemptions_per_user: Optional[int] = Field(None, gt=0, description="Max redemptions per user")
    total_available: Optional[int] = Field(None, gt=0, description="Total quantity available")
    minimum_tier: Optional[LoyaltyTier] = Field(None, description="Minimum tier required")
    service_id: Optional[int] = Field(None, description="Associated service ID")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Free Haircut",
                "description": "Complimentary haircut service",
                "redemption_type": "free_service",
                "point_cost": 2000,
                "monetary_value": "50.00",
                "minimum_tier": "silver",
                "service_id": 123
            }
        }


# Response Schemas
class TierBenefitsResponse(BaseModel):
    """Tier benefits information."""

    name: str
    point_multiplier: float
    birthday_bonus: int
    referral_bonus: int
    minimum_points: int
    next_tier_points: Optional[int]


class LoyaltyAccountResponse(BaseModel):
    """Loyalty account information."""

    id: int
    user_id: int
    current_points: int
    lifetime_points: int
    current_tier: LoyaltyTier
    tier_name: str
    tier_points: int
    points_to_next_tier: Optional[int]
    tier_progress_percentage: float
    next_tier_threshold: Optional[int]
    join_date: datetime
    last_activity_date: Optional[datetime]
    is_active: bool
    is_suspended: bool
    suspended_until: Optional[datetime]
    total_bookings: int
    total_spent: Decimal
    referrals_count: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123,
                "current_points": 2500,
                "lifetime_points": 5000,
                "current_tier": "silver",
                "tier_name": "Silver",
                "tier_points": 1500,
                "points_to_next_tier": 1500,
                "tier_progress_percentage": 50.0,
                "next_tier_threshold": 3000,
                "join_date": "2025-01-01T00:00:00Z",
                "last_activity_date": "2025-01-15T10:30:00Z",
                "is_active": True,
                "is_suspended": False,
                "suspended_until": None,
                "total_bookings": 15,
                "total_spent": "750.00",
                "referrals_count": 3
            }
        }


class PointTransactionResponse(BaseModel):
    """Point transaction information."""

    id: int
    transaction_type: PointTransactionType
    points_amount: int
    balance_after: int
    earn_reason: Optional[PointEarnReason]
    redemption_type: Optional[PointRedemptionType]
    monetary_value: Optional[Decimal]
    discount_applied: Optional[Decimal]
    description: Optional[str]
    transaction_date: datetime
    expiry_date: Optional[datetime]
    days_until_expiry: Optional[int]
    is_expired: bool
    booking_id: Optional[int]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "transaction_type": "earned",
                "points_amount": 500,
                "balance_after": 2500,
                "earn_reason": "booking_completed",
                "redemption_type": None,
                "monetary_value": "50.00",
                "discount_applied": None,
                "description": "Points for booking #456",
                "transaction_date": "2025-01-15T10:30:00Z",
                "expiry_date": "2027-01-15T10:30:00Z",
                "days_until_expiry": 730,
                "is_expired": False,
                "booking_id": 456
            }
        }


class LoyaltyRewardResponse(BaseModel):
    """Loyalty reward information."""

    id: int
    name: str
    description: Optional[str]
    redemption_type: PointRedemptionType
    point_cost: int
    monetary_value: Optional[Decimal]
    is_active: bool
    is_available: bool
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    max_redemptions_per_user: Optional[int]
    total_available: Optional[int]
    total_redeemed: int
    remaining_quantity: Optional[int]
    minimum_tier: Optional[LoyaltyTier]
    service_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Free Haircut",
                "description": "Complimentary haircut service",
                "redemption_type": "free_service",
                "point_cost": 2000,
                "monetary_value": "50.00",
                "is_active": True,
                "is_available": True,
                "available_from": None,
                "available_until": None,
                "max_redemptions_per_user": 2,
                "total_available": 100,
                "total_redeemed": 25,
                "remaining_quantity": 75,
                "minimum_tier": "silver",
                "service_id": 123,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        }


class UserRewardResponse(BaseModel):
    """Reward information for user context."""

    id: int
    name: str
    description: Optional[str]
    point_cost: int
    monetary_value: Optional[Decimal]
    redemption_type: PointRedemptionType
    can_redeem: bool
    user_redemptions: int
    max_redemptions: Optional[int]
    remaining_quantity: Optional[int]
    minimum_tier: Optional[LoyaltyTier]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Free Haircut",
                "description": "Complimentary haircut service",
                "point_cost": 2000,
                "monetary_value": "50.00",
                "redemption_type": "free_service",
                "can_redeem": True,
                "user_redemptions": 1,
                "max_redemptions": 2,
                "remaining_quantity": 75,
                "minimum_tier": "silver"
            }
        }


class PointsSummaryResponse(BaseModel):
    """Points summary information."""

    total_earned: int
    total_redeemed: int
    total_expired: int
    total_transactions: int
    net_points: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_earned": 5000,
                "total_redeemed": 2000,
                "total_expired": 500,
                "total_transactions": 50,
                "net_points": 2500
            }
        }


class LoyaltySummaryResponse(BaseModel):
    """Comprehensive loyalty summary."""

    account_id: int
    current_points: int
    lifetime_points: int
    current_tier: str
    tier_name: str
    tier_points: int
    points_to_next_tier: Optional[int]
    tier_progress_percentage: float
    points_expiring_soon: int
    total_bookings: int
    total_spent: float
    referrals_count: int
    is_suspended: bool
    points_summary: PointsSummaryResponse
    tier_benefits: TierBenefitsResponse

    class Config:
        json_schema_extra = {
            "example": {
                "account_id": 1,
                "current_points": 2500,
                "lifetime_points": 5000,
                "current_tier": "silver",
                "tier_name": "Silver",
                "tier_points": 1500,
                "points_to_next_tier": 1500,
                "tier_progress_percentage": 50.0,
                "points_expiring_soon": 200,
                "total_bookings": 15,
                "total_spent": 750.0,
                "referrals_count": 3,
                "is_suspended": False,
                "points_summary": {
                    "total_earned": 5000,
                    "total_redeemed": 2000,
                    "total_expired": 500,
                    "total_transactions": 50,
                    "net_points": 2500
                },
                "tier_benefits": {
                    "name": "Silver",
                    "point_multiplier": 1.2,
                    "birthday_bonus": 200,
                    "referral_bonus": 75,
                    "minimum_points": 1000,
                    "next_tier_points": 3000
                }
            }
        }


class RedemptionResponse(BaseModel):
    """Point redemption result."""

    transaction_id: int
    points_redeemed: int
    discount_amount: Optional[float] = None
    reward_name: Optional[str] = None
    remaining_balance: int

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": 123,
                "points_redeemed": 1000,
                "discount_amount": 10.0,
                "reward_name": None,
                "remaining_balance": 1500
            }
        }


class LoyaltyStatisticsResponse(BaseModel):
    """System-wide loyalty statistics."""

    tier_distribution: Dict[str, int]
    points_statistics: Dict[str, Any]
    redemption_statistics: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "tier_distribution": {
                    "bronze": 150,
                    "silver": 75,
                    "gold": 30,
                    "platinum": 10,
                    "diamond": 5
                },
                "points_statistics": {
                    "total_points_outstanding": 500000,
                    "total_points_issued": 750000,
                    "average_points_per_user": 1852,
                    "total_active_accounts": 270
                },
                "redemption_statistics": {
                    "discount": {
                        "count": 45,
                        "points_redeemed": 50000,
                        "discount_value": 500.0
                    },
                    "free_service": {
                        "count": 12,
                        "points_redeemed": 24000,
                        "discount_value": 600.0
                    }
                }
            }
        }
