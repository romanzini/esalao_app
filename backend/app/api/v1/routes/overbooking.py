"""Overbooking management API routes."""

import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.schemas.overbooking import (
    CapacityCheckRequest,
    CapacityCheckResponse,
    OverbookingConfigCreate,
    OverbookingConfigResponse,
    OverbookingConfigUpdate,
    OverbookingStatusRequest,
    OverbookingStatusResponse,
    OverbookingAnalyticsResponse
)
from backend.app.core.security.rbac import get_current_user, require_role
from backend.app.db.models.overbooking import OverbookingScope
from backend.app.db.models.user import User, UserRole
from backend.app.db.session import get_db
from backend.app.services.overbooking import OverbookingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/overbooking", tags=["📈 Overbooking Management"])


@router.post(
    "/configs",
    response_model=OverbookingConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create overbooking configuration",
    description="""
    Create a new overbooking configuration.

    This endpoint allows administrators and salon owners to configure
    overbooking rules for different scopes (global, salon, professional, service).

    **Authentication Required:** Admin or Salon Owner

    **Configuration Scopes:**
    - **Global**: Platform-wide default settings
    - **Salon**: Salon-specific settings
    - **Professional**: Professional-specific settings
    - **Service**: Service-specific settings

    **Business Rules:**
    - Only one active configuration per scope combination
    - Requires historical data to enable overbooking
    - No-show rate must be within configured thresholds
    """,
)
async def create_overbooking_config(
    config_data: OverbookingConfigCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create overbooking configuration."""
    # Permission check
    if current_user.role not in [UserRole.ADMIN, UserRole.SALON_OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and salon owners can create overbooking configurations"
        )

    # Additional validation for salon owners
    if current_user.role == UserRole.SALON_OWNER:
        if config_data.scope == OverbookingScope.GLOBAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Salon owners cannot create global configurations"
            )

        # TODO: Validate salon ownership for salon-scoped configs
        # if config_data.scope == OverbookingScope.SALON and config_data.salon_id != current_user.salon_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Can only create configurations for your own salon"
        #     )

    try:
        overbooking_service = OverbookingService(session)
        config = await overbooking_service.create_configuration(config_data.dict())

        logger.info(
            f"Overbooking configuration created by user {current_user.id}: "
            f"{config.name} (scope: {config.scope.value})"
        )

        return config

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create overbooking configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create overbooking configuration"
        )


@router.get(
    "/configs",
    response_model=List[OverbookingConfigResponse],
    summary="List overbooking configurations",
    description="""
    List overbooking configurations with optional filtering.

    **Authentication Required:** Admin, Salon Owner, or Professional

    **Query Parameters:**
    - **scope**: Filter by configuration scope
    - **scope_id**: Filter by scope-specific ID
    - **include_inactive**: Include inactive configurations
    """,
)
async def list_overbooking_configs(
    scope: Optional[OverbookingScope] = Query(None, description="Filter by scope"),
    scope_id: Optional[int] = Query(None, description="Filter by scope ID"),
    include_inactive: bool = Query(False, description="Include inactive configurations"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List overbooking configurations."""
    overbooking_service = OverbookingService(session)

    if scope:
        configs = await overbooking_service.overbooking_repo.list_by_scope(
            scope=scope,
            scope_id=scope_id,
            include_inactive=include_inactive
        )
    else:
        configs = await overbooking_service.overbooking_repo.list_all(
            include_inactive=include_inactive
        )

    # Filter based on user permissions
    if current_user.role == UserRole.SALON_OWNER:
        # TODO: Filter to only show configs for user's salon
        pass
    elif current_user.role == UserRole.PROFESSIONAL:
        # TODO: Filter to only show configs relevant to professional
        pass

    return configs


@router.get(
    "/configs/{config_id}",
    response_model=OverbookingConfigResponse,
    summary="Get overbooking configuration",
    description="Get specific overbooking configuration by ID.",
)
async def get_overbooking_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get overbooking configuration by ID."""
    overbooking_service = OverbookingService(session)
    config = await overbooking_service.overbooking_repo.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overbooking configuration not found"
        )

    return config


@router.put(
    "/configs/{config_id}",
    response_model=OverbookingConfigResponse,
    summary="Update overbooking configuration",
    description="Update existing overbooking configuration.",
)
async def update_overbooking_config(
    config_id: int,
    update_data: OverbookingConfigUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    session: AsyncSession = Depends(get_db),
):
    """Update overbooking configuration."""
    overbooking_service = OverbookingService(session)

    # Get existing config
    config = await overbooking_service.overbooking_repo.get_by_id(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overbooking configuration not found"
        )

    try:
        # Update configuration
        updated_config = await overbooking_service.overbooking_repo.update(
            config_id, update_data.dict(exclude_unset=True)
        )
        await session.commit()

        logger.info(f"Overbooking configuration {config_id} updated by user {current_user.id}")
        return updated_config

    except Exception as e:
        logger.error(f"Failed to update overbooking configuration {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update overbooking configuration"
        )


@router.delete(
    "/configs/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete overbooking configuration",
    description="Delete overbooking configuration.",
)
async def delete_overbooking_config(
    config_id: int,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    session: AsyncSession = Depends(get_db),
):
    """Delete overbooking configuration."""
    overbooking_service = OverbookingService(session)

    success = await overbooking_service.overbooking_repo.delete(config_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overbooking configuration not found"
        )

    await session.commit()
    logger.info(f"Overbooking configuration {config_id} deleted by user {current_user.id}")


@router.post(
    "/capacity/check",
    response_model=CapacityCheckResponse,
    summary="Check booking capacity",
    description="""
    Check if a booking can be accepted considering overbooking rules.

    This endpoint analyzes:
    - Current bookings for the time slot
    - Applicable overbooking configuration
    - Historical no-show data
    - Capacity calculations

    **Returns:**
    - Whether booking can be accepted
    - Detailed capacity information
    - Warnings if any issues detected
    """,
)
async def check_booking_capacity(
    request: CapacityCheckRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Check booking capacity with overbooking considerations."""
    try:
        overbooking_service = OverbookingService(session)

        can_accept, capacity_info = await overbooking_service.can_accept_booking(
            professional_id=request.professional_id,
            target_datetime=request.target_datetime,
            service_duration_minutes=request.service_duration_minutes,
            salon_id=request.salon_id,
            service_id=request.service_id
        )

        return CapacityCheckResponse(
            can_accept_booking=can_accept,
            capacity_info=capacity_info
        )

    except Exception as e:
        logger.error(f"Failed to check booking capacity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check booking capacity"
        )


@router.post(
    "/status",
    response_model=OverbookingStatusResponse,
    summary="Get overbooking status",
    description="""
    Get overbooking status for a specific date and professional.

    **Returns:**
    - Overbooking configuration details
    - Current bookings breakdown
    - Potential conflict analysis
    """,
)
async def get_overbooking_status(
    request: OverbookingStatusRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get overbooking status for a date."""
    try:
        target_date = datetime.strptime(request.target_date, "%Y-%m-%d").date()

        overbooking_service = OverbookingService(session)
        status_info = await overbooking_service.get_overbooking_status(
            professional_id=request.professional_id,
            target_date=target_date,
            salon_id=request.salon_id,
            service_id=request.service_id
        )

        return OverbookingStatusResponse(**status_info)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to get overbooking status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get overbooking status"
        )


@router.get(
    "/analytics/{professional_id}",
    response_model=OverbookingAnalyticsResponse,
    summary="Get overbooking analytics",
    description="""
    Get analytics and recommendations for overbooking configuration.

    **Authentication Required:** Admin, Salon Owner, or the Professional

    **Analytics Include:**
    - Historical no-show statistics
    - Recommended overbooking settings
    - Current configuration assessment
    """,
)
async def get_overbooking_analytics(
    professional_id: int,
    salon_id: Optional[int] = Query(None, description="Salon ID for analysis"),
    service_id: Optional[int] = Query(None, description="Service ID for analysis"),
    period_days: int = Query(30, ge=7, le=365, description="Analysis period in days"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get overbooking analytics for a professional."""
    # TODO: Add permission check for professional access

    try:
        overbooking_service = OverbookingService(session)

        # Get no-show statistics
        no_show_stats = await overbooking_service._get_no_show_statistics(
            professional_id=professional_id,
            salon_id=salon_id,
            service_id=service_id,
            historical_period_days=period_days
        )

        # Get current configuration
        current_config = await overbooking_service.overbooking_repo.get_effective_config(
            salon_id=salon_id,
            professional_id=professional_id,
            service_id=service_id
        )

        # Generate recommendations
        recommendation = _generate_overbooking_recommendation(no_show_stats)

        return OverbookingAnalyticsResponse(
            professional_id=professional_id,
            salon_id=salon_id,
            service_id=service_id,
            no_show_statistics=no_show_stats,
            overbooking_recommendation=recommendation,
            current_config=current_config
        )

    except Exception as e:
        logger.error(f"Failed to get overbooking analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get overbooking analytics"
        )


def _generate_overbooking_recommendation(no_show_stats: dict) -> dict:
    """Generate overbooking recommendation based on statistics."""
    no_show_rate = no_show_stats["no_show_rate"]
    total_bookings = no_show_stats["total_bookings"]

    recommendation = {
        "recommended_enabled": False,
        "recommended_percentage": 0.0,
        "confidence": "low",
        "reasons": []
    }

    # Insufficient data
    if total_bookings < 20:
        recommendation["reasons"].append(
            f"Insufficient historical data ({total_bookings} bookings, need at least 20)"
        )
        return recommendation

    # Low no-show rate
    if no_show_rate < 5:
        recommendation["reasons"].append(
            f"No-show rate too low ({no_show_rate:.1f}%, need at least 5%)"
        )
        return recommendation

    # Very high no-show rate (risky)
    if no_show_rate > 50:
        recommendation["reasons"].append(
            f"No-show rate too high ({no_show_rate:.1f}%, maximum 50%)"
        )
        return recommendation

    # Good candidate for overbooking
    recommendation["recommended_enabled"] = True
    recommendation["confidence"] = "high" if total_bookings >= 50 else "medium"

    # Calculate recommended percentage (conservative approach)
    if 5 <= no_show_rate <= 15:
        recommendation["recommended_percentage"] = min(no_show_rate * 0.8, 12.0)
    elif 15 < no_show_rate <= 30:
        recommendation["recommended_percentage"] = min(no_show_rate * 0.7, 20.0)
    else:  # 30-50%
        recommendation["recommended_percentage"] = min(no_show_rate * 0.6, 25.0)

    recommendation["reasons"].append(
        f"Good candidate: {no_show_rate:.1f}% no-show rate with {total_bookings} historical bookings"
    )

    return recommendation
