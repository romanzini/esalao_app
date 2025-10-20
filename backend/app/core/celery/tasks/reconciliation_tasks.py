"""
Celery tasks for payment reconciliation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.app.core.celery.app import celery_app, PaymentTask
from backend.app.db.session import get_sync_db
from backend.app.db.models.payment import Payment, PaymentStatus, Refund, RefundStatus
from backend.app.domain.payments.logging_service import get_payment_logger
from backend.app.domain.payments.providers.factory import get_payment_provider


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=PaymentTask, name="reconciliation.daily_reconciliation")
def daily_reconciliation(
    self,
    target_date: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform daily payment reconciliation.

    Args:
        target_date: Date to reconcile (YYYY-MM-DD), defaults to yesterday
        correlation_id: Request correlation ID

    Returns:
        Reconciliation result with summary
    """
    if target_date:
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        target_date_obj = (datetime.utcnow() - timedelta(days=1)).date()

    start_time = datetime.combine(target_date_obj, datetime.min.time())
    end_time = datetime.combine(target_date_obj, datetime.max.time())

    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Log reconciliation start
            payment_logger.log(
                log_type="reconciliation_run",
                message=f"Starting daily reconciliation for {target_date_obj}",
                level="INFO",
                correlation_id=correlation_id,
                request_data={"target_date": target_date_obj.isoformat()},
            )

            # Get payments for the target date
            payments = db.query(Payment).filter(
                and_(
                    Payment.created_at >= start_time,
                    Payment.created_at <= end_time,
                )
            ).all()

            # Initialize counters
            total_payments = len(payments)
            processed_count = 0
            discrepancy_count = 0
            error_count = 0
            discrepancies = []

            # Group payments by provider
            providers = {}
            for payment in payments:
                if payment.provider not in providers:
                    providers[payment.provider] = []
                providers[payment.provider].append(payment)

            # Reconcile each provider
            for provider_name, provider_payments in providers.items():
                try:
                    provider_result = reconcile_provider_payments(
                        provider=provider_name,
                        payments=provider_payments,
                        correlation_id=correlation_id,
                    )

                    processed_count += provider_result["processed_count"]
                    discrepancy_count += provider_result["discrepancy_count"]
                    discrepancies.extend(provider_result["discrepancies"])

                except Exception as exc:
                    error_count += 1
                    logger.error(f"Error reconciling {provider_name}: {exc}")

                    payment_logger.log_provider_error(
                        provider=provider_name,
                        operation="daily_reconciliation",
                        error=exc,
                        correlation_id=correlation_id,
                    )

            # Calculate summary
            total_amount = sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
            successful_payments = len([p for p in payments if p.status == PaymentStatus.COMPLETED])
            failed_payments = len([p for p in payments if p.status == PaymentStatus.FAILED])
            pending_payments = len([p for p in payments if p.status == PaymentStatus.PENDING])

            result = {
                "status": "completed",
                "target_date": target_date_obj.isoformat(),
                "summary": {
                    "total_payments": total_payments,
                    "successful_payments": successful_payments,
                    "failed_payments": failed_payments,
                    "pending_payments": pending_payments,
                    "total_amount": float(total_amount),
                    "processed_count": processed_count,
                    "discrepancy_count": discrepancy_count,
                    "error_count": error_count,
                },
                "discrepancies": discrepancies,
            }

            # Log reconciliation completion
            payment_logger.log(
                log_type="reconciliation_run",
                message=f"Daily reconciliation completed for {target_date_obj}",
                level="INFO" if discrepancy_count == 0 else "WARNING",
                correlation_id=correlation_id,
                response_data=result,
            )

            return result

        except Exception as exc:
            payment_logger.log_exception(
                exception=exc,
                context=f"daily_reconciliation for {target_date_obj}",
                correlation_id=correlation_id,
            )

            raise


def reconcile_provider_payments(
    provider: str,
    payments: List[Payment],
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reconcile payments with specific provider.

    Args:
        provider: Payment provider name
        payments: List of payments to reconcile
        correlation_id: Request correlation ID

    Returns:
        Reconciliation result for provider
    """
    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get provider instance
            payment_provider = get_payment_provider(provider)

            processed_count = 0
            discrepancy_count = 0
            discrepancies = []

            for payment in payments:
                try:
                    # Get status from provider
                    provider_status = payment_provider.get_payment_status(
                        payment.provider_transaction_id
                    )

                    # Check for discrepancies
                    if provider_status.status != payment.status:
                        discrepancy = {
                            "payment_id": payment.id,
                            "external_id": payment.external_id,
                            "provider_transaction_id": payment.provider_transaction_id,
                            "local_status": payment.status,
                            "provider_status": provider_status.status,
                            "amount": float(payment.amount),
                            "created_at": payment.created_at.isoformat(),
                        }
                        discrepancies.append(discrepancy)
                        discrepancy_count += 1

                        # Log discrepancy
                        payment_logger.log(
                            log_type="reconciliation_mismatch",
                            message=f"Status mismatch for payment {payment.external_id}: {payment.status} vs {provider_status.status}",
                            level="WARNING",
                            payment_id=payment.id,
                            provider=provider,
                            correlation_id=correlation_id,
                            request_data=discrepancy,
                        )

                        # Auto-correct if provider shows completed and we show pending
                        if (payment.status == PaymentStatus.PENDING and
                            provider_status.status == PaymentStatus.COMPLETED):

                            old_status = payment.status
                            payment.status = provider_status.status
                            payment.updated_at = datetime.utcnow()

                            payment_logger.log_payment_updated(
                                payment=payment,
                                old_status=old_status,
                                new_status=payment.status,
                                correlation_id=correlation_id,
                                context={"reconciliation_auto_correction": True},
                            )

                            db.commit()

                    processed_count += 1

                except Exception as exc:
                    logger.error(f"Error reconciling payment {payment.id}: {exc}")
                    payment_logger.log_provider_error(
                        provider=provider,
                        operation="reconcile_payment",
                        error=exc,
                        payment_id=payment.id,
                        correlation_id=correlation_id,
                    )

            return {
                "processed_count": processed_count,
                "discrepancy_count": discrepancy_count,
                "discrepancies": discrepancies,
            }

        except Exception as exc:
            payment_logger.log_provider_error(
                provider=provider,
                operation="reconcile_provider_payments",
                error=exc,
                correlation_id=correlation_id,
            )
            raise


@celery_app.task(bind=True, base=PaymentTask, name="reconciliation.sync_provider_payments")
def sync_provider_payments(
    self,
    provider: str,
    start_date: str,
    end_date: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sync payments from provider for date range.

    Args:
        provider: Payment provider name
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        correlation_id: Request correlation ID

    Returns:
        Sync result with statistics
    """
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Get provider instance
            payment_provider = get_payment_provider(provider)

            # TODO: Implement provider-specific payment listing
            # This would depend on each provider's API capabilities
            # For now, we'll focus on syncing existing payments

            # Get payments in date range for this provider
            payments = db.query(Payment).filter(
                and_(
                    Payment.provider == provider,
                    Payment.created_at >= start_date_obj,
                    Payment.created_at <= end_date_obj,
                )
            ).all()

            synced_count = 0
            updated_count = 0
            error_count = 0

            for payment in payments:
                try:
                    # Get current status from provider
                    provider_status = payment_provider.get_payment_status(
                        payment.provider_transaction_id
                    )

                    # Update if status changed
                    if provider_status.status != payment.status:
                        old_status = payment.status
                        payment.status = provider_status.status
                        payment.updated_at = datetime.utcnow()

                        payment_logger.log_payment_updated(
                            payment=payment,
                            old_status=old_status,
                            new_status=payment.status,
                            correlation_id=correlation_id,
                            context={"sync_source": "provider_api"},
                        )

                        updated_count += 1

                    synced_count += 1

                except Exception as exc:
                    error_count += 1
                    payment_logger.log_provider_error(
                        provider=provider,
                        operation="sync_payment",
                        error=exc,
                        payment_id=payment.id,
                        correlation_id=correlation_id,
                    )

            db.commit()

            result = {
                "status": "completed",
                "provider": provider,
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
                "statistics": {
                    "total_payments": len(payments),
                    "synced_count": synced_count,
                    "updated_count": updated_count,
                    "error_count": error_count,
                },
            }

            payment_logger.log(
                log_type="reconciliation_run",
                message=f"Provider sync completed for {provider}: {synced_count} synced, {updated_count} updated",
                level="INFO",
                provider=provider,
                correlation_id=correlation_id,
                response_data=result,
            )

            return result

        except Exception as exc:
            payment_logger.log_exception(
                exception=exc,
                context=f"sync_provider_payments {provider} {start_date} to {end_date}",
                correlation_id=correlation_id,
            )

            raise


@celery_app.task(bind=True, base=PaymentTask, name="reconciliation.generate_settlement_report")
def generate_settlement_report(
    self,
    start_date: str,
    end_date: str,
    provider: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate settlement report for date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        provider: Optional provider filter
        correlation_id: Request correlation ID

    Returns:
        Settlement report data
    """
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    with get_sync_db() as db:
        payment_logger = get_payment_logger(db)

        try:
            # Build query
            query = db.query(Payment).filter(
                and_(
                    Payment.created_at >= start_date_obj,
                    Payment.created_at <= end_date_obj,
                )
            )

            if provider:
                query = query.filter(Payment.provider == provider)

            payments = query.all()

            # Calculate statistics
            total_payments = len(payments)
            completed_payments = [p for p in payments if p.status == PaymentStatus.COMPLETED]
            failed_payments = [p for p in payments if p.status == PaymentStatus.FAILED]
            pending_payments = [p for p in payments if p.status == PaymentStatus.PENDING]

            gross_revenue = sum(p.amount for p in completed_payments)

            # Calculate refunds
            refund_query = db.query(Refund).join(Payment).filter(
                and_(
                    Refund.created_at >= start_date_obj,
                    Refund.created_at <= end_date_obj,
                    Refund.status == RefundStatus.COMPLETED,
                )
            )

            if provider:
                refund_query = refund_query.filter(Payment.provider == provider)

            refunds = refund_query.all()
            total_refunds = sum(r.amount for r in refunds)

            net_revenue = gross_revenue - total_refunds

            # Group by provider
            provider_stats = {}
            for payment in completed_payments:
                if payment.provider not in provider_stats:
                    provider_stats[payment.provider] = {
                        "count": 0,
                        "amount": Decimal("0"),
                    }
                provider_stats[payment.provider]["count"] += 1
                provider_stats[payment.provider]["amount"] += payment.amount

            # Convert Decimal to float for JSON serialization
            for provider_name in provider_stats:
                provider_stats[provider_name]["amount"] = float(provider_stats[provider_name]["amount"])

            report = {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "provider_filter": provider,
                },
                "summary": {
                    "total_payments": total_payments,
                    "completed_payments": len(completed_payments),
                    "failed_payments": len(failed_payments),
                    "pending_payments": len(pending_payments),
                    "gross_revenue": float(gross_revenue),
                    "total_refunds": float(total_refunds),
                    "net_revenue": float(net_revenue),
                    "refund_count": len(refunds),
                },
                "provider_breakdown": provider_stats,
                "generated_at": datetime.utcnow().isoformat(),
            }

            payment_logger.log(
                log_type="reconciliation_run",
                message=f"Settlement report generated for {start_date} to {end_date}",
                level="INFO",
                correlation_id=correlation_id,
                response_data={"summary": report["summary"]},
            )

            return report

        except Exception as exc:
            payment_logger.log_exception(
                exception=exc,
                context=f"generate_settlement_report {start_date} to {end_date}",
                correlation_id=correlation_id,
            )

            raise
