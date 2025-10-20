"""
Payment Reconciliation Service.

This service handles synchronization of payment states between
our database and payment providers, ensuring data consistency.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.payment import Payment, PaymentStatus as ModelPaymentStatus
from backend.app.domain.payments import (
    PaymentProvider,
    PaymentStatus,
    PaymentProviderError,
    PaymentProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class ReconciliationResult:
    """Result of payment reconciliation process."""

    def __init__(self):
        self.processed_count = 0
        self.updated_count = 0
        self.error_count = 0
        self.errors: List[str] = []
        self.updated_payments: List[int] = []

    def add_update(self, payment_id: int):
        """Record a successful payment update."""
        self.processed_count += 1
        self.updated_count += 1
        self.updated_payments.append(payment_id)

    def add_error(self, payment_id: int, error: str):
        """Record a reconciliation error."""
        self.processed_count += 1
        self.error_count += 1
        self.errors.append(f"Payment {payment_id}: {error}")

    def add_no_change(self, payment_id: int):
        """Record a payment with no changes."""
        self.processed_count += 1


class ReconciliationService:
    """
    Service for reconciling payment states with providers.

    This service periodically checks payment statuses with providers
    to ensure our local database stays in sync.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._providers: Dict[str, PaymentProvider] = {}

    def register_provider(self, name: str, provider: PaymentProvider):
        """Register a payment provider for reconciliation."""
        self._providers[name] = provider

    async def reconcile_pending_payments(
        self,
        max_age_hours: int = 24,
        limit: int = 100
    ) -> ReconciliationResult:
        """
        Reconcile pending payments that may have status updates.

        Args:
            max_age_hours: Maximum age of payments to reconcile
            limit: Maximum number of payments to process

        Returns:
            ReconciliationResult with processing statistics
        """
        result = ReconciliationResult()

        # Find pending/processing payments within age limit
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        stmt = select(Payment).where(
            and_(
                Payment.status.in_([
                    ModelPaymentStatus.PENDING.value,
                    ModelPaymentStatus.PROCESSING.value
                ]),
                Payment.created_at >= cutoff_time
            )
        ).limit(limit)

        pending_payments = await self.db.execute(stmt)
        payments = pending_payments.scalars().all()

        logger.info(f"Found {len(payments)} payments to reconcile")

        for payment in payments:
            try:
                await self._reconcile_single_payment(payment, result)
            except Exception as e:
                error_msg = f"Unexpected error reconciling payment: {str(e)}"
                result.add_error(payment.id, error_msg)
                logger.error(error_msg, exc_info=True)

        await self.db.commit()

        logger.info(
            f"Reconciliation completed: {result.processed_count} processed, "
            f"{result.updated_count} updated, {result.error_count} errors"
        )

        return result

    async def reconcile_single_payment(self, payment_id: int) -> ReconciliationResult:
        """
        Reconcile a single payment by ID.

        Args:
            payment_id: ID of payment to reconcile

        Returns:
            ReconciliationResult for this payment
        """
        result = ReconciliationResult()

        payment = await self.db.get(Payment, payment_id)
        if not payment:
            result.add_error(payment_id, "Payment not found")
            return result

        try:
            await self._reconcile_single_payment(payment, result)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            error_msg = f"Failed to reconcile payment: {str(e)}"
            result.add_error(payment_id, error_msg)
            logger.error(error_msg, exc_info=True)

        return result

    async def _reconcile_single_payment(
        self,
        payment: Payment,
        result: ReconciliationResult
    ):
        """Reconcile a single payment with its provider."""
        provider = self._providers.get(payment.provider_name)
        if not provider:
            result.add_error(
                payment.id,
                f"Provider {payment.provider_name} not registered"
            )
            return

        try:
            # Get current status from provider
            provider_response = await provider.get_payment_status(
                payment.provider_payment_id
            )

            # Compare statuses
            current_status = payment.status
            provider_status = provider_response.status.value

            if current_status != provider_status:
                # Update payment status
                old_status = payment.status
                payment.status = provider_status
                payment.update_status_timestamps()
                payment.updated_at = datetime.now(timezone.utc)

                # Update provider data if available
                if provider_response.provider_data:
                    payment.provider_data = provider_response.provider_data

                logger.info(
                    f"Payment {payment.id} status updated from "
                    f"{old_status} to {provider_status}"
                )

                result.add_update(payment.id)
            else:
                result.add_no_change(payment.id)

        except PaymentProviderUnavailableError as e:
            result.add_error(
                payment.id,
                f"Provider temporarily unavailable: {str(e)}"
            )
        except PaymentProviderError as e:
            result.add_error(
                payment.id,
                f"Provider error: {str(e)}"
            )

    async def reconcile_stale_payments(
        self,
        stale_hours: int = 168,  # 1 week
        limit: int = 50
    ) -> ReconciliationResult:
        """
        Reconcile payments that haven't been updated recently.

        This is useful for catching payments that may have been
        updated via webhooks that we missed.

        Args:
            stale_hours: Hours since last update to consider stale
            limit: Maximum number of payments to process

        Returns:
            ReconciliationResult with processing statistics
        """
        result = ReconciliationResult()

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=stale_hours)

        stmt = select(Payment).where(
            and_(
                Payment.status.in_([
                    ModelPaymentStatus.PENDING.value,
                    ModelPaymentStatus.PROCESSING.value,
                    ModelPaymentStatus.SUCCEEDED.value  # Check successful payments too
                ]),
                or_(
                    Payment.last_webhook_at.is_(None),
                    Payment.last_webhook_at < cutoff_time
                ),
                Payment.updated_at < cutoff_time
            )
        ).limit(limit)

        stale_payments = await self.db.execute(stmt)
        payments = stale_payments.scalars().all()

        logger.info(f"Found {len(payments)} stale payments to reconcile")

        for payment in payments:
            try:
                await self._reconcile_single_payment(payment, result)
            except Exception as e:
                error_msg = f"Unexpected error reconciling stale payment: {str(e)}"
                result.add_error(payment.id, error_msg)
                logger.error(error_msg, exc_info=True)

        await self.db.commit()

        logger.info(
            f"Stale payment reconciliation completed: {result.processed_count} processed, "
            f"{result.updated_count} updated, {result.error_count} errors"
        )

        return result

    async def get_reconciliation_candidates(
        self,
        hours_old: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get list of payments that are candidates for reconciliation.

        Args:
            hours_old: Minimum age in hours for payments to be candidates

        Returns:
            List of payment information for reconciliation candidates
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)

        stmt = select(Payment).where(
            and_(
                Payment.status.in_([
                    ModelPaymentStatus.PENDING.value,
                    ModelPaymentStatus.PROCESSING.value
                ]),
                Payment.created_at <= cutoff_time
            )
        ).order_by(Payment.created_at.asc())

        candidates = await self.db.execute(stmt)
        payments = candidates.scalars().all()

        return [
            {
                "id": payment.id,
                "provider_name": payment.provider_name,
                "provider_payment_id": payment.provider_payment_id,
                "status": payment.status,
                "amount": float(payment.amount),
                "created_at": payment.created_at.isoformat(),
                "last_webhook_at": payment.last_webhook_at.isoformat() if payment.last_webhook_at else None,
                "age_hours": (datetime.now(timezone.utc) - payment.created_at).total_seconds() / 3600
            }
            for payment in payments
        ]

    async def get_reconciliation_stats(self) -> Dict[str, Any]:
        """Get statistics about payment reconciliation needs."""
        now = datetime.now(timezone.utc)

        # Count payments by status and age
        stats = {
            "pending_1h": 0,
            "pending_24h": 0,
            "pending_7d": 0,
            "processing_1h": 0,
            "processing_24h": 0,
            "stale_succeeded": 0,
            "providers": list(self._providers.keys())
        }

        # Pending payments
        for hours, key_prefix in [(1, "1h"), (24, "24h"), (168, "7d")]:
            cutoff = now - timedelta(hours=hours)

            if key_prefix != "7d":  # Don't count processing for 7d
                processing_count = await self.db.scalar(
                    select(Payment).where(
                        and_(
                            Payment.status == ModelPaymentStatus.PROCESSING.value,
                            Payment.created_at <= cutoff
                        )
                    ).with_only_columns([Payment.id]).count()
                )
                stats[f"processing_{key_prefix}"] = processing_count or 0

            pending_count = await self.db.scalar(
                select(Payment).where(
                    and_(
                        Payment.status == ModelPaymentStatus.PENDING.value,
                        Payment.created_at <= cutoff
                    )
                ).with_only_columns([Payment.id]).count()
            )
            stats[f"pending_{key_prefix}"] = pending_count or 0

        # Stale succeeded payments (no webhook in 7 days)
        stale_cutoff = now - timedelta(days=7)
        stale_succeeded = await self.db.scalar(
            select(Payment).where(
                and_(
                    Payment.status == ModelPaymentStatus.SUCCEEDED.value,
                    or_(
                        Payment.last_webhook_at.is_(None),
                        Payment.last_webhook_at < stale_cutoff
                    )
                )
            ).with_only_columns([Payment.id]).count()
        )
        stats["stale_succeeded"] = stale_succeeded or 0

        return stats
