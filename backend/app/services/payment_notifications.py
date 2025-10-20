"""
Payment notification integration service.

This service integrates the notification system with payment events,
automatically sending notifications when payments are processed, received,
failed, or refunded.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.payment import PaymentRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.services.notifications import NotificationService
from backend.app.db.models.payment import Payment, PaymentStatus
from backend.app.db.models.notifications import NotificationEventType, NotificationPriority


logger = logging.getLogger(__name__)


class PaymentNotificationService:
    """Service for handling payment-related notifications."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the payment notification service.

        Args:
            session: Database session
        """
        self.session = session
        self.notification_service = NotificationService(session)
        self.payment_repo = PaymentRepository(session)
        self.booking_repo = BookingRepository(session)
        self.user_repo = UserRepository(session)

    async def notify_payment_received(
        self,
        payment_id: int,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send payment confirmation notifications.

        Args:
            payment_id: ID of the successful payment
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get payment with related data
            payment = await self._get_payment_with_relations(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            # Prepare context data
            context = await self._prepare_payment_context(payment)

            # Send notification to client
            result = await self.notification_service.send_notification(
                user_id=payment.user_id,
                event_type=NotificationEventType.PAYMENT_RECEIVED.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"payment_{payment_id}"
            )

            logger.info(f"Payment confirmation notification sent for payment {payment_id}")

            return {
                "payment_id": payment_id,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send payment confirmation notification for payment {payment_id}: {str(e)}")
            raise

    async def notify_payment_failed(
        self,
        payment_id: int,
        failure_reason: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send payment failure notifications.

        Args:
            payment_id: ID of the failed payment
            failure_reason: Reason for payment failure
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get payment with related data
            payment = await self._get_payment_with_relations(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            # Prepare context data
            context = await self._prepare_payment_context(payment)
            context.update({
                "failure_reason": failure_reason or "Falha no processamento",
                "retry_url": f"{context.get('app_url', '')}/payments/{payment_id}/retry",
                "support_contact": "(11) 99999-9999"  # Should come from config
            })

            # Send notification to client
            result = await self.notification_service.send_notification(
                user_id=payment.user_id,
                event_type=NotificationEventType.PAYMENT_FAILED.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"payment_{payment_id}_failed"
            )

            logger.info(f"Payment failure notification sent for payment {payment_id}")

            return {
                "payment_id": payment_id,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send payment failure notification for payment {payment_id}: {str(e)}")
            raise

    async def notify_refund_processed(
        self,
        payment_id: int,
        refund_amount: Decimal,
        refund_reason: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send refund processing notifications.

        Args:
            payment_id: ID of the payment being refunded
            refund_amount: Amount being refunded
            refund_reason: Reason for the refund
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get payment with related data
            payment = await self._get_payment_with_relations(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            # Prepare context data
            context = await self._prepare_payment_context(payment)
            context.update({
                "refund_amount": f"{refund_amount:.2f}",
                "refund_reason": refund_reason or "Reembolso processado",
                "refund_date": datetime.now().strftime("%d/%m/%Y"),
                "refund_business_days": "3-5",  # Should come from config
                "original_amount": context["payment_amount"]
            })

            # Send notification to client
            result = await self.notification_service.send_notification(
                user_id=payment.user_id,
                event_type=NotificationEventType.REFUND_PROCESSED.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"payment_{payment_id}_refund"
            )

            logger.info(f"Refund notification sent for payment {payment_id}")

            return {
                "payment_id": payment_id,
                "refund_amount": float(refund_amount),
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send refund notification for payment {payment_id}: {str(e)}")
            raise

    async def notify_payment_pending(
        self,
        payment_id: int,
        payment_method: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send payment pending notifications (for methods like bank slip).

        Args:
            payment_id: ID of the pending payment
            payment_method: Payment method used
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get payment with related data
            payment = await self._get_payment_with_relations(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            # Only send for certain payment methods
            if payment_method.lower() not in ['boleto', 'bank_slip', 'pix']:
                return {"payment_id": payment_id, "notifications_queued": 0}

            # Prepare context data
            context = await self._prepare_payment_context(payment)
            context.update({
                "payment_method_name": self._get_payment_method_name(payment_method),
                "due_date": (datetime.now().replace(hour=23, minute=59, second=59)).strftime("%d/%m/%Y às %H:%M"),
                "payment_instructions": self._get_payment_instructions(payment_method)
            })

            # Send notification to client
            result = await self.notification_service.send_notification(
                user_id=payment.user_id,
                event_type=NotificationEventType.PAYMENT_RECEIVED.value,  # Reuse for pending
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"payment_{payment_id}_pending"
            )

            logger.info(f"Payment pending notification sent for payment {payment_id}")

            return {
                "payment_id": payment_id,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send payment pending notification for payment {payment_id}: {str(e)}")
            raise

    async def _get_payment_with_relations(self, payment_id: int) -> Optional[Payment]:
        """Get payment with all related data needed for notifications."""
        return await self.payment_repo.get_payment_with_user(payment_id)

    async def _prepare_payment_context(self, payment: Payment) -> Dict[str, Any]:
        """
        Prepare context data for payment notifications.

        Args:
            payment: Payment instance with relations loaded

        Returns:
            Dictionary with context data for template rendering
        """
        # Get user information
        user = payment.user if hasattr(payment, 'user') and payment.user else await self.user_repo.get_by_id(payment.user_id)

        # Format payment data
        payment_date = payment.created_at.strftime("%d/%m/%Y")
        payment_time = payment.created_at.strftime("%H:%M")

        # Get booking information if available
        booking_info = {}
        if payment.booking_id:
            booking = await self.booking_repo.get_by_id_with_relations(payment.booking_id)
            if booking:
                booking_info.update({
                    "service_name": booking.service.name,
                    "professional_name": booking.professional.user.full_name,
                    "appointment_date": booking.scheduled_at.strftime("%d/%m/%Y"),
                    "appointment_time": booking.scheduled_at.strftime("%H:%M")
                })

        context = {
            "user_name": user.full_name if user else "Cliente",
            "payment_amount": f"{payment.amount:.2f}",
            "payment_method": self._get_payment_method_name(payment.payment_method),
            "payment_date": payment_date,
            "payment_time": payment_time,
            "transaction_id": payment.provider_payment_id or str(payment.id),
            "app_url": "https://esalao.app",  # Should come from config
            "support_email": "suporte@esalao.app",  # Should come from config
        }

        # Add booking information if available
        context.update(booking_info)

        return context

    def _get_payment_method_name(self, payment_method: str) -> str:
        """
        Get human-readable payment method name.

        Args:
            payment_method: Payment method code

        Returns:
            Human-readable payment method name
        """
        method_names = {
            "credit_card": "Cartão de Crédito",
            "debit_card": "Cartão de Débito",
            "pix": "PIX",
            "boleto": "Boleto Bancário",
            "bank_slip": "Boleto Bancário",
            "cash": "Dinheiro",
            "bank_transfer": "Transferência Bancária"
        }
        return method_names.get(payment_method.lower(), payment_method.title())

    def _get_payment_instructions(self, payment_method: str) -> str:
        """
        Get payment-specific instructions.

        Args:
            payment_method: Payment method code

        Returns:
            Payment instructions
        """
        instructions = {
            "pix": "Utilize a chave PIX ou QR Code enviado para completar o pagamento.",
            "boleto": "Pague o boleto em qualquer banco, lotérica ou internet banking até a data de vencimento.",
            "bank_slip": "Pague o boleto em qualquer banco, lotérica ou internet banking até a data de vencimento.",
            "bank_transfer": "Complete a transferência bancária com os dados fornecidos."
        }
        return instructions.get(payment_method.lower(), "Siga as instruções fornecidas para completar o pagamento.")
