"""
API endpoints for notification management.

This module provides REST API endpoints for managing user notification preferences,
notification templates, sending notifications, and tracking delivery history.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.rbac import get_current_user, require_role
from backend.app.db.session import get_db
from backend.app.db.models.user import User, UserRole
from backend.app.api.v1.schemas.notifications import (
    # Request schemas
    PreferenceUpdateRequest,
    BulkPreferenceUpdateRequest,
    NotificationTemplateRequest,
    SendNotificationRequest,

    # Response schemas
    PreferenceResponse,
    NotificationTemplateResponse,
    NotificationQueueResponse,
    NotificationLogResponse,
    SendNotificationResponse,
    NotificationStatisticsResponse,
    PreferenceListResponse,
    TemplateListResponse,
    NotificationHistoryResponse,

    # Enums
    NotificationChannelEnum,
    NotificationEventTypeEnum,
    NotificationStatusEnum,
)
from backend.app.db.models.user import User
from backend.app.db.repositories.notifications import NotificationRepository
from backend.app.services.notifications import NotificationService


router = APIRouter()


# ==================== User Preference Endpoints ====================

@router.get("/preferences", response_model=PreferenceListResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's notification preferences.

    Returns all notification preferences for the authenticated user,
    including enabled/disabled status and channel-specific settings.
    """
    repo = NotificationRepository(db)
    preferences = await repo.get_user_preferences(current_user.id)

    return PreferenceListResponse(
        preferences=[PreferenceResponse.from_orm(pref) for pref in preferences],
        total=len(preferences)
    )


@router.put("/preferences", response_model=PreferenceResponse)
async def update_preference(
    request: PreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a single notification preference.

    Creates or updates a notification preference for the authenticated user.
    If the preference doesn't exist, it will be created with the provided settings.
    """
    repo = NotificationRepository(db)

    preference = await repo.update_user_preference(
        user_id=current_user.id,
        event_type=request.event_type.value,
        channel=request.channel.value,
        enabled=request.enabled,
        advance_minutes=request.advance_minutes,
        quiet_hours_start=request.quiet_hours_start,
        quiet_hours_end=request.quiet_hours_end
    )

    return PreferenceResponse.from_orm(preference)


@router.put("/preferences/bulk", response_model=PreferenceListResponse)
async def update_bulk_preferences(
    request: BulkPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update multiple notification preferences at once.

    Allows bulk updates of notification preferences to efficiently configure
    multiple event types and channels in a single request.
    """
    repo = NotificationRepository(db)
    updated_preferences = []

    for pref_request in request.preferences:
        preference = await repo.update_user_preference(
            user_id=current_user.id,
            event_type=pref_request.event_type.value,
            channel=pref_request.channel.value,
            enabled=pref_request.enabled,
            advance_minutes=pref_request.advance_minutes,
            quiet_hours_start=pref_request.quiet_hours_start,
            quiet_hours_end=pref_request.quiet_hours_end
        )
        updated_preferences.append(preference)

    return PreferenceListResponse(
        preferences=[PreferenceResponse.from_orm(pref) for pref in updated_preferences],
        total=len(updated_preferences)
    )


@router.delete("/preferences/{event_type}/{channel}")
async def delete_preference(
    event_type: NotificationEventTypeEnum,
    channel: NotificationChannelEnum,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a specific notification preference.

    Removes the notification preference for the given event type and channel.
    This will revert to system defaults for that combination.
    """
    repo = NotificationRepository(db)

    success = await repo.delete_user_preference(
        user_id=current_user.id,
        event_type=event_type.value,
        channel=channel.value
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found"
        )

    return {"message": "Preference deleted successfully"}


# ==================== Notification History Endpoints ====================

@router.get("/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    channel: Optional[NotificationChannelEnum] = Query(None, description="Filter by channel"),
    event_type: Optional[NotificationEventTypeEnum] = Query(None, description="Filter by event type"),
    status: Optional[NotificationStatusEnum] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
):
    """
    Get notification history for the current user.

    Returns paginated list of notifications sent to the user with optional filtering
    by channel, event type, status, and date range.
    """
    repo = NotificationRepository(db)

    # Convert enum values to strings for repository call
    channel_value = channel.value if channel else None
    event_type_value = event_type.value if event_type else None
    status_value = status.value if status else None

    notifications, total = await repo.get_user_notification_history(
        user_id=current_user.id,
        page=page,
        limit=limit,
        channel=channel_value,
        event_type=event_type_value,
        status=status_value,
        start_date=start_date,
        end_date=end_date
    )

    return NotificationHistoryResponse(
        notifications=[NotificationLogResponse.from_orm(notif) for notif in notifications],
        total=total,
        page=page,
        limit=limit
    )


# ==================== Send Notification Endpoints ====================

@router.post("/send", response_model=SendNotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a notification to a specific user.

    Queues a notification to be sent to the specified user based on their
    preferences and the provided context data.
    """
    service = NotificationService(db)

    # Convert channel enums to strings if provided
    channels = [ch.value for ch in request.channels] if request.channels else None

    result = await service.send_notification(
        user_id=request.user_id,
        event_type=request.event_type.value,
        context_data=request.context_data,
        priority=request.priority.value,
        channels=channels,
        scheduled_at=request.scheduled_at,
        correlation_id=request.correlation_id
    )

    return SendNotificationResponse(
        message="Notification queued successfully",
        notifications_queued=result["notifications_queued"],
        channels=result["channels"]
    )


# ==================== Admin Template Endpoints ====================

@router.get("/templates", response_model=TemplateListResponse)
async def get_notification_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    event_type: Optional[NotificationEventTypeEnum] = Query(None, description="Filter by event type"),
    channel: Optional[NotificationChannelEnum] = Query(None, description="Filter by channel"),
    locale: Optional[str] = Query("pt_BR", description="Filter by locale"),
    active_only: bool = Query(True, description="Show only active templates"),
):
    """
    Get notification templates (admin only).

    Returns list of notification templates with optional filtering.
    Only accessible by superusers for template management.
    """
    repo = NotificationRepository(db)

    # Convert enum values to strings for repository call
    event_type_value = event_type.value if event_type else None
    channel_value = channel.value if channel else None

    templates = await repo.get_templates(
        event_type=event_type_value,
        channel=channel_value,
        locale=locale,
        active_only=active_only
    )

    return TemplateListResponse(
        templates=[NotificationTemplateResponse.from_orm(template) for template in templates],
        total=len(templates)
    )


@router.post("/templates", response_model=NotificationTemplateResponse)
async def create_notification_template(
    request: NotificationTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Create a new notification template (admin only).

    Creates a new notification template for the specified event type and channel.
    Only accessible by superusers.
    """
    repo = NotificationRepository(db)

    # Check if template with same name already exists
    existing = await repo.get_template_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template with this name already exists"
        )

    template = await repo.create_template(
        name=request.name,
        event_type=request.event_type.value,
        channel=request.channel.value,
        subject=request.subject,
        body_template=request.body_template,
        variables=request.variables,
        priority=request.priority.value,
        locale=request.locale
    )

    return NotificationTemplateResponse.from_orm(template)


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def update_notification_template(
    template_id: int,
    request: NotificationTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Update an existing notification template (admin only).

    Updates the specified notification template with new content.
    Only accessible by superusers.
    """
    repo = NotificationRepository(db)

    template = await repo.update_template(
        template_id=template_id,
        name=request.name,
        event_type=request.event_type.value,
        channel=request.channel.value,
        subject=request.subject,
        body_template=request.body_template,
        variables=request.variables,
        priority=request.priority.value,
        locale=request.locale
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return NotificationTemplateResponse.from_orm(template)


@router.delete("/templates/{template_id}")
async def delete_notification_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete a notification template (admin only).

    Soft deletes the specified notification template by marking it as inactive.
    Only accessible by superusers.
    """
    repo = NotificationRepository(db)

    success = await repo.delete_template(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return {"message": "Template deleted successfully"}


# ==================== Admin Queue Management Endpoints ====================

@router.get("/queue", response_model=List[NotificationQueueResponse])
async def get_notification_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    status: Optional[NotificationStatusEnum] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
):
    """
    Get pending notifications in queue (admin only).

    Returns list of notifications currently queued for processing.
    Only accessible by superusers for queue monitoring.
    """
    repo = NotificationRepository(db)

    status_value = status.value if status else None

    queue_items = await repo.get_pending_notifications(
        limit=limit,
        status=status_value,
        priority=priority
    )

    return [NotificationQueueResponse.from_orm(item) for item in queue_items]


@router.post("/queue/process")
async def process_notification_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    limit: int = Query(50, ge=1, le=200, description="Maximum notifications to process"),
):
    """
    Manually trigger notification queue processing (admin only).

    Processes pending notifications in the queue. This is typically handled
    by background workers, but can be manually triggered for testing.
    Only accessible by superusers.
    """
    service = NotificationService(db)

    results = await service.process_pending_notifications(limit=limit)

    return {
        "message": "Queue processing completed",
        "processed": results["processed"],
        "successful": results["successful"],
        "failed": results["failed"]
    }


# ==================== Statistics Endpoints ====================

@router.get("/statistics", response_model=NotificationStatisticsResponse)
async def get_notification_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    start_date: Optional[datetime] = Query(None, description="Statistics start date"),
    end_date: Optional[datetime] = Query(None, description="Statistics end date"),
):
    """
    Get notification delivery statistics (admin only).

    Returns comprehensive statistics about notification delivery including
    success rates by channel and event type distribution.
    Only accessible by superusers.
    """
    repo = NotificationRepository(db)

    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    stats = await repo.get_notification_statistics(
        start_date=start_date,
        end_date=end_date
    )

    return NotificationStatisticsResponse(
        period={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        total_sent=stats["total_sent"],
        channel_statistics=stats["channel_statistics"],
        event_distribution=stats["event_distribution"]
    )


# ==================== Health Check Endpoints ====================

@router.get("/health")
async def notification_health_check(
    db: AsyncSession = Depends(get_db),
):
    """
    Health check for notification system.

    Returns basic health information about the notification system
    including queue size and recent delivery rates.
    """
    repo = NotificationRepository(db)

    # Get basic queue metrics
    pending_count = len(await repo.get_pending_notifications(limit=1000))

    # Get recent statistics (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_stats = await repo.get_notification_statistics(
        start_date=yesterday,
        end_date=datetime.now()
    )

    return {
        "status": "healthy",
        "queue_size": pending_count,
        "recent_deliveries": recent_stats["total_sent"],
        "timestamp": datetime.now().isoformat()
    }
