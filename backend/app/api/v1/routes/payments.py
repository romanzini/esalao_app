"""
Payment routes for handling payment operations.

This module provides endpoints for creating payments, checking status,
and handling refunds through various payment providers.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.rbac import require_role
from backend.app.db.models.user import UserRole
from backend.app.db.session import get_db
from backend.app.domain.payments import (
    PaymentMethod,
    PaymentStatus,
    PaymentRequest,
    PaymentProviderError,
    PaymentProviderUnavailableError,
)
from backend.app.services.payment_notifications import PaymentNotificationService

# TODO: Import payment service when implemented
# from backend.app.domain.payments.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])
security = HTTPBearer()


class PaymentCreateRequest(BaseModel):
    """Request model for creating a payment."""

    amount: Decimal = Field(..., gt=0, description="Payment amount in BRL")
    payment_method: PaymentMethod = Field(..., description="Payment method to use")
    booking_id: Optional[int] = Field(None, description="Related booking ID")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    customer_email: Optional[str] = Field(None, description="Customer email for payment")
    customer_name: Optional[str] = Field(None, description="Customer name for payment")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key for duplicate prevention")

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > Decimal('99999.99'):
            raise ValueError('Amount too large')
        return v

    @validator('customer_email')
    def validate_email(cls, v):
        if v is not None and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class PaymentResponse(BaseModel):
    """Response model for payment operations."""

    id: int
    provider_payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    payment_url: Optional[str] = None
    booking_id: Optional[int] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PaymentStatusResponse(BaseModel):
    """Response model for payment status checks."""

    id: int
    status: PaymentStatus
    provider_payment_id: str
    amount: Decimal
    paid_at: Optional[str] = None
    failed_at: Optional[str] = None
    canceled_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new payment",
    description="Create a new payment with the specified provider and method",
)
async def create_payment(
    payment_data: PaymentCreateRequest,
    current_user: Any = Depends(require_role([UserRole.CLIENT, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Create a new payment.

    This endpoint creates a payment with the configured payment provider.
    For PIX payments, it returns a payment URL with QR code.
    For card payments, it returns a checkout URL.

    - **amount**: Payment amount in BRL (must be positive)
    - **payment_method**: Method to use (pix, credit_card, debit_card)
    - **booking_id**: Optional booking to associate with payment
    - **idempotency_key**: Optional key to prevent duplicate payments
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payment = await payment_service.create_payment(
        #     user_id=current_user.id,
        #     request=PaymentRequest(
        #         amount=payment_data.amount,
        #         payment_method=payment_data.payment_method,
        #         customer_email=payment_data.customer_email or current_user.email,
        #         customer_name=payment_data.customer_name or current_user.name,
        #         description=payment_data.description,
        #         metadata={"booking_id": payment_data.booking_id}
        #     ),
        #     booking_id=payment_data.booking_id,
        #     idempotency_key=payment_data.idempotency_key
        # )
        #
        # # Send payment notifications based on method and status
        # try:
        #     notification_service = PaymentNotificationService(db)
        #     if payment.status == PaymentStatus.CONFIRMED:
        #         await notification_service.notify_payment_received(
        #             payment_id=payment.id,
        #             correlation_id=f"payment_create_{payment.id}"
        #         )
        #     elif payment.status == PaymentStatus.PENDING:
        #         await notification_service.notify_payment_pending(
        #             payment_id=payment.id,
        #             payment_method=payment_data.payment_method,
        #             correlation_id=f"payment_create_{payment.id}"
        #         )
        # except Exception as e:
        #     # Log notification error but don't fail the payment creation
        #     import logging
        #     logger = logging.getLogger(__name__)
        #     logger.error(f"Failed to send payment notification for payment {payment.id}: {str(e)}")
        #
        # return PaymentResponse.from_orm(payment)

        # Placeholder response for now
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Payment service not yet implemented. Complete TASK-0200 and TASK-0201 first."
        )

    except PaymentProviderUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Payment provider temporarily unavailable: {str(e)}"
        )
    except PaymentProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment failed: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment details",
    description="Retrieve payment details by ID",
)
async def get_payment(
    payment_id: int,
    current_user: Any = Depends(require_role([UserRole.CLIENT, UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Get payment details.

    Retrieves payment information including current status.
    Users can only access their own payments unless they are admins.
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payment = await payment_service.get_payment(
        #     payment_id=payment_id,
        #     user_id=current_user.id if current_user.role != UserRole.ADMIN else None
        # )
        # return PaymentResponse.from_orm(payment)

        # Placeholder response for now
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Payment service not yet implemented"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/{payment_id}/status",
    response_model=PaymentStatusResponse,
    summary="Check payment status",
    description="Check current payment status from provider",
)
async def check_payment_status(
    payment_id: int,
    current_user: Any = Depends(require_role([UserRole.CLIENT, UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> PaymentStatusResponse:
    """
    Check payment status.

    Queries the payment provider for the current status and updates
    the local database if needed.
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # old_status = await payment_service.get_payment_status(payment_id)
        # payment = await payment_service.refresh_payment_status(
        #     payment_id=payment_id,
        #     user_id=current_user.id if current_user.role != UserRole.ADMIN else None
        # )
        #
        # # Send notifications if status changed
        # try:
        #     notification_service = PaymentNotificationService(db)
        #     if old_status != payment.status:
        #         if payment.status == PaymentStatus.CONFIRMED:
        #             await notification_service.notify_payment_received(
        #                 payment_id=payment.id,
        #                 correlation_id=f"payment_status_check_{payment.id}"
        #             )
        #         elif payment.status == PaymentStatus.FAILED:
        #             await notification_service.notify_payment_failed(
        #                 payment_id=payment.id,
        #                 correlation_id=f"payment_status_check_{payment.id}"
        #             )
        # except Exception as e:
        #     # Log notification error but don't fail the status check
        #     import logging
        #     logger = logging.getLogger(__name__)
        #     logger.error(f"Failed to send payment status notification for payment {payment.id}: {str(e)}")
        #
        # return PaymentStatusResponse.from_orm(payment)

        # Placeholder response for now
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Payment service not yet implemented"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
    summary="Cancel payment",
    description="Cancel a pending payment",
)
async def cancel_payment(
    payment_id: int,
    current_user: Any = Depends(require_role([UserRole.CLIENT, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Cancel a payment.

    Cancels a pending payment. Only works for payments that haven't
    been processed yet.
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payment = await payment_service.cancel_payment(
        #     payment_id=payment_id,
        #     user_id=current_user.id if current_user.role != UserRole.ADMIN else None
        # )
        # return PaymentResponse.from_orm(payment)

        # Placeholder response for now
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Payment service not yet implemented"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=list[PaymentResponse],
    summary="List user payments",
    description="List payments for the current user",
)
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[PaymentStatus] = None,
    current_user: Any = Depends(require_role([UserRole.CLIENT, UserRole.ADMIN, UserRole.SALON_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentResponse]:
    """
    List payments for the current user.

    Admins can see all payments, while regular users see only their own.
    """
    try:
        # TODO: Implement payment service integration
        # payment_service = PaymentService(db)
        # payments = await payment_service.list_payments(
        #     user_id=current_user.id if current_user.role != UserRole.ADMIN else None,
        #     skip=skip,
        #     limit=limit,
        #     status_filter=status_filter
        # )
        # return [PaymentResponse.from_orm(payment) for payment in payments]

        # Placeholder response for now
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Payment service not yet implemented"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
