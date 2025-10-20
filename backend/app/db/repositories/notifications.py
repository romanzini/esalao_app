"""
Repository for notification operations.

This module handles database operations for notification preferences,
templates, queue management, and delivery tracking.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from sqlalchemy import select, update, delete, and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.notifications import (
    NotificationPreferences, NotificationTemplate, NotificationQueue, NotificationLog,
    NotificationChannel, NotificationEventType, NotificationPriority, NotificationStatus
)
from backend.app.db.models.user import User
from backend.app.core.exceptions import NotFoundError, ValidationError


class NotificationRepository:
    """Repository for notification-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Notification Preferences ====================

    async def get_user_preferences(
        self,
        user_id: int,
        event_type: Optional[NotificationEventType] = None,
        channel: Optional[NotificationChannel] = None
    ) -> List[NotificationPreferences]:
        """Get user notification preferences with optional filtering."""
        query = select(NotificationPreferences).where(
            NotificationPreferences.user_id == user_id
        )

        if event_type:
            query = query.where(NotificationPreferences.event_type == event_type)
        if channel:
            query = query.where(NotificationPreferences.channel == channel)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def set_user_preference(
        self,
        user_id: int,
        event_type: NotificationEventType,
        channel: NotificationChannel,
        enabled: bool,
        advance_minutes: Optional[int] = None,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None
    ) -> NotificationPreferences:
        """Set or update a user's notification preference."""
        # Check if preference already exists
        existing = await self.session.execute(
            select(NotificationPreferences).where(
                and_(
                    NotificationPreferences.user_id == user_id,
                    NotificationPreferences.event_type == event_type,
                    NotificationPreferences.channel == channel
                )
            )
        )
        preference = existing.scalar_one_or_none()

        if preference:
            # Update existing
            preference.enabled = enabled
            preference.advance_minutes = advance_minutes
            preference.quiet_hours_start = quiet_hours_start
            preference.quiet_hours_end = quiet_hours_end
            preference.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            preference = NotificationPreferences(
                user_id=user_id,
                event_type=event_type,
                channel=channel,
                enabled=enabled,
                advance_minutes=advance_minutes,
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end
            )
            self.session.add(preference)

        await self.session.commit()
        await self.session.refresh(preference)
        return preference

    async def get_enabled_channels_for_user(
        self,
        user_id: int,
        event_type: NotificationEventType
    ) -> List[NotificationChannel]:
        """Get enabled notification channels for a user and event type."""
        result = await self.session.execute(
            select(NotificationPreferences.channel).where(
                and_(
                    NotificationPreferences.user_id == user_id,
                    NotificationPreferences.event_type == event_type,
                    NotificationPreferences.enabled == True
                )
            )
        )
        return [row[0] for row in result.all()]

    async def setup_default_preferences(self, user_id: int) -> List[NotificationPreferences]:
        """Set up default notification preferences for a new user."""
        default_configs = [
            # Email preferences (most events enabled)
            (NotificationEventType.BOOKING_CONFIRMED, NotificationChannel.EMAIL, True, None),
            (NotificationEventType.BOOKING_REMINDER, NotificationChannel.EMAIL, True, 60),
            (NotificationEventType.BOOKING_CANCELLED, NotificationChannel.EMAIL, True, None),
            (NotificationEventType.PAYMENT_RECEIVED, NotificationChannel.EMAIL, True, None),
            (NotificationEventType.POINTS_EARNED, NotificationChannel.EMAIL, True, None),
            (NotificationEventType.TIER_UPGRADED, NotificationChannel.EMAIL, True, None),

            # SMS preferences (critical events only)
            (NotificationEventType.BOOKING_CONFIRMED, NotificationChannel.SMS, True, None),
            (NotificationEventType.BOOKING_REMINDER, NotificationChannel.SMS, True, 30),
            (NotificationEventType.BOOKING_CANCELLED, NotificationChannel.SMS, True, None),
            (NotificationEventType.PAYMENT_FAILED, NotificationChannel.SMS, True, None),

            # Push preferences (timely events)
            (NotificationEventType.BOOKING_REMINDER, NotificationChannel.PUSH, True, 15),
            (NotificationEventType.SLOT_AVAILABLE, NotificationChannel.PUSH, True, None),
            (NotificationEventType.POINTS_EARNED, NotificationChannel.PUSH, True, None),

            # In-app preferences (all events)
            (NotificationEventType.BOOKING_CONFIRMED, NotificationChannel.IN_APP, True, None),
            (NotificationEventType.BOOKING_REMINDER, NotificationChannel.IN_APP, True, 5),
            (NotificationEventType.POINTS_EARNED, NotificationChannel.IN_APP, True, None),
            (NotificationEventType.REWARD_AVAILABLE, NotificationChannel.IN_APP, True, None),
        ]

        preferences = []
        for event_type, channel, enabled, advance_minutes in default_configs:
            pref = NotificationPreferences(
                user_id=user_id,
                event_type=event_type,
                channel=channel,
                enabled=enabled,
                advance_minutes=advance_minutes
            )
            self.session.add(pref)
            preferences.append(pref)

        await self.session.commit()
        return preferences

    # ==================== Notification Templates ====================

    async def get_template(
        self,
        event_type: NotificationEventType,
        channel: NotificationChannel,
        locale: str = "pt_BR"
    ) -> Optional[NotificationTemplate]:
        """Get notification template for event type, channel, and locale."""
        result = await self.session.execute(
            select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.event_type == event_type,
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.locale == locale,
                    NotificationTemplate.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_template(
        self,
        name: str,
        event_type: NotificationEventType,
        channel: NotificationChannel,
        subject: Optional[str],
        body_template: str,
        variables: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        locale: str = "pt_BR"
    ) -> NotificationTemplate:
        """Create a new notification template."""
        template = NotificationTemplate(
            name=name,
            event_type=event_type,
            channel=channel,
            subject=subject,
            body_template=body_template,
            variables=variables,
            priority=priority,
            locale=locale
        )
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def update_template(
        self,
        template_id: int,
        **updates
    ) -> NotificationTemplate:
        """Update an existing notification template."""
        template = await self.session.get(NotificationTemplate, template_id)
        if not template:
            raise NotFoundError(f"Template with ID {template_id} not found")

        for field, value in updates.items():
            if hasattr(template, field):
                setattr(template, field, value)

        template.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def list_templates(
        self,
        event_type: Optional[NotificationEventType] = None,
        channel: Optional[NotificationChannel] = None,
        active_only: bool = True
    ) -> List[NotificationTemplate]:
        """List notification templates with optional filtering."""
        query = select(NotificationTemplate)

        if event_type:
            query = query.where(NotificationTemplate.event_type == event_type)
        if channel:
            query = query.where(NotificationTemplate.channel == channel)
        if active_only:
            query = query.where(NotificationTemplate.is_active == True)

        query = query.order_by(NotificationTemplate.event_type, NotificationTemplate.channel)

        result = await self.session.execute(query)
        return result.scalars().all()

    # ==================== Notification Queue ====================

    async def queue_notification(
        self,
        user_id: int,
        template_id: int,
        channel: NotificationChannel,
        context_data: Dict[str, Any],
        subject: Optional[str] = None,
        body: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        max_retries: int = 3
    ) -> NotificationQueue:
        """Queue a notification for delivery."""
        notification = NotificationQueue(
            user_id=user_id,
            template_id=template_id,
            channel=channel,
            priority=priority,
            subject=subject,
            body=body or "",  # Will be rendered later if empty
            context_data=context_data,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
            correlation_id=correlation_id,
            max_retries=max_retries
        )
        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def get_pending_notifications(
        self,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
        priority: Optional[NotificationPriority] = None
    ) -> List[NotificationQueue]:
        """Get pending notifications ready for delivery."""
        query = (
            select(NotificationQueue)
            .options(selectinload(NotificationQueue.user))
            .options(selectinload(NotificationQueue.template))
            .where(
                and_(
                    NotificationQueue.status.in_([
                        NotificationStatus.PENDING,
                        NotificationStatus.QUEUED
                    ]),
                    NotificationQueue.scheduled_at <= datetime.now(timezone.utc)
                )
            )
            .order_by(
                NotificationQueue.priority.desc(),
                NotificationQueue.scheduled_at.asc()
            )
            .limit(limit)
        )

        if channel:
            query = query.where(NotificationQueue.channel == channel)
        if priority:
            query = query.where(NotificationQueue.priority == priority)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_notifications_for_retry(
        self,
        limit: int = 50
    ) -> List[NotificationQueue]:
        """Get notifications that need retry."""
        now = datetime.now(timezone.utc)
        query = (
            select(NotificationQueue)
            .options(selectinload(NotificationQueue.user))
            .options(selectinload(NotificationQueue.template))
            .where(
                and_(
                    NotificationQueue.status == NotificationStatus.RETRYING,
                    NotificationQueue.next_retry_at <= now,
                    NotificationQueue.retry_count < NotificationQueue.max_retries
                )
            )
            .order_by(NotificationQueue.next_retry_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_notification_status(
        self,
        notification_id: int,
        status: NotificationStatus,
        external_id: Optional[str] = None,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        increment_retry: bool = False
    ) -> NotificationQueue:
        """Update notification status and metadata."""
        notification = await self.session.get(NotificationQueue, notification_id)
        if not notification:
            raise NotFoundError(f"Notification with ID {notification_id} not found")

        notification.status = status
        if external_id:
            notification.external_id = external_id
        if error_message:
            notification.last_error = error_message
        if sent_at:
            notification.sent_at = sent_at

        if increment_retry:
            notification.retry_count += 1
            if notification.retry_count < notification.max_retries:
                # Schedule next retry with exponential backoff
                delay_minutes = 2 ** notification.retry_count  # 2, 4, 8 minutes
                notification.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                notification.status = NotificationStatus.RETRYING

        notification.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def cancel_notifications(
        self,
        correlation_id: str,
        reason: str = "Cancelled by system"
    ) -> int:
        """Cancel pending notifications by correlation ID."""
        result = await self.session.execute(
            update(NotificationQueue)
            .where(
                and_(
                    NotificationQueue.correlation_id == correlation_id,
                    NotificationQueue.status.in_([
                        NotificationStatus.PENDING,
                        NotificationStatus.QUEUED,
                        NotificationStatus.RETRYING
                    ])
                )
            )
            .values(
                status=NotificationStatus.CANCELLED,
                last_error=reason,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.commit()
        return result.rowcount

    # ==================== Notification Logs ====================

    async def log_notification(
        self,
        queue_id: Optional[int],
        user_id: int,
        channel: NotificationChannel,
        event_type: NotificationEventType,
        status: NotificationStatus,
        subject: Optional[str] = None,
        external_id: Optional[str] = None,
        provider_response: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        delivered_at: Optional[datetime] = None
    ) -> NotificationLog:
        """Log a notification delivery attempt."""
        log_entry = NotificationLog(
            queue_id=queue_id,
            user_id=user_id,
            channel=channel,
            event_type=event_type,
            status=status,
            subject=subject,
            external_id=external_id,
            provider_response=provider_response,
            error_message=error_message,
            error_code=error_code,
            correlation_id=correlation_id,
            delivered_at=delivered_at
        )
        self.session.add(log_entry)
        await self.session.commit()
        await self.session.refresh(log_entry)
        return log_entry

    async def get_user_notification_history(
        self,
        user_id: int,
        event_type: Optional[NotificationEventType] = None,
        channel: Optional[NotificationChannel] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[NotificationLog]:
        """Get notification history for a user."""
        query = (
            select(NotificationLog)
            .where(NotificationLog.user_id == user_id)
            .order_by(desc(NotificationLog.sent_at))
            .limit(limit)
            .offset(offset)
        )

        if event_type:
            query = query.where(NotificationLog.event_type == event_type)
        if channel:
            query = query.where(NotificationLog.channel == channel)

        result = await self.session.execute(query)
        return result.scalars().all()

    # ==================== Analytics and Reporting ====================

    async def get_notification_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification delivery statistics."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Total notifications sent
        total_result = await self.session.execute(
            select(func.count(NotificationLog.id))
            .where(
                and_(
                    NotificationLog.sent_at >= start_date,
                    NotificationLog.sent_at <= end_date
                )
            )
        )
        total_sent = total_result.scalar() or 0

        # Success rate by channel
        channel_stats = await self.session.execute(
            select(
                NotificationLog.channel,
                func.count(NotificationLog.id).label("total"),
                func.sum(
                    func.case(
                        (NotificationLog.status.in_([
                            NotificationStatus.SENT,
                            NotificationStatus.DELIVERED
                        ]), 1),
                        else_=0
                    )
                ).label("successful")
            )
            .where(
                and_(
                    NotificationLog.sent_at >= start_date,
                    NotificationLog.sent_at <= end_date
                )
            )
            .group_by(NotificationLog.channel)
        )

        channel_data = {}
        for row in channel_stats:
            channel_data[row.channel.value] = {
                "total": row.total,
                "successful": row.successful,
                "success_rate": (row.successful / row.total * 100) if row.total > 0 else 0
            }

        # Event type distribution
        event_stats = await self.session.execute(
            select(
                NotificationLog.event_type,
                func.count(NotificationLog.id).label("count")
            )
            .where(
                and_(
                    NotificationLog.sent_at >= start_date,
                    NotificationLog.sent_at <= end_date
                )
            )
            .group_by(NotificationLog.event_type)
            .order_by(func.count(NotificationLog.id).desc())
        )

        event_data = {row.event_type.value: row.count for row in event_stats}

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_sent": total_sent,
            "channel_statistics": channel_data,
            "event_distribution": event_data
        }

    async def cleanup_old_notifications(
        self,
        days_to_keep: int = 90
    ) -> Dict[str, int]:
        """Clean up old notification data."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Clean up old completed queue items
        queue_result = await self.session.execute(
            delete(NotificationQueue)
            .where(
                and_(
                    NotificationQueue.status.in_([
                        NotificationStatus.SENT,
                        NotificationStatus.DELIVERED,
                        NotificationStatus.CANCELLED
                    ]),
                    NotificationQueue.updated_at < cutoff_date
                )
            )
        )

        # Clean up old logs
        log_result = await self.session.execute(
            delete(NotificationLog)
            .where(NotificationLog.sent_at < cutoff_date)
        )

        await self.session.commit()

        return {
            "queue_items_deleted": queue_result.rowcount,
            "log_entries_deleted": log_result.rowcount
        }
