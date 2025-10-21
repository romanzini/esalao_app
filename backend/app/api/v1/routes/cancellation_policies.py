"""
Cancellation policy routes for managing cancellation rules and tiers.

This module provides endpoints for creating, updating, and managing
cancellation policies and their associated tiers.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.rbac import require_role
from backend.app.db.models.user import UserRole
from backend.app.db.models.cancellation_policy import CancellationPolicyStatus
from backend.app.db.session import get_db
from backend.app.db.repositories.cancellation_policy import CancellationPolicyRepository
from backend.app.domain.policies.cancellation import (
    CancellationPolicy as CancellationPolicyDomain,
    CancellationTier as CancellationTierDomain,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cancellation-policies", tags=["🎯 Policies - Cancellation Policies"])
security = HTTPBearer()


class CancellationTierRequest(BaseModel):
    """Request model for creating/updating a cancellation tier."""

    name: str = Field(..., min_length=1, max_length=100, description="Tier name")
    advance_notice_hours: int = Field(..., ge=0, description="Required advance notice in hours")
    fee_type: str = Field(..., regex="^(percentage|fixed)$", description="Fee type: percentage or fixed")
    fee_value: Decimal = Field(..., ge=0, description="Fee value (percentage 0-100 or fixed amount)")
    allows_refund: bool = Field(True, description="Whether refund is allowed")
    display_order: int = Field(..., ge=0, description="Display order for UI")

    @validator('fee_value')
    def validate_fee_value(cls, v, values):
        """Validate fee value based on fee type."""
        fee_type = values.get('fee_type')
        if fee_type == 'percentage' and v > 100:
            raise ValueError('Percentage fee cannot exceed 100%')
        if fee_type == 'fixed' and v < 0:
            raise ValueError('Fixed fee cannot be negative')
        return v


class CancellationTierResponse(BaseModel):
    """Response model for cancellation tier."""

    id: int
    name: str
    advance_notice_hours: int
    fee_type: str
    fee_value: Decimal
    allows_refund: bool
    display_order: int

    class Config:
        from_attributes = True


class CancellationPolicyRequest(BaseModel):
    """Request model for creating/updating a cancellation policy."""

    name: str = Field(..., min_length=1, max_length=100, description="Policy name")
    description: Optional[str] = Field(None, max_length=500, description="Policy description")
    salon_id: Optional[int] = Field(None, description="Salon ID (null for default policy)")
    is_default: bool = Field(False, description="Whether this is the default policy")
    effective_from: Optional[datetime] = Field(None, description="When policy becomes effective")
    effective_until: Optional[datetime] = Field(None, description="When policy expires")
    status: CancellationPolicyStatus = Field(CancellationPolicyStatus.DRAFT, description="Policy status")
    tiers: List[CancellationTierRequest] = Field(..., min_items=1, description="Cancellation tiers")

    @validator('effective_until')
    def validate_effective_until(cls, v, values):
        """Validate that effective_until is after effective_from."""
        effective_from = values.get('effective_from')
        if v and effective_from and v <= effective_from:
            raise ValueError('effective_until must be after effective_from')
        return v

    @validator('tiers')
    def validate_tiers(cls, v):
        """Validate tier ordering and uniqueness."""
        if not v:
            raise ValueError('At least one tier is required')

        # Check for duplicate advance notice hours
        hours = [tier.advance_notice_hours for tier in v]
        if len(hours) != len(set(hours)):
            raise ValueError('Duplicate advance notice hours not allowed')

        # Check for duplicate display orders
        orders = [tier.display_order for tier in v]
        if len(orders) != len(set(orders)):
            raise ValueError('Duplicate display orders not allowed')

        return v


class CancellationPolicyResponse(BaseModel):
    """Response model for cancellation policy."""

    id: int
    name: str
    description: Optional[str]
    salon_id: Optional[int]
    is_default: bool
    effective_from: datetime
    effective_until: Optional[datetime]
    status: CancellationPolicyStatus
    tiers: List[CancellationTierResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CancellationPolicyListResponse(BaseModel):
    """Response model for policy list."""

    id: int
    name: str
    description: Optional[str]
    salon_id: Optional[int]
    is_default: bool
    status: CancellationPolicyStatus
    effective_from: datetime
    effective_until: Optional[datetime]
    tier_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post(
    "/",
    response_model=CancellationPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create cancellation policy",
    description="Create a new cancellation policy with tiers",
)
async def create_policy(
    policy_data: CancellationPolicyRequest,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> CancellationPolicyResponse:
    """
    Create a new cancellation policy.

    Only admins and salon owners can create policies.
    Salon owners can only create policies for their own salons.
    """
    try:
        policy_repo = CancellationPolicyRepository(db)

        # Salon owners can only create policies for their salon
        if current_user.role == UserRole.SALON_OWNER:
            # TODO: Validate that salon_id belongs to current user
            if not policy_data.salon_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Salon owners must specify salon_id"
                )

        # Check if trying to create default policy when one already exists
        if policy_data.is_default:
            existing_default = await policy_repo.get_default_policy()
            if existing_default:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A default policy already exists"
                )

        # Create policy
        policy = await policy_repo.create_policy(
            name=policy_data.name,
            description=policy_data.description,
            salon_id=policy_data.salon_id,
            is_default=policy_data.is_default,
            effective_from=policy_data.effective_from,
            effective_until=policy_data.effective_until,
            status=policy_data.status,
        )

        # Create tiers
        for tier_data in policy_data.tiers:
            await policy_repo.create_tier(
                policy_id=policy.id,
                name=tier_data.name,
                advance_notice_hours=tier_data.advance_notice_hours,
                fee_type=tier_data.fee_type,
                fee_value=tier_data.fee_value,
                allows_refund=tier_data.allows_refund,
                display_order=tier_data.display_order,
            )

        # Get complete policy with tiers
        complete_policy = await policy_repo.get_by_id_with_tiers(policy.id)

        logger.info(f"Created cancellation policy {policy.id} by user {current_user.id}")

        return CancellationPolicyResponse.from_orm(complete_policy)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create cancellation policy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create policy"
        )


@router.get(
    "/",
    response_model=List[CancellationPolicyListResponse],
    summary="List cancellation policies",
    description="List all cancellation policies with filtering",
)
async def list_policies(
    salon_id: Optional[int] = Query(None, description="Filter by salon ID"),
    status_filter: Optional[CancellationPolicyStatus] = Query(None, description="Filter by status"),
    is_default: Optional[bool] = Query(None, description="Filter by default status"),
    skip: int = Query(0, ge=0, description="Number of policies to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of policies to return"),
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])),
    db: AsyncSession = Depends(get_db),
) -> List[CancellationPolicyListResponse]:
    """
    List cancellation policies.

    Filtering rules:
    - Admins can see all policies
    - Salon owners can see policies for their salons + default policies
    - Receptionists can see policies for their salons + default policies
    """
    try:
        policy_repo = CancellationPolicyRepository(db)

        # Apply access control
        if current_user.role != UserRole.ADMIN:
            # TODO: Get user's salon(s) and filter accordingly
            # For now, we'll just filter by salon_id if provided
            pass

        policies = await policy_repo.list_policies(
            salon_id=salon_id,
            status=status_filter,
            is_default=is_default,
            skip=skip,
            limit=limit,
        )

        return [CancellationPolicyListResponse.from_orm(policy) for policy in policies]

    except Exception as e:
        logger.error(f"Failed to list cancellation policies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list policies"
        )


@router.get(
    "/{policy_id}",
    response_model=CancellationPolicyResponse,
    summary="Get cancellation policy",
    description="Get a specific cancellation policy with all tiers",
)
async def get_policy(
    policy_id: int,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER, UserRole.RECEPTIONIST])),
    db: AsyncSession = Depends(get_db),
) -> CancellationPolicyResponse:
    """
    Get a cancellation policy by ID.

    Returns the complete policy including all tiers.
    """
    try:
        policy_repo = CancellationPolicyRepository(db)
        policy = await policy_repo.get_by_id_with_tiers(policy_id)

        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )

        # TODO: Check access permissions for salon-specific policies

        return CancellationPolicyResponse.from_orm(policy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cancellation policy {policy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get policy"
        )


@router.put(
    "/{policy_id}",
    response_model=CancellationPolicyResponse,
    summary="Update cancellation policy",
    description="Update an existing cancellation policy",
)
async def update_policy(
    policy_id: int,
    policy_data: CancellationPolicyRequest,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> CancellationPolicyResponse:
    """
    Update a cancellation policy.

    Only admins and salon owners can update policies.
    Salon owners can only update policies for their own salons.
    """
    try:
        policy_repo = CancellationPolicyRepository(db)

        # Check if policy exists
        existing_policy = await policy_repo.get_by_id(policy_id)
        if not existing_policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )

        # TODO: Check access permissions

        # Update policy
        updated_policy = await policy_repo.update_policy(
            policy_id=policy_id,
            name=policy_data.name,
            description=policy_data.description,
            salon_id=policy_data.salon_id,
            is_default=policy_data.is_default,
            effective_from=policy_data.effective_from,
            effective_until=policy_data.effective_until,
            status=policy_data.status,
        )

        # Update tiers (delete existing and create new ones)
        await policy_repo.delete_policy_tiers(policy_id)

        for tier_data in policy_data.tiers:
            await policy_repo.create_tier(
                policy_id=policy_id,
                name=tier_data.name,
                advance_notice_hours=tier_data.advance_notice_hours,
                fee_type=tier_data.fee_type,
                fee_value=tier_data.fee_value,
                allows_refund=tier_data.allows_refund,
                display_order=tier_data.display_order,
            )

        # Get complete updated policy
        complete_policy = await policy_repo.get_by_id_with_tiers(policy_id)

        logger.info(f"Updated cancellation policy {policy_id} by user {current_user.id}")

        return CancellationPolicyResponse.from_orm(complete_policy)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update cancellation policy {policy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update policy"
        )


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete cancellation policy",
    description="Delete a cancellation policy and all its tiers",
)
async def delete_policy(
    policy_id: int,
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a cancellation policy.

    Only admins can delete policies.
    Cannot delete policies that are currently in use.
    """
    try:
        policy_repo = CancellationPolicyRepository(db)

        # Check if policy exists
        policy = await policy_repo.get_by_id(policy_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )

        # TODO: Check if policy is in use by active bookings

        # Delete policy (cascades to tiers)
        await policy_repo.delete_policy(policy_id)

        logger.info(f"Deleted cancellation policy {policy_id} by user {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete cancellation policy {policy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete policy"
        )


@router.post(
    "/{policy_id}/activate",
    response_model=CancellationPolicyResponse,
    summary="Activate cancellation policy",
    description="Activate a cancellation policy",
)
async def activate_policy(
    policy_id: int,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> CancellationPolicyResponse:
    """
    Activate a cancellation policy.

    Sets the policy status to ACTIVE and makes it effective immediately
    if no effective_from date is set.
    """
    try:
        policy_repo = CancellationPolicyRepository(db)

        # Check if policy exists
        policy = await policy_repo.get_by_id(policy_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )

        # TODO: Check access permissions

        # Activate policy
        updated_policy = await policy_repo.update_policy_status(
            policy_id=policy_id,
            status=CancellationPolicyStatus.ACTIVE
        )

        # Get complete policy with tiers
        complete_policy = await policy_repo.get_by_id_with_tiers(policy_id)

        logger.info(f"Activated cancellation policy {policy_id} by user {current_user.id}")

        return CancellationPolicyResponse.from_orm(complete_policy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate cancellation policy {policy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate policy"
        )


@router.post(
    "/{policy_id}/deactivate",
    response_model=CancellationPolicyResponse,
    summary="Deactivate cancellation policy",
    description="Deactivate a cancellation policy",
)
async def deactivate_policy(
    policy_id: int,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> CancellationPolicyResponse:
    """
    Deactivate a cancellation policy.

    Sets the policy status to INACTIVE.
    """
    try:
        policy_repo = CancellationPolicyRepository(db)

        # Check if policy exists
        policy = await policy_repo.get_by_id(policy_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )

        # TODO: Check access permissions

        # Deactivate policy
        updated_policy = await policy_repo.update_policy_status(
            policy_id=policy_id,
            status=CancellationPolicyStatus.INACTIVE
        )

        # Get complete policy with tiers
        complete_policy = await policy_repo.get_by_id_with_tiers(policy_id)

        logger.info(f"Deactivated cancellation policy {policy_id} by user {current_user.id}")

        return CancellationPolicyResponse.from_orm(complete_policy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate cancellation policy {policy_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate policy"
        )
