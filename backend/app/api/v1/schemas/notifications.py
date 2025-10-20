"""
API schemas for notification management.

This module contains Pydantic models for notification API requests and responses,
including preference management, template configuration, and delivery tracking.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

from backend.app.db.models.notifications import (
    NotificationChannel, NotificationEventType, NotificationPriority, NotificationStatus
)


class NotificationChannelEnum(str, Enum):
    """Notification channel enum for API."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WHATSAPP = "whatsapp"


class NotificationEventTypeEnum(str, Enum):
    """Notification event type enum for API."""
    # Booking Events
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_REMINDER = "booking_reminder"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_RESCHEDULED = "booking_rescheduled"
    BOOKING_COMPLETED = "booking_completed"

    # Payment Events
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    REFUND_PROCESSED = "refund_processed"

    # Loyalty Events
    POINTS_EARNED = "points_earned"
    TIER_UPGRADED = "tier_upgraded"
    REWARD_AVAILABLE = "reward_available"
    POINTS_EXPIRING = "points_expiring"

    # Waitlist Events
    WAITLIST_ADDED = "waitlist_added"
    SLOT_AVAILABLE = "slot_available"
    WAITLIST_EXPIRED = "waitlist_expired"

    # No-show Events
    NO_SHOW_DETECTED = "no_show_detected"
    NO_SHOW_FEE_CHARGED = "no_show_fee_charged"

    # Professional Events
    NEW_BOOKING = "new_booking"
    CANCELLATION_NOTICE = "cancellation_notice"
    CLIENT_NO_SHOW = "client_no_show"

    # Marketing Events
    PROMOTIONAL_OFFER = "promotional_offer"
    BIRTHDAY_GREETING = "birthday_greeting"
    ANNIVERSARY_OFFER = "anniversary_offer"

    # System Events
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    ACCOUNT_LOCKED = "account_locked"


class NotificationPriorityEnum(str, Enum):
    """Notification priority enum for API."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationStatusEnum(str, Enum):
    """Notification status enum for API."""
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


# ==================== Request Schemas ====================

class PreferenceUpdateRequest(BaseModel):
    """Request to update notification preference."""

    event_type: NotificationEventTypeEnum = Field(
        ...,
        description="Type of notification event"
    )
    channel: NotificationChannelEnum = Field(
        ...,
        description="Notification channel"
    )
    enabled: bool = Field(
        ...,
        description="Whether notifications are enabled for this combination"
    )
    advance_minutes: Optional[int] = Field(
        None,
        ge=0,
        le=1440,
        description="Minutes in advance for reminder notifications (0-1440)"
    )
    quiet_hours_start: Optional[str] = Field(
        None,
        regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
        description="Start time for quiet hours (HH:MM format)"
    )
    quiet_hours_end: Optional[str] = Field(
        None,
        regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
        description="End time for quiet hours (HH:MM format)"
    )

    class Config:
        schema_extra = {
            "example": {
                "event_type": "booking_reminder",
                "channel": "sms",
                "enabled": True,
                "advance_minutes": 30,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00"
            }
        }


class BulkPreferenceUpdateRequest(BaseModel):
    """Request to update multiple notification preferences."""

    preferences: List[PreferenceUpdateRequest] = Field(
        ...,
        description="List of preference updates"
    )

    class Config:
        schema_extra = {
            "example": {
                "preferences": [
                    {
                        "event_type": "booking_reminder",
                        "channel": "email",
                        "enabled": True,
                        "advance_minutes": 60
                    },
                    {
                        "event_type": "booking_reminder",
                        "channel": "sms",
                        "enabled": True,
                        "advance_minutes": 15
                    }
                ]
            }
        }


class NotificationTemplateRequest(BaseModel):
    """Request to create or update notification template."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique template name/identifier"
    )
    event_type: NotificationEventTypeEnum = Field(
        ...,
        description="Event type this template handles"
    )
    channel: NotificationChannelEnum = Field(
        ...,
        description="Channel this template is for"
    )
    subject: Optional[str] = Field(
        None,
        max_length=200,
        description="Subject line template for email/SMS title"
    )
    body_template: str = Field(
        ...,
        min_length=1,
        description="Template body with variable placeholders"
    )
    variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Available template variables and descriptions"
    )
    priority: NotificationPriorityEnum = Field(
        NotificationPriorityEnum.NORMAL,
        description="Default priority for this template"
    )
    locale: str = Field(
        "pt_BR",
        regex=r'^[a-z]{2}_[A-Z]{2}$',
        description="Language/locale for this template"
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "booking_confirmation_email",
                "event_type": "booking_confirmed",
                "channel": "email",
                "subject": "Agendamento Confirmado - {{salon_name}}",
                "body_template": "Olá {{user_name}},\n\nSeu agendamento foi confirmado!\n\nDetalhes:\n- Serviço: {{service_name}}\n- Data: {{appointment_date}}\n- Horário: {{appointment_time}}\n- Profissional: {{professional_name}}\n\nAguardamos você!\n\nEquipe {{salon_name}}",
                "variables": {
                    "user_name": "Nome do usuário",
                    "salon_name": "Nome do salão",
                    "service_name": "Nome do serviço",
                    "appointment_date": "Data do agendamento",
                    "appointment_time": "Horário do agendamento",
                    "professional_name": "Nome do profissional"
                },
                "priority": "high",
                "locale": "pt_BR"
            }
        }


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    user_id: int = Field(
        ...,
        gt=0,
        description="ID of the user to send notification to"
    )
    event_type: NotificationEventTypeEnum = Field(
        ...,
        description="Type of notification event"
    )
    context_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context data for template rendering"
    )
    priority: NotificationPriorityEnum = Field(
        NotificationPriorityEnum.NORMAL,
        description="Notification priority"
    )
    channels: Optional[List[NotificationChannelEnum]] = Field(
        None,
        description="Specific channels to use (uses user preferences if not specified)"
    )
    scheduled_at: Optional[datetime] = Field(
        None,
        description="When to send the notification (immediate if not specified)"
    )
    correlation_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Correlation ID for tracking related notifications"
    )

    class Config:
        schema_extra = {
            "example": {
                "user_id": 123,
                "event_type": "booking_confirmed",
                "context_data": {
                    "booking_id": "456",
                    "service_name": "Corte de Cabelo",
                    "appointment_date": "2023-12-25",
                    "appointment_time": "14:30",
                    "professional_name": "Maria Silva"
                },
                "priority": "high",
                "channels": ["email", "sms"],
                "correlation_id": "booking_456"
            }
        }


# ==================== Response Schemas ====================

class PreferenceResponse(BaseModel):
    """Notification preference response."""

    id: int = Field(..., description="Preference ID")
    event_type: NotificationEventTypeEnum = Field(..., description="Event type")
    channel: NotificationChannelEnum = Field(..., description="Notification channel")
    enabled: bool = Field(..., description="Whether notifications are enabled")
    advance_minutes: Optional[int] = Field(None, description="Minutes in advance for reminders")
    quiet_hours_start: Optional[str] = Field(None, description="Quiet hours start time")
    quiet_hours_end: Optional[str] = Field(None, description="Quiet hours end time")
    created_at: datetime = Field(..., description="When preference was created")
    updated_at: datetime = Field(..., description="When preference was last updated")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 123,
                "event_type": "booking_reminder",
                "channel": "email",
                "enabled": True,
                "advance_minutes": 60,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
                "created_at": "2023-12-01T10:00:00Z",
                "updated_at": "2023-12-01T10:00:00Z"
            }
        }


class NotificationTemplateResponse(BaseModel):
    """Notification template response."""

    id: int = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    event_type: NotificationEventTypeEnum = Field(..., description="Event type")
    channel: NotificationChannelEnum = Field(..., description="Channel")
    subject: Optional[str] = Field(None, description="Subject template")
    body_template: str = Field(..., description="Body template")
    variables: Dict[str, Any] = Field(..., description="Available variables")
    priority: NotificationPriorityEnum = Field(..., description="Default priority")
    is_active: bool = Field(..., description="Whether template is active")
    locale: str = Field(..., description="Template locale")
    created_at: datetime = Field(..., description="When template was created")
    updated_at: datetime = Field(..., description="When template was last updated")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 456,
                "name": "booking_confirmation_email",
                "event_type": "booking_confirmed",
                "channel": "email",
                "subject": "Agendamento Confirmado - {{salon_name}}",
                "body_template": "Olá {{user_name}}, seu agendamento foi confirmado!",
                "variables": {
                    "user_name": "Nome do usuário",
                    "salon_name": "Nome do salão"
                },
                "priority": "high",
                "is_active": True,
                "locale": "pt_BR",
                "created_at": "2023-12-01T10:00:00Z",
                "updated_at": "2023-12-01T10:00:00Z"
            }
        }


class NotificationQueueResponse(BaseModel):
    """Notification queue item response."""

    id: int = Field(..., description="Queue item ID")
    user_id: int = Field(..., description="User ID")
    channel: NotificationChannelEnum = Field(..., description="Notification channel")
    priority: NotificationPriorityEnum = Field(..., description="Priority")
    status: NotificationStatusEnum = Field(..., description="Current status")
    subject: Optional[str] = Field(None, description="Rendered subject")
    scheduled_at: datetime = Field(..., description="When notification should be sent")
    sent_at: Optional[datetime] = Field(None, description="When notification was sent")
    retry_count: int = Field(..., description="Number of retry attempts")
    max_retries: int = Field(..., description="Maximum retry attempts")
    last_error: Optional[str] = Field(None, description="Last error message")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    external_id: Optional[str] = Field(None, description="External service ID")
    created_at: datetime = Field(..., description="When notification was queued")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 789,
                "user_id": 123,
                "channel": "email",
                "priority": "high",
                "status": "sent",
                "subject": "Agendamento Confirmado - eSalão",
                "scheduled_at": "2023-12-01T14:00:00Z",
                "sent_at": "2023-12-01T14:00:05Z",
                "retry_count": 0,
                "max_retries": 3,
                "last_error": None,
                "correlation_id": "booking_456",
                "external_id": "email_1701435605.123",
                "created_at": "2023-12-01T14:00:00Z"
            }
        }


class NotificationLogResponse(BaseModel):
    """Notification log entry response."""

    id: int = Field(..., description="Log entry ID")
    user_id: int = Field(..., description="User ID")
    channel: NotificationChannelEnum = Field(..., description="Channel used")
    event_type: NotificationEventTypeEnum = Field(..., description="Event type")
    status: NotificationStatusEnum = Field(..., description="Delivery status")
    subject: Optional[str] = Field(None, description="Subject that was sent")
    sent_at: datetime = Field(..., description="When delivery was attempted")
    delivered_at: Optional[datetime] = Field(None, description="When delivery was confirmed")
    external_id: Optional[str] = Field(None, description="External service ID")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code from provider")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 101112,
                "user_id": 123,
                "channel": "email",
                "event_type": "booking_confirmed",
                "status": "delivered",
                "subject": "Agendamento Confirmado - eSalão",
                "sent_at": "2023-12-01T14:00:05Z",
                "delivered_at": "2023-12-01T14:00:07Z",
                "external_id": "email_1701435605.123",
                "error_message": None,
                "error_code": None,
                "correlation_id": "booking_456"
            }
        }


class SendNotificationResponse(BaseModel):
    """Response to send notification request."""

    message: str = Field(..., description="Response message")
    notifications_queued: int = Field(..., description="Number of notifications queued")
    channels: List[NotificationChannelEnum] = Field(..., description="Channels used")

    class Config:
        schema_extra = {
            "example": {
                "message": "Notifications queued successfully",
                "notifications_queued": 2,
                "channels": ["email", "sms"]
            }
        }


class NotificationStatisticsResponse(BaseModel):
    """Notification delivery statistics response."""

    period: Dict[str, str] = Field(..., description="Statistics period")
    total_sent: int = Field(..., description="Total notifications sent")
    channel_statistics: Dict[str, Dict[str, Union[int, float]]] = Field(
        ..., description="Statistics by channel"
    )
    event_distribution: Dict[str, int] = Field(..., description="Event type distribution")

    class Config:
        schema_extra = {
            "example": {
                "period": {
                    "start_date": "2023-11-01T00:00:00Z",
                    "end_date": "2023-12-01T00:00:00Z"
                },
                "total_sent": 1250,
                "channel_statistics": {
                    "email": {
                        "total": 800,
                        "successful": 792,
                        "success_rate": 99.0
                    },
                    "sms": {
                        "total": 300,
                        "successful": 295,
                        "success_rate": 98.33
                    },
                    "push": {
                        "total": 150,
                        "successful": 140,
                        "success_rate": 93.33
                    }
                },
                "event_distribution": {
                    "booking_confirmed": 400,
                    "booking_reminder": 350,
                    "payment_received": 250,
                    "points_earned": 150,
                    "tier_upgraded": 50,
                    "slot_available": 50
                }
            }
        }


# ==================== List Response Schemas ====================

class PreferenceListResponse(BaseModel):
    """List of notification preferences response."""

    preferences: List[PreferenceResponse] = Field(..., description="User preferences")
    total: int = Field(..., description="Total number of preferences")

    class Config:
        schema_extra = {
            "example": {
                "preferences": [
                    {
                        "id": 123,
                        "event_type": "booking_reminder",
                        "channel": "email",
                        "enabled": True,
                        "advance_minutes": 60,
                        "quiet_hours_start": None,
                        "quiet_hours_end": None,
                        "created_at": "2023-12-01T10:00:00Z",
                        "updated_at": "2023-12-01T10:00:00Z"
                    }
                ],
                "total": 1
            }
        }


class TemplateListResponse(BaseModel):
    """List of notification templates response."""

    templates: List[NotificationTemplateResponse] = Field(..., description="Notification templates")
    total: int = Field(..., description="Total number of templates")

    class Config:
        schema_extra = {
            "example": {
                "templates": [
                    {
                        "id": 456,
                        "name": "booking_confirmation_email",
                        "event_type": "booking_confirmed",
                        "channel": "email",
                        "subject": "Agendamento Confirmado",
                        "body_template": "Olá {{user_name}}, seu agendamento foi confirmado!",
                        "variables": {"user_name": "Nome do usuário"},
                        "priority": "high",
                        "is_active": True,
                        "locale": "pt_BR",
                        "created_at": "2023-12-01T10:00:00Z",
                        "updated_at": "2023-12-01T10:00:00Z"
                    }
                ],
                "total": 1
            }
        }


class NotificationHistoryResponse(BaseModel):
    """Notification history response."""

    notifications: List[NotificationLogResponse] = Field(..., description="Notification history")
    total: int = Field(..., description="Total number of notifications")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")

    class Config:
        schema_extra = {
            "example": {
                "notifications": [
                    {
                        "id": 101112,
                        "user_id": 123,
                        "channel": "email",
                        "event_type": "booking_confirmed",
                        "status": "delivered",
                        "subject": "Agendamento Confirmado",
                        "sent_at": "2023-12-01T14:00:05Z",
                        "delivered_at": "2023-12-01T14:00:07Z",
                        "external_id": "email_123",
                        "error_message": None,
                        "error_code": None,
                        "correlation_id": "booking_456"
                    }
                ],
                "total": 1,
                "page": 1,
                "limit": 50
            }
        }
