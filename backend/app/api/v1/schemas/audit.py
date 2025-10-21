"""
OpenAPI schemas for audit event endpoints.

This module contains Pydantic models specifically designed for
OpenAPI documentation of audit event endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class AuditEventSchema(BaseModel):
    """Schema for audit event."""

    id: int = Field(..., description="Event ID", example=12345)
    event_type: str = Field(
        ...,
        description="Type of event",
        example="booking_created"
    )
    severity: str = Field(
        ...,
        description="Event severity level",
        example="info"
    )
    user_id: Optional[int] = Field(
        None,
        description="ID of user who triggered the event",
        example=123
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID associated with the event",
        example="sess_abc123def456"
    )
    ip_address: Optional[str] = Field(
        None,
        description="IP address of the request",
        example="192.168.1.100"
    )
    user_agent: Optional[str] = Field(
        None,
        description="User agent string",
        example="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    resource_type: Optional[str] = Field(
        None,
        description="Type of resource affected",
        example="booking"
    )
    resource_id: Optional[int] = Field(
        None,
        description="ID of the affected resource",
        example=456
    )
    details: Dict[str, Any] = Field(
        ...,
        description="Event details and metadata",
        example={
            "booking_id": 456,
            "professional_id": 789,
            "service_id": 101,
            "scheduled_at": "2025-01-28T10:00:00Z",
            "total_price": 150.00
        }
    )
    timestamp: datetime = Field(
        ...,
        description="When the event occurred",
        example="2025-01-27T14:30:00Z"
    )


class AuditEventFilterSchema(BaseModel):
    """Schema for audit event filtering parameters."""

    event_type: Optional[str] = Field(
        None,
        description="Filter by event type",
        example="booking_created"
    )
    severity: Optional[str] = Field(
        None,
        description="Filter by severity level",
        example="info"
    )
    user_id: Optional[int] = Field(
        None,
        description="Filter by user ID",
        example=123
    )
    resource_type: Optional[str] = Field(
        None,
        description="Filter by resource type",
        example="booking"
    )
    resource_id: Optional[int] = Field(
        None,
        description="Filter by resource ID",
        example=456
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Filter events after this date",
        example="2025-01-01T00:00:00Z"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Filter events before this date",
        example="2025-01-31T23:59:59Z"
    )
    ip_address: Optional[str] = Field(
        None,
        description="Filter by IP address",
        example="192.168.1.100"
    )


class AuditEventListResponseSchema(BaseModel):
    """Schema for audit event list response."""

    events: List[AuditEventSchema] = Field(..., description="List of audit events")
    total: int = Field(..., description="Total number of events matching filter")
    page: int = Field(..., description="Current page number", example=1)
    size: int = Field(..., description="Page size", example=50)
    has_next: bool = Field(..., description="Whether there are more pages")


class AuditEventStatsSchema(BaseModel):
    """Schema for audit event statistics."""

    total_events: int = Field(..., description="Total number of events", example=15420)
    events_by_type: Dict[str, int] = Field(
        ...,
        description="Event count by type",
        example={
            "booking_created": 5230,
            "booking_cancelled": 1240,
            "user_login": 8950
        }
    )
    events_by_severity: Dict[str, int] = Field(
        ...,
        description="Event count by severity",
        example={
            "info": 12300,
            "warning": 2100,
            "error": 950,
            "critical": 70
        }
    )
    events_by_user: Dict[str, int] = Field(
        ...,
        description="Top 10 users by event count",
        example={
            "user_123": 450,
            "user_456": 380,
            "user_789": 320
        }
    )
    events_by_hour: Dict[str, int] = Field(
        ...,
        description="Event count by hour (last 24 hours)",
        example={
            "00": 45,
            "01": 23,
            "02": 12,
            "09": 156,
            "10": 234
        }
    )
    date_range: Dict[str, datetime] = Field(
        ...,
        description="Date range of events",
        example={
            "earliest": "2025-01-01T00:00:00Z",
            "latest": "2025-01-27T14:30:00Z"
        }
    )


class AuditEventDetailSchema(BaseModel):
    """Schema for detailed audit event view."""

    event: AuditEventSchema = Field(..., description="The audit event")
    related_events: List[AuditEventSchema] = Field(
        ...,
        description="Related events (same resource, user, or session)"
    )
    context: Dict[str, Any] = Field(
        ...,
        description="Additional context information",
        example={
            "user_name": "John Doe",
            "user_role": "client",
            "resource_name": "Haircut Appointment",
            "salon_name": "Beauty Studio"
        }
    )


class AuditTrailSchema(BaseModel):
    """Schema for audit trail of a specific resource."""

    resource_type: str = Field(..., description="Type of resource")
    resource_id: int = Field(..., description="ID of the resource")
    events: List[AuditEventSchema] = Field(..., description="Chronological list of events")
    summary: Dict[str, Any] = Field(
        ...,
        description="Summary of changes",
        example={
            "created_at": "2025-01-27T10:00:00Z",
            "created_by": 123,
            "last_modified_at": "2025-01-27T14:30:00Z",
            "last_modified_by": 456,
            "total_changes": 3,
            "status_changes": ["confirmed", "cancelled"]
        }
    )


class AuditSearchRequestSchema(BaseModel):
    """Schema for audit event search request."""

    query: str = Field(
        ...,
        min_length=3,
        description="Search query (searches in event details)",
        example="booking cancellation fee"
    )
    filters: Optional[AuditEventFilterSchema] = Field(
        None,
        description="Additional filters to apply"
    )
    sort_by: Optional[str] = Field(
        "timestamp",
        description="Field to sort by",
        example="timestamp"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="Sort order (asc or desc)",
        example="desc"
    )


class AuditReportRequestSchema(BaseModel):
    """Schema for audit report generation request."""

    report_type: str = Field(
        ...,
        description="Type of report to generate",
        example="security_events"
    )
    date_range: Dict[str, datetime] = Field(
        ...,
        description="Date range for the report",
        example={
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-31T23:59:59Z"
        }
    )
    filters: Optional[AuditEventFilterSchema] = Field(
        None,
        description="Additional filters for the report"
    )
    format: Optional[str] = Field(
        "json",
        description="Report format (json, csv, pdf)",
        example="json"
    )


class AuditReportResponseSchema(BaseModel):
    """Schema for audit report response."""

    report_id: str = Field(..., description="Unique report ID")
    report_type: str = Field(..., description="Type of report")
    generated_at: datetime = Field(..., description="When the report was generated")
    date_range: Dict[str, datetime] = Field(..., description="Report date range")
    summary: Dict[str, Any] = Field(
        ...,
        description="Report summary statistics"
    )
    data: List[Dict[str, Any]] = Field(..., description="Report data")
    metadata: Dict[str, Any] = Field(
        ...,
        description="Report metadata",
        example={
            "total_records": 1500,
            "generation_time_ms": 245,
            "filters_applied": 3
        }
    )
