"""
OpenAPI schemas for no-show detection endpoints.

This module contains Pydantic models specifically designed for
OpenAPI documentation of no-show detection endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class NoShowJobConfigSchema(BaseModel):
    """Schema for no-show job configuration."""

    grace_period_minutes: int = Field(
        ...,
        ge=0,
        le=1440,
        description="Grace period in minutes after appointment time",
        example=30
    )
    batch_size: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Number of bookings to process in each batch",
        example=100
    )
    enabled: bool = Field(
        ...,
        description="Whether no-show detection is enabled",
        example=True
    )
    schedule_cron: str = Field(
        ...,
        description="Cron expression for automatic job scheduling",
        example="0 */15 * * *"
    )
    notification_enabled: bool = Field(
        ...,
        description="Whether to send notifications on no-show detection",
        example=True
    )
    auto_mark_enabled: bool = Field(
        ...,
        description="Whether to automatically mark bookings as no-show",
        example=True
    )


class NoShowJobExecutionSchema(BaseModel):
    """Schema for no-show job execution request."""

    force_run: bool = Field(
        False,
        description="Force run even if recently executed",
        example=False
    )
    batch_size: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Override default batch size for this run",
        example=50
    )
    salon_id: Optional[int] = Field(
        None,
        description="Run only for specific salon (admin only)",
        example=1
    )
    dry_run: bool = Field(
        False,
        description="Perform dry run without making changes",
        example=False
    )


class NoShowJobResultSchema(BaseModel):
    """Schema for no-show job execution result."""

    job_id: str = Field(..., description="Unique job execution ID", example="job_20250127_143000")
    started_at: datetime = Field(..., description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    status: str = Field(
        ...,
        description="Job execution status",
        example="completed"
    )
    processed_bookings: int = Field(..., description="Number of bookings processed", example=145)
    no_shows_detected: int = Field(..., description="Number of no-shows detected", example=12)
    notifications_sent: int = Field(..., description="Number of notifications sent", example=12)
    errors_encountered: int = Field(..., description="Number of errors encountered", example=0)
    execution_time_ms: int = Field(..., description="Execution time in milliseconds", example=2450)
    summary: Dict[str, Any] = Field(
        ...,
        description="Execution summary",
        example={
            "salons_processed": 5,
            "bookings_by_salon": {"salon_1": 45, "salon_2": 67},
            "no_shows_by_salon": {"salon_1": 3, "salon_2": 9}
        }
    )


class NoShowJobHistorySchema(BaseModel):
    """Schema for no-show job execution history."""

    jobs: List[NoShowJobResultSchema] = Field(..., description="List of job executions")
    total: int = Field(..., description="Total number of job executions", example=156)
    page: int = Field(..., description="Current page number", example=1)
    size: int = Field(..., description="Page size", example=20)
    has_next: bool = Field(..., description="Whether there are more pages", example=True)


class NoShowDetectionCriteriaSchema(BaseModel):
    """Schema for no-show detection criteria."""

    appointment_passed_minutes: int = Field(
        ...,
        description="Minutes since appointment time",
        example=45
    )
    grace_period_minutes: int = Field(
        ...,
        description="Grace period applied",
        example=30
    )
    booking_status: str = Field(
        ...,
        description="Current booking status",
        example="confirmed"
    )
    professional_notified: bool = Field(
        ...,
        description="Whether professional was notified",
        example=True
    )
    client_notified: bool = Field(
        ...,
        description="Whether client was notified",
        example=False
    )


class NoShowDetectionResultSchema(BaseModel):
    """Schema for individual no-show detection result."""

    booking_id: int = Field(..., description="Booking ID", example=12345)
    client_id: int = Field(..., description="Client ID", example=678)
    professional_id: int = Field(..., description="Professional ID", example=234)
    salon_id: int = Field(..., description="Salon ID", example=1)
    service_name: str = Field(..., description="Service name", example="Haircut")
    scheduled_at: datetime = Field(..., description="Original appointment time")
    detected_at: datetime = Field(..., description="When no-show was detected")
    criteria: NoShowDetectionCriteriaSchema = Field(..., description="Detection criteria used")
    action_taken: str = Field(
        ...,
        description="Action taken",
        example="marked_no_show_and_notified"
    )
    previous_status: str = Field(..., description="Previous booking status", example="confirmed")
    new_status: str = Field(..., description="New booking status", example="no_show")


class NoShowStatisticsSchema(BaseModel):
    """Schema for no-show statistics."""

    total_no_shows: int = Field(..., description="Total no-shows detected", example=234)
    no_show_rate: float = Field(..., description="Overall no-show rate percentage", example=8.5)
    by_salon: Dict[str, Dict[str, Union[int, float]]] = Field(
        ...,
        description="No-show statistics by salon",
        example={
            "salon_1": {"count": 45, "rate": 7.2},
            "salon_2": {"count": 67, "rate": 9.8}
        }
    )
    by_professional: Dict[str, Dict[str, Union[int, float]]] = Field(
        ...,
        description="No-show statistics by professional",
        example={
            "prof_123": {"count": 12, "rate": 6.5},
            "prof_456": {"count": 18, "rate": 11.2}
        }
    )
    by_service_category: Dict[str, Dict[str, Union[int, float]]] = Field(
        ...,
        description="No-show statistics by service category",
        example={
            "haircut": {"count": 89, "rate": 7.8},
            "coloring": {"count": 45, "rate": 9.2}
        }
    )
    by_time_of_day: Dict[str, Dict[str, Union[int, float]]] = Field(
        ...,
        description="No-show statistics by time of day",
        example={
            "morning": {"count": 67, "rate": 6.5},
            "afternoon": {"count": 89, "rate": 8.9},
            "evening": {"count": 78, "rate": 9.8}
        }
    )
    trends: Dict[str, List[Dict[str, Any]]] = Field(
        ...,
        description="No-show trends over time",
        example={
            "daily": [
                {"date": "2025-01-20", "count": 8, "rate": 7.5},
                {"date": "2025-01-21", "count": 12, "rate": 9.1}
            ]
        }
    )


class NoShowPreventionInsightSchema(BaseModel):
    """Schema for no-show prevention insights."""

    risk_factors: List[Dict[str, Any]] = Field(
        ...,
        description="Identified risk factors",
        example=[
            {
                "factor": "booking_lead_time",
                "description": "Bookings made more than 2 weeks in advance",
                "risk_level": "high",
                "correlation": 0.78
            }
        ]
    )
    recommendations: List[Dict[str, str]] = Field(
        ...,
        description="Prevention recommendations",
        example=[
            {
                "type": "reminder_policy",
                "description": "Send reminder 24 hours before appointment",
                "expected_impact": "15% reduction in no-shows"
            }
        ]
    )
    patterns: Dict[str, Any] = Field(
        ...,
        description="Detected patterns",
        example={
            "repeat_no_show_clients": 23,
            "high_risk_time_slots": ["friday_evening", "monday_morning"],
            "seasonal_trends": "higher_in_january"
        }
    )


class NoShowNotificationSchema(BaseModel):
    """Schema for no-show notification details."""

    notification_id: str = Field(..., description="Notification ID")
    booking_id: int = Field(..., description="Related booking ID")
    recipient_type: str = Field(..., description="Recipient type", example="professional")
    recipient_id: int = Field(..., description="Recipient ID")
    message_type: str = Field(..., description="Message type", example="no_show_detected")
    sent_at: datetime = Field(..., description="When notification was sent")
    delivery_status: str = Field(..., description="Delivery status", example="delivered")
    template_used: str = Field(..., description="Template used", example="no_show_alert")
    content_preview: str = Field(
        ...,
        description="Preview of notification content",
        example="Client John Doe did not show up for 2:00 PM appointment..."
    )


class NoShowBulkActionSchema(BaseModel):
    """Schema for bulk no-show actions."""

    action: str = Field(
        ...,
        description="Bulk action to perform",
        example="mark_no_show"
    )
    booking_ids: List[int] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of booking IDs to process",
        example=[12345, 12346, 12347]
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for bulk action",
        example="Manual review identified missed appointments"
    )
    send_notifications: bool = Field(
        True,
        description="Whether to send notifications",
        example=True
    )


class NoShowBulkActionResultSchema(BaseModel):
    """Schema for bulk no-show action results."""

    total_requested: int = Field(..., description="Total bookings requested for processing")
    successfully_processed: int = Field(..., description="Successfully processed bookings")
    failed_processing: int = Field(..., description="Failed processing count")
    results: List[Dict[str, Any]] = Field(
        ...,
        description="Detailed results for each booking",
        example=[
            {
                "booking_id": 12345,
                "status": "success",
                "previous_status": "confirmed",
                "new_status": "no_show"
            }
        ]
    )
    notifications_sent: int = Field(..., description="Number of notifications sent")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
