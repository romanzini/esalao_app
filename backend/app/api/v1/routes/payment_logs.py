"""
Payment logs API endpoints for audit and debugging.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, and_, or_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.core.auth import require_permissions
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.payment_log import PaymentLog, PaymentLogLevel, PaymentLogType


router = APIRouter()


class PaymentLogResponse(BaseModel):
    """Response model for payment log entries."""

    id: int
    payment_id: Optional[int]
    refund_id: Optional[int]
    booking_id: Optional[int]
    user_id: Optional[int]
    log_type: str
    level: str
    message: str
    provider: Optional[str]
    provider_transaction_id: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    correlation_id: Optional[str]
    processing_time_ms: Optional[int]
    retry_count: int
    timestamp: datetime

    class Config:
        from_attributes = True


class PaymentLogFilter(BaseModel):
    """Filter parameters for payment log queries."""

    payment_id: Optional[int] = Field(None, description="Filter by payment ID")
    refund_id: Optional[int] = Field(None, description="Filter by refund ID")
    booking_id: Optional[int] = Field(None, description="Filter by booking ID")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    log_type: Optional[str] = Field(None, description="Filter by log type")
    level: Optional[str] = Field(None, description="Filter by log level")
    provider: Optional[str] = Field(None, description="Filter by payment provider")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    start_date: Optional[datetime] = Field(None, description="Filter logs after this date")
    end_date: Optional[datetime] = Field(None, description="Filter logs before this date")
    search: Optional[str] = Field(None, description="Search in message and error fields")


class PaymentLogListResponse(BaseModel):
    """Response model for paginated payment log list."""

    logs: List[PaymentLogResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


@router.get("/logs", response_model=PaymentLogListResponse)
@require_permissions(["read:payment_logs"])
async def list_payment_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    payment_id: Optional[int] = Query(None, description="Filter by payment ID"),
    refund_id: Optional[int] = Query(None, description="Filter by refund ID"),
    booking_id: Optional[int] = Query(None, description="Filter by booking ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    log_type: Optional[str] = Query(None, description="Filter by log type"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    provider: Optional[str] = Query(None, description="Filter by payment provider"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Search in messages"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve paginated list of payment logs with filtering.

    Requires `read:payment_logs` permission.
    """
    # Build query with filters
    query = db.query(PaymentLog)

    # Apply filters
    if payment_id:
        query = query.filter(PaymentLog.payment_id == payment_id)

    if refund_id:
        query = query.filter(PaymentLog.refund_id == refund_id)

    if booking_id:
        query = query.filter(PaymentLog.booking_id == booking_id)

    if user_id:
        query = query.filter(PaymentLog.user_id == user_id)

    if log_type:
        query = query.filter(PaymentLog.log_type == log_type)

    if level:
        query = query.filter(PaymentLog.level == level)

    if provider:
        query = query.filter(PaymentLog.provider == provider)

    if correlation_id:
        query = query.filter(PaymentLog.correlation_id == correlation_id)

    if start_date:
        query = query.filter(PaymentLog.timestamp >= start_date)

    if end_date:
        query = query.filter(PaymentLog.timestamp <= end_date)

    if search:
        search_filter = or_(
            PaymentLog.message.ilike(f"%{search}%"),
            PaymentLog.error_message.ilike(f"%{search}%"),
            PaymentLog.provider_transaction_id.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    # Order by timestamp (most recent first)
    query = query.order_by(desc(PaymentLog.timestamp))

    # Get total count for pagination
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()

    return PaymentLogListResponse(
        logs=[PaymentLogResponse.from_orm(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + page_size < total,
        has_prev=page > 1,
    )


@router.get("/logs/{log_id}", response_model=PaymentLogResponse)
@require_permissions(["read:payment_logs"])
async def get_payment_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific payment log entry by ID.

    Requires `read:payment_logs` permission.
    """
    log = db.query(PaymentLog).filter(PaymentLog.id == log_id).first()

    if not log:
        raise HTTPException(status_code=404, detail="Payment log not found")

    return PaymentLogResponse.from_orm(log)


@router.get("/logs/types", response_model=List[str])
@require_permissions(["read:payment_logs"])
async def get_payment_log_types(
    current_user: User = Depends(get_current_user),
):
    """
    Get list of available payment log types.

    Requires `read:payment_logs` permission.
    """
    return [
        PaymentLogType.PAYMENT_CREATED,
        PaymentLogType.PAYMENT_UPDATED,
        PaymentLogType.PAYMENT_CANCELLED,
        PaymentLogType.PAYMENT_COMPLETED,
        PaymentLogType.PAYMENT_FAILED,
        PaymentLogType.PROVIDER_CALL,
        PaymentLogType.PROVIDER_RESPONSE,
        PaymentLogType.PROVIDER_ERROR,
        PaymentLogType.PROVIDER_TIMEOUT,
        PaymentLogType.PROVIDER_RETRY,
        PaymentLogType.WEBHOOK_RECEIVED,
        PaymentLogType.WEBHOOK_PROCESSED,
        PaymentLogType.WEBHOOK_FAILED,
        PaymentLogType.WEBHOOK_DUPLICATE,
        PaymentLogType.WEBHOOK_INVALID,
        PaymentLogType.REFUND_CREATED,
        PaymentLogType.REFUND_PROCESSED,
        PaymentLogType.REFUND_FAILED,
        PaymentLogType.REFUND_CANCELLED,
        PaymentLogType.SECURITY_VIOLATION,
        PaymentLogType.VALIDATION_FAILED,
        PaymentLogType.RATE_LIMIT_EXCEEDED,
        PaymentLogType.RECONCILIATION_RUN,
        PaymentLogType.RECONCILIATION_MISMATCH,
        PaymentLogType.SYSTEM_ERROR,
        PaymentLogType.CONFIG_CHANGED,
    ]


@router.get("/logs/levels", response_model=List[str])
@require_permissions(["read:payment_logs"])
async def get_payment_log_levels(
    current_user: User = Depends(get_current_user),
):
    """
    Get list of available payment log levels.

    Requires `read:payment_logs` permission.
    """
    return [
        PaymentLogLevel.DEBUG,
        PaymentLogLevel.INFO,
        PaymentLogLevel.WARNING,
        PaymentLogLevel.ERROR,
        PaymentLogLevel.CRITICAL,
    ]


@router.get("/logs/stats")
@require_permissions(["read:payment_logs"])
async def get_payment_log_stats(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get payment log statistics for the specified time period.

    Requires `read:payment_logs` permission.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Get log counts by level
    level_stats = {}
    for level in [PaymentLogLevel.DEBUG, PaymentLogLevel.INFO, PaymentLogLevel.WARNING,
                  PaymentLogLevel.ERROR, PaymentLogLevel.CRITICAL]:
        count = db.query(PaymentLog).filter(
            and_(
                PaymentLog.level == level,
                PaymentLog.timestamp >= cutoff_time
            )
        ).count()
        level_stats[level] = count

    # Get log counts by type (top 10)
    type_stats = {}
    for log_type in [PaymentLogType.PAYMENT_CREATED, PaymentLogType.PAYMENT_UPDATED,
                     PaymentLogType.PROVIDER_CALL, PaymentLogType.PROVIDER_RESPONSE,
                     PaymentLogType.WEBHOOK_RECEIVED, PaymentLogType.WEBHOOK_PROCESSED,
                     PaymentLogType.REFUND_CREATED, PaymentLogType.PROVIDER_ERROR]:
        count = db.query(PaymentLog).filter(
            and_(
                PaymentLog.log_type == log_type,
                PaymentLog.timestamp >= cutoff_time
            )
        ).count()
        if count > 0:
            type_stats[log_type] = count

    # Get provider stats
    provider_stats = {}
    providers = db.query(PaymentLog.provider).filter(
        and_(
            PaymentLog.provider.isnot(None),
            PaymentLog.timestamp >= cutoff_time
        )
    ).distinct().all()

    for provider_tuple in providers:
        provider = provider_tuple[0]
        count = db.query(PaymentLog).filter(
            and_(
                PaymentLog.provider == provider,
                PaymentLog.timestamp >= cutoff_time
            )
        ).count()
        provider_stats[provider] = count

    # Get total count
    total_logs = db.query(PaymentLog).filter(
        PaymentLog.timestamp >= cutoff_time
    ).count()

    return {
        "period_hours": hours,
        "total_logs": total_logs,
        "levels": level_stats,
        "types": type_stats,
        "providers": provider_stats,
        "cutoff_time": cutoff_time,
    }
