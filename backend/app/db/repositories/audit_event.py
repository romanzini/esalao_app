"""
Repository for audit event data access and management.

This module provides comprehensive data access methods for audit events,
including filtering, searching, and reporting capabilities.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.audit_event import AuditEvent, AuditEventType, AuditEventSeverity


class AuditEventRepository:
    """Repository for audit event operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
            metadata: Optional[Dict] = None,
        severity: AuditEventSeverity = AuditEventSeverity.LOW,
        correlation_id: Optional[str] = None,
        parent_event_id: Optional[int] = None,
        success: Optional[str] = None,
        error_message: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> AuditEvent:
        """
        Create a new audit event.

        Args:
            event_type: Type of the audit event
            action: Action that was performed
            user_id: ID of the user who performed the action
            session_id: Session ID
            ip_address: IP address of the client
            user_agent: User agent string
            request_id: Unique request identifier
            endpoint: API endpoint that was called
            http_method: HTTP method used
            resource_type: Type of resource affected
            resource_id: ID of the resource affected
            description: Human-readable description
            old_values: Previous values (for updates)
            new_values: New values (for updates/creates)
            metadata: Additional context data
            severity: Severity level of the event
            correlation_id: Correlation ID for tracking related events
            parent_event_id: ID of parent event (for nested operations)
            success: Success status (success/failure/partial)
            error_message: Error message if applicable
            user_role: Role of the user who performed the action

        Returns:
            Created AuditEvent instance
        """
        event = AuditEvent(
            event_type=event_type,
            action=action,
            user_id=user_id,
            session_id=session_id,
            user_role=user_role,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            endpoint=endpoint,
            http_method=http_method,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            event_metadata=metadata,
            severity=severity,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
            success=success,
            error_message=error_message,
            timestamp=datetime.utcnow(),
        )

        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)

        return event

    async def get_by_id(self, event_id: int) -> Optional[AuditEvent]:
        """Get audit event by ID."""
        stmt = select(AuditEvent).where(AuditEvent.id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_events(
        self,
        user_id: Optional[int] = None,
        event_types: Optional[List[AuditEventType]] = None,
        severities: Optional[List[AuditEventSeverity]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        success_status: Optional[str] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "timestamp",
        order_desc: bool = True,
    ) -> Tuple[List[AuditEvent], int]:
        """
        List audit events with filtering and pagination.

        Args:
            user_id: Filter by user ID
            event_types: Filter by event types
            severities: Filter by severity levels
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            ip_address: Filter by IP address
            start_date: Filter events after this date
            end_date: Filter events before this date
            correlation_id: Filter by correlation ID
            success_status: Filter by success status
            search_term: Search in description and action fields
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order by
            order_desc: Whether to order in descending order

        Returns:
            Tuple of (events list, total count)
        """
        # Build base query
        stmt = select(AuditEvent)
        count_stmt = select(func.count(AuditEvent.id))

        # Apply filters
        conditions = []

        if user_id is not None:
            conditions.append(AuditEvent.user_id == user_id)

        if event_types:
            conditions.append(AuditEvent.event_type.in_(event_types))

        if severities:
            conditions.append(AuditEvent.severity.in_(severities))

        if resource_type:
            conditions.append(AuditEvent.resource_type == resource_type)

        if resource_id:
            conditions.append(AuditEvent.resource_id == resource_id)

        if ip_address:
            conditions.append(AuditEvent.ip_address == ip_address)

        if start_date:
            conditions.append(AuditEvent.timestamp >= start_date)

        if end_date:
            conditions.append(AuditEvent.timestamp <= end_date)

        if correlation_id:
            conditions.append(AuditEvent.correlation_id == correlation_id)

        if success_status:
            conditions.append(AuditEvent.success == success_status)

        if search_term:
            search_conditions = [
                AuditEvent.description.ilike(f"%{search_term}%"),
                AuditEvent.action.ilike(f"%{search_term}%"),
                AuditEvent.event_type.ilike(f"%{search_term}%"),
            ]
            conditions.append(or_(*search_conditions))

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        # Get total count
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar()

        # Apply ordering
        if order_by == "timestamp":
            order_field = AuditEvent.timestamp
        elif order_by == "severity":
            order_field = AuditEvent.severity
        elif order_by == "event_type":
            order_field = AuditEvent.event_type
        elif order_by == "user_id":
            order_field = AuditEvent.user_id
        else:
            order_field = AuditEvent.timestamp

        if order_desc:
            stmt = stmt.order_by(desc(order_field))
        else:
            stmt = stmt.order_by(order_field)

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        events = result.scalars().all()

        return list(events), total_count

    async def get_user_activity(
        self,
        user_id: int,
        hours_back: int = 24,
        limit: int = 50,
    ) -> List[AuditEvent]:
        """
        Get recent activity for a specific user.

        Args:
            user_id: User ID to get activity for
            hours_back: How many hours back to look
            limit: Maximum number of events to return

        Returns:
            List of recent audit events for the user
        """
        since = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = (
            select(AuditEvent)
            .where(
                and_(
                    AuditEvent.user_id == user_id,
                    AuditEvent.timestamp >= since
                )
            )
            .order_by(desc(AuditEvent.timestamp))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_security_events(
        self,
        hours_back: int = 24,
        limit: int = 100,
        min_severity: AuditEventSeverity = AuditEventSeverity.MEDIUM,
    ) -> List[AuditEvent]:
        """
        Get recent security-related events.

        Args:
            hours_back: How many hours back to look
            limit: Maximum number of events to return
            min_severity: Minimum severity level to include

        Returns:
            List of security events
        """
        since = datetime.utcnow() - timedelta(hours=hours_back)

        security_types = [
            AuditEventType.LOGIN_FAILED,
            AuditEventType.ACCOUNT_LOCKED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.UNAUTHORIZED_ACCESS,
            AuditEventType.DATA_BREACH_DETECTED,
        ]

        # Map severity to numeric values for comparison
        severity_values = {
            AuditEventSeverity.LOW: 1,
            AuditEventSeverity.MEDIUM: 2,
            AuditEventSeverity.HIGH: 3,
            AuditEventSeverity.CRITICAL: 4,
        }

        min_severity_value = severity_values[min_severity]
        qualifying_severities = [
            sev for sev, val in severity_values.items() 
            if val >= min_severity_value
        ]

        stmt = (
            select(AuditEvent)
            .where(
                and_(
                    or_(
                        AuditEvent.event_type.in_(security_types),
                        AuditEvent.severity.in_(qualifying_severities)
                    ),
                    AuditEvent.timestamp >= since
                )
            )
            .order_by(desc(AuditEvent.timestamp))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_correlation(
        self,
        correlation_id: str,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        Get all events with the same correlation ID.

        Args:
            correlation_id: Correlation ID to search for
            limit: Maximum number of events to return

        Returns:
            List of related audit events
        """
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.correlation_id == correlation_id)
            .order_by(AuditEvent.timestamp)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
    ) -> List[AuditEvent]:
        """
        Get audit history for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            limit: Maximum number of events to return

        Returns:
            List of audit events for the resource
        """
        stmt = (
            select(AuditEvent)
            .where(
                and_(
                    AuditEvent.resource_type == resource_type,
                    AuditEvent.resource_id == resource_id
                )
            )
            .order_by(desc(AuditEvent.timestamp))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get audit event statistics.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary with audit statistics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build base condition
        base_condition = and_(
            AuditEvent.timestamp >= start_date,
            AuditEvent.timestamp <= end_date
        )

        # Total events
        total_stmt = select(func.count(AuditEvent.id)).where(base_condition)
        total_result = await self.session.execute(total_stmt)
        total_events = total_result.scalar()

        # Events by type
        type_stmt = (
            select(AuditEvent.event_type, func.count(AuditEvent.id))
            .where(base_condition)
            .group_by(AuditEvent.event_type)
            .order_by(desc(func.count(AuditEvent.id)))
        )
        type_result = await self.session.execute(type_stmt)
        events_by_type = dict(type_result.fetchall())

        # Events by severity
        severity_stmt = (
            select(AuditEvent.severity, func.count(AuditEvent.id))
            .where(base_condition)
            .group_by(AuditEvent.severity)
            .order_by(desc(func.count(AuditEvent.id)))
        )
        severity_result = await self.session.execute(severity_stmt)
        events_by_severity = dict(severity_result.fetchall())

        # Top users by activity
        user_stmt = (
            select(AuditEvent.user_id, func.count(AuditEvent.id))
            .where(and_(base_condition, AuditEvent.user_id.is_not(None)))
            .group_by(AuditEvent.user_id)
            .order_by(desc(func.count(AuditEvent.id)))
            .limit(10)
        )
        user_result = await self.session.execute(user_stmt)
        top_users = dict(user_result.fetchall())

        # Failed events
        failed_stmt = select(func.count(AuditEvent.id)).where(
            and_(base_condition, AuditEvent.success == "failure")
        )
        failed_result = await self.session.execute(failed_stmt)
        failed_events = failed_result.scalar()

        return {
            "total_events": total_events,
            "failed_events": failed_events,
            "success_rate": (total_events - failed_events) / total_events if total_events > 0 else 0,
            "events_by_type": events_by_type,
            "events_by_severity": events_by_severity,
            "top_users_by_activity": top_users,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

    async def cleanup_old_events(
        self,
        days_to_keep: int = 365,
        batch_size: int = 1000,
    ) -> int:
        """
        Clean up old audit events.

        Args:
            days_to_keep: Number of days of events to keep
            batch_size: Number of events to delete per batch

        Returns:
            Number of events deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count events to be deleted
        count_stmt = select(func.count(AuditEvent.id)).where(
            AuditEvent.timestamp < cutoff_date
        )
        count_result = await self.session.execute(count_stmt)
        total_to_delete = count_result.scalar()

        if total_to_delete == 0:
            return 0

        # Delete in batches to avoid long-running transactions
        deleted_count = 0
        while deleted_count < total_to_delete:
            # Get batch of IDs to delete
            id_stmt = (
                select(AuditEvent.id)
                .where(AuditEvent.timestamp < cutoff_date)
                .limit(batch_size)
            )
            id_result = await self.session.execute(id_stmt)
            ids_to_delete = [row[0] for row in id_result.fetchall()]

            if not ids_to_delete:
                break

            # Delete the batch
            from sqlalchemy import delete as sql_delete
            delete_stmt = sql_delete(AuditEvent).where(AuditEvent.id.in_(ids_to_delete))
            await self.session.execute(delete_stmt)

            await self.session.commit()
            deleted_count += len(ids_to_delete)

        return deleted_count