"""No-show policy domain models and business rules."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NoShowStatus(str, Enum):
    """No-show status for bookings."""

    NOT_APPLICABLE = "not_applicable"
    PENDING_DETECTION = "pending_detection"
    MARKED_NO_SHOW = "marked_no_show"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class NoShowReason(str, Enum):
    """Reasons for marking booking as no-show."""

    CLIENT_NO_SHOW = "client_no_show"
    CLIENT_LATE_EXCESSIVE = "client_late_excessive"
    CLIENT_UNPREPARED = "client_unprepared"
    PROFESSIONAL_NO_SHOW = "professional_no_show"
    PROFESSIONAL_LATE = "professional_late"
    SYSTEM_ERROR = "system_error"
    DISPUTED_RESOLVED = "disputed_resolved"


class NoShowFeeRule(BaseModel):
    """No-show fee calculation rule."""

    base_percentage: float = Field(
        ge=0.0, le=100.0,
        description="Base percentage of service value (0-100%)"
    )
    fixed_amount: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Fixed fee amount in BRL"
    )
    minimum_fee: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Minimum fee amount in BRL"
    )
    maximum_fee: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum fee amount in BRL"
    )
    grace_period_minutes: int = Field(
        default=15,
        ge=0,
        description="Grace period before marking as no-show"
    )


class NoShowPolicy(BaseModel):
    """No-show policy configuration."""

    id: int
    name: str
    description: str
    is_active: bool = True

    # Detection rules
    auto_detect_enabled: bool = True
    detection_delay_minutes: int = Field(
        default=15,
        ge=0,
        description="Minutes after scheduled time to auto-detect no-show"
    )

    # Fee rules
    client_no_show_rule: NoShowFeeRule
    professional_no_show_rule: Optional[NoShowFeeRule] = None

    # Dispute handling
    dispute_window_hours: int = Field(
        default=24,
        ge=0,
        description="Hours clients have to dispute no-show"
    )

    # Metadata
    created_at: datetime
    updated_at: datetime


class NoShowContext(BaseModel):
    """Context for no-show evaluation."""

    booking_id: int
    client_id: int
    professional_id: int
    service_id: int
    unit_id: int

    scheduled_at: datetime
    service_duration_minutes: int
    service_price: float

    # Status tracking
    current_time: datetime
    booking_status: str

    # Detection context
    client_arrived: bool = False
    professional_arrived: bool = True  # Assume professional is available

    # Grace period and timing
    grace_period_minutes: int = 15
    late_threshold_minutes: int = 30

    # History
    previous_no_shows: int = 0
    client_reputation_score: float = 100.0


class NoShowEvaluation(BaseModel):
    """Result of no-show policy evaluation."""

    should_mark_no_show: bool
    reason: Optional[NoShowReason] = None
    fee_amount: float = 0.0
    fee_calculation: Dict[str, Any] = Field(default_factory=dict)

    # Detection details
    detection_time: datetime
    grace_period_expired: bool = False
    minutes_late: int = 0

    # Policy applied
    policy_id: int
    auto_detected: bool = True

    # Additional context
    can_dispute: bool = True
    dispute_deadline: Optional[datetime] = None
    recommended_action: str = ""


class NoShowRecord(BaseModel):
    """No-show record for tracking."""

    id: int
    booking_id: int

    # Status and timing
    status: NoShowStatus
    marked_at: datetime
    marked_by_id: int

    # Reason and fee
    reason: NoShowReason
    fee_amount: float
    fee_paid: bool = False

    # Dispute tracking
    disputed_at: Optional[datetime] = None
    disputed_by_id: Optional[int] = None
    dispute_reason: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None

    # Policy reference
    policy_id: int
    evaluation_data: Dict[str, Any] = Field(default_factory=dict)


class NoShowStatistics(BaseModel):
    """No-show statistics for reporting."""

    period_start: datetime
    period_end: datetime

    # Counts
    total_bookings: int
    total_no_shows: int
    client_no_shows: int
    professional_no_shows: int

    # Rates
    no_show_rate: float = 0.0
    client_no_show_rate: float = 0.0
    professional_no_show_rate: float = 0.0

    # Financial impact
    total_fees_charged: float = 0.0
    total_fees_collected: float = 0.0
    revenue_lost: float = 0.0

    # Dispute data
    total_disputes: int = 0
    disputes_resolved: int = 0
    disputes_upheld: int = 0

    # Top reasons
    top_reasons: List[Dict[str, Any]] = Field(default_factory=list)


def calculate_no_show_fee(
    context: NoShowContext,
    rule: NoShowFeeRule
) -> Dict[str, Any]:
    """Calculate no-show fee based on rule and context."""

    calculation = {
        "base_price": context.service_price,
        "rule": rule.dict(),
        "steps": []
    }

    # Start with percentage-based fee
    if rule.base_percentage > 0:
        percentage_fee = context.service_price * (rule.base_percentage / 100)
        calculation["steps"].append({
            "type": "percentage",
            "percentage": rule.base_percentage,
            "amount": percentage_fee
        })
        fee_amount = percentage_fee
    else:
        fee_amount = 0.0

    # Apply fixed amount if specified
    if rule.fixed_amount is not None:
        calculation["steps"].append({
            "type": "fixed",
            "amount": rule.fixed_amount
        })
        fee_amount = rule.fixed_amount

    # Apply minimum fee
    if rule.minimum_fee is not None and fee_amount < rule.minimum_fee:
        calculation["steps"].append({
            "type": "minimum_applied",
            "original": fee_amount,
            "minimum": rule.minimum_fee
        })
        fee_amount = rule.minimum_fee

    # Apply maximum fee
    if rule.maximum_fee is not None and fee_amount > rule.maximum_fee:
        calculation["steps"].append({
            "type": "maximum_applied",
            "original": fee_amount,
            "maximum": rule.maximum_fee
        })
        fee_amount = rule.maximum_fee

    calculation["final_amount"] = fee_amount

    return calculation


def evaluate_no_show_detection(
    context: NoShowContext,
    policy: NoShowPolicy
) -> NoShowEvaluation:
    """Evaluate if booking should be marked as no-show."""

    # Calculate timing
    minutes_since_scheduled = (
        context.current_time - context.scheduled_at
    ).total_seconds() / 60

    # Check if grace period has expired
    grace_period_expired = minutes_since_scheduled > policy.detection_delay_minutes

    # Determine if should mark as no-show
    should_mark = False
    reason = None
    fee_amount = 0.0
    fee_calculation = {}

    if grace_period_expired:
        if not context.client_arrived and context.professional_arrived:
            # Client no-show
            should_mark = True
            reason = NoShowReason.CLIENT_NO_SHOW
            fee_calculation = calculate_no_show_fee(
                context,
                policy.client_no_show_rule
            )
            fee_amount = fee_calculation["final_amount"]

        elif context.client_arrived and not context.professional_arrived:
            # Professional no-show
            should_mark = True
            reason = NoShowReason.PROFESSIONAL_NO_SHOW
            if policy.professional_no_show_rule:
                fee_calculation = calculate_no_show_fee(
                    context,
                    policy.professional_no_show_rule
                )
                fee_amount = fee_calculation["final_amount"]

    # Calculate dispute deadline
    dispute_deadline = None
    if should_mark and policy.dispute_window_hours > 0:
        dispute_deadline = context.current_time + timedelta(
            hours=policy.dispute_window_hours
        )

    return NoShowEvaluation(
        should_mark_no_show=should_mark,
        reason=reason,
        fee_amount=fee_amount,
        fee_calculation=fee_calculation,
        detection_time=context.current_time,
        grace_period_expired=grace_period_expired,
        minutes_late=max(0, int(minutes_since_scheduled)),
        policy_id=policy.id,
        auto_detected=policy.auto_detect_enabled,
        can_dispute=should_mark,
        dispute_deadline=dispute_deadline,
        recommended_action="mark_no_show" if should_mark else "wait_longer"
    )
