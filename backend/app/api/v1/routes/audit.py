"""
Audit event endpoints for querying and managing audit logs.

This module provides comprehensive endpoints for accessing audit events,
including filtering, searching, and reporting capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.rbac import require_role
from backend.app.db.models.audit_event import AuditEventType, AuditEventSeverity
from backend.app.db.models.user import UserRole
from backend.app.db.repositories.audit_event import AuditEventRepository
from backend.app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    """Response model for audit events."""

    id: int
    event_type: str
    severity: str
    user_id: Optional[int]
    session_id: Optional[str]
    user_role: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    endpoint: Optional[str]
    http_method: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    description: Optional[str]
    old_values: Optional[dict]
    new_values: Optional[dict]
    metadata: Optional[dict]
    timestamp: datetime
    correlation_id: Optional[str]
    parent_event_id: Optional[int]
    success: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class AuditEventListResponse(BaseModel):
    """Response model for paginated audit events."""

    events: List[AuditEventResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class AuditStatisticsResponse(BaseModel):
    """Response model for audit statistics."""

    total_events: int
    failed_events: int
    success_rate: float
    events_by_type: dict
    events_by_severity: dict
    top_users_by_activity: dict
    date_range: dict


@router.get(
    "/events",
    response_model=AuditEventListResponse,
    summary="List audit events",
    description="""
    List audit events with comprehensive filtering and pagination.

    **Filtering Options:**
    - `user_id`: Filter by specific user
    - `event_types`: Filter by event types (comma-separated)
    - `severities`: Filter by severity levels (comma-separated)
    - `resource_type`: Filter by resource type (e.g., booking, payment)
    - `resource_id`: Filter by specific resource ID
    - `ip_address`: Filter by IP address
    - `start_date` / `end_date`: Filter by date range
    - `search_term`: Search in descriptions and actions
    - `success_status`: Filter by success/failure

    **Authentication Required:** Admin or Salon Owner
    """,
)
async def list_audit_events(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    severities: Optional[str] = Query(None, description="Comma-separated severity levels"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[datetime] = Query(None, description="Start of date range"),
    end_date: Optional[datetime] = Query(None, description="End of date range"),
    search_term: Optional[str] = Query(None, description="Search in descriptions"),
    success_status: Optional[str] = Query(None, description="Filter by success status"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
    order_by: str = Query("timestamp", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> AuditEventListResponse:
    """List audit events with filtering and pagination."""
    try:
        audit_repo = AuditEventRepository(db)

        # Parse event types
        parsed_event_types = None
        if event_types:
            try:
                parsed_event_types = [
                    AuditEventType(t.strip()) for t in event_types.split(",") if t.strip()
                ]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {e}"
                )

        # Parse severities
        parsed_severities = None
        if severities:
            try:
                parsed_severities = [
                    AuditEventSeverity(s.strip()) for s in severities.split(",") if s.strip()
                ]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity: {e}"
                )

        # Calculate skip
        skip = (page - 1) * page_size

        # Get events
        events, total_count = await audit_repo.list_events(
            user_id=user_id,
            event_types=parsed_event_types,
            severities=parsed_severities,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            start_date=start_date,
            end_date=end_date,
            correlation_id=correlation_id,
            success_status=success_status,
            search_term=search_term,
            skip=skip,
            limit=page_size,
            order_by=order_by,
            order_desc=order_desc,
        )

        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size

        return AuditEventListResponse(
            events=[AuditEventResponse.model_validate(event) for event in events],
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list audit events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit events"
        )


@router.get(
    "/events/{event_id}",
    response_model=AuditEventResponse,
    summary="Get audit event by ID",
    description="Get detailed information about a specific audit event.",
)
async def get_audit_event(
    event_id: int,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> AuditEventResponse:
    """Get audit event by ID."""
    try:
        audit_repo = AuditEventRepository(db)
        event = await audit_repo.get_by_id(event_id)

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit event not found"
            )

        return AuditEventResponse.model_validate(event)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit event {event_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit event"
        )


@router.get(
    "/users/{user_id}/activity",
    response_model=List[AuditEventResponse],
    summary="Get user activity",
    description="Get recent activity for a specific user.",
)
async def get_user_activity(
    user_id: int,
    hours_back: int = Query(24, ge=1, le=168, description="Hours back to look"),
    limit: int = Query(50, ge=1, le=500, description="Maximum events to return"),
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> List[AuditEventResponse]:
    """Get recent activity for a specific user."""
    try:
        audit_repo = AuditEventRepository(db)
        events = await audit_repo.get_user_activity(
            user_id=user_id,
            hours_back=hours_back,
            limit=limit,
        )

        return [AuditEventResponse.model_validate(event) for event in events]

    except Exception as e:
        logger.error(f"Failed to get user activity for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user activity"
        )


@router.get(
    "/security-events",
    response_model=List[AuditEventResponse],
    summary="Get security events",
    description="Get recent security-related events for monitoring.",
)
async def get_security_events(
    hours_back: int = Query(24, ge=1, le=168, description="Hours back to look"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    min_severity: AuditEventSeverity = Query(
        AuditEventSeverity.MEDIUM,
        description="Minimum severity level"
    ),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> List[AuditEventResponse]:
    """Get recent security events."""
    try:
        audit_repo = AuditEventRepository(db)
        events = await audit_repo.get_security_events(
            hours_back=hours_back,
            limit=limit,
            min_severity=min_severity,
        )

        return [AuditEventResponse.model_validate(event) for event in events]

    except Exception as e:
        logger.error(f"Failed to get security events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security events"
        )


@router.get(
    "/resources/{resource_type}/{resource_id}/history",
    response_model=List[AuditEventResponse],
    summary="Get resource history",
    description="Get audit history for a specific resource.",
)
async def get_resource_history(
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum events to return"),
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> List[AuditEventResponse]:
    """Get audit history for a specific resource."""
    try:
        audit_repo = AuditEventRepository(db)
        events = await audit_repo.get_resource_history(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
        )

        return [AuditEventResponse.model_validate(event) for event in events]

    except Exception as e:
        logger.error(f"Failed to get resource history for {resource_type}/{resource_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource history"
        )


@router.get(
    "/correlation/{correlation_id}",
    response_model=List[AuditEventResponse],
    summary="Get related events",
    description="Get all events with the same correlation ID.",
)
async def get_related_events(
    correlation_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum events to return"),
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> List[AuditEventResponse]:
    """Get all events with the same correlation ID."""
    try:
        audit_repo = AuditEventRepository(db)
        events = await audit_repo.get_events_by_correlation(
            correlation_id=correlation_id,
            limit=limit,
        )

        return [AuditEventResponse.model_validate(event) for event in events]

    except Exception as e:
        logger.error(f"Failed to get related events for {correlation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve related events"
        )


@router.get(
    "/statistics",
    response_model=AuditStatisticsResponse,
    summary="Get audit statistics",
    description="Get comprehensive audit statistics and metrics.",
)
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Start of date range"),
    end_date: Optional[datetime] = Query(None, description="End of date range"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> AuditStatisticsResponse:
    """Get audit statistics."""
    try:
        audit_repo = AuditEventRepository(db)

        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        stats = await audit_repo.get_statistics(
            start_date=start_date,
            end_date=end_date,
        )

        return AuditStatisticsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get audit statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit statistics"
        )


@router.delete(
    "/cleanup",
    summary="Clean up old audit events",
    description="""
    Clean up old audit events to manage storage space.

    **Warning:** This operation permanently deletes audit events.
    Only events older than the specified number of days will be deleted.

    **Authentication Required:** Admin only
    """,
)
async def cleanup_old_events(
    days_to_keep: int = Query(365, ge=30, le=3650, description="Days of events to keep"),
    confirm: bool = Query(False, description="Confirmation that you want to delete events"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clean up old audit events."""
    try:
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cleanup must be confirmed with confirm=true parameter"
            )

        audit_repo = AuditEventRepository(db)
        deleted_count = await audit_repo.cleanup_old_events(
            days_to_keep=days_to_keep,
            batch_size=1000,
        )

        logger.info(
            f"Audit cleanup completed by user {current_user.get('id')}: "
            f"{deleted_count} events deleted"
        )

        return {
            "message": "Cleanup completed successfully",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep,
            "performed_by": current_user.get("id"),
            "performed_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup audit events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup audit events"
        )


@router.get(
    "/export",
    summary="Export audit events",
    description="""
    Export audit events as CSV for external analysis.

    **Note:** Large exports may take time to process.
    Consider using date filters to limit the result set.

    **Authentication Required:** Admin only
    """,
)
async def export_audit_events(
    start_date: Optional[datetime] = Query(None, description="Start of date range"),
    end_date: Optional[datetime] = Query(None, description="End of date range"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    format: str = Query("csv", description="Export format (csv only for now)"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Export audit events (placeholder - would return file in real implementation)."""
    try:
        # TODO: Implement actual CSV export
        # This would generate a CSV file and return a download link or stream

        return {
            "message": "Export functionality not yet implemented",
            "note": "This endpoint would generate and return a CSV file with audit events",
            "parameters": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "event_types": event_types,
                "user_id": user_id,
                "format": format,
            },
            "requested_by": current_user.get("id"),
            "requested_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to export audit events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit events"
        )
