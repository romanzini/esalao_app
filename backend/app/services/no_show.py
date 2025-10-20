"""No-show management service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.domain.policies.no_show import (
    NoShowContext,
    NoShowEvaluation,
    NoShowPolicy,
    NoShowReason,
    NoShowFeeRule,
    evaluate_no_show_detection,
)

logger = logging.getLogger(__name__)


class NoShowService:
    """Service for managing no-show detection and processing."""

    def __init__(
        self,
        booking_repository: BookingRepository,
        user_repository: UserRepository,
    ):
        """Initialize no-show service."""
        self.booking_repository = booking_repository
        self.user_repository = user_repository

    async def get_default_no_show_policy(self) -> NoShowPolicy:
        """Get default no-show policy."""
        # For now, return a hardcoded policy
        # TODO: Load from database in future
        return NoShowPolicy(
            id=1,
            name="Default No-Show Policy",
            description="Standard no-show policy for all bookings",
            is_active=True,
            auto_detect_enabled=True,
            detection_delay_minutes=15,
            client_no_show_rule=NoShowFeeRule(
                base_percentage=50.0,
                minimum_fee=10.0,
                maximum_fee=100.0,
                grace_period_minutes=15,
            ),
            professional_no_show_rule=NoShowFeeRule(
                base_percentage=0.0,  # No fee for professional no-show
                grace_period_minutes=15,
            ),
            dispute_window_hours=24,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def evaluate_booking_for_no_show(
        self,
        booking_id: int,
        current_time: Optional[datetime] = None
    ) -> NoShowEvaluation:
        """Evaluate if a booking should be marked as no-show."""

        # Get booking details
        booking = await self.booking_repository.get_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking not found: {booking_id}")

        # Check if booking is eligible for no-show evaluation
        if booking.status not in [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]:
            raise ValueError(
                f"Booking cannot be evaluated for no-show. Status: {booking.status}"
            )

        # Check if already marked as no-show
        if booking.marked_no_show_at:
            raise ValueError(
                f"Booking already marked as no-show at {booking.marked_no_show_at}"
            )

        current_time = current_time or datetime.utcnow()

        # Build context
        context = NoShowContext(
            booking_id=booking.id,
            client_id=booking.client_id,
            professional_id=booking.professional_id,
            service_id=booking.service_id,
            unit_id=booking.unit_id,
            scheduled_at=booking.scheduled_at,
            service_duration_minutes=booking.duration_minutes,
            service_price=float(booking.price),
            current_time=current_time,
            booking_status=booking.status.value,
            # TODO: Get actual arrival status from check-in system
            client_arrived=False,
            professional_arrived=True,
            # TODO: Get client history
            previous_no_shows=0,
            client_reputation_score=100.0,
        )

        # Get policy
        policy = await self.get_default_no_show_policy()

        # Evaluate
        evaluation = evaluate_no_show_detection(context, policy)

        logger.info(
            f"No-show evaluation for booking {booking_id}: "
            f"should_mark={evaluation.should_mark_no_show}, "
            f"reason={evaluation.reason}, "
            f"fee={evaluation.fee_amount}"
        )

        return evaluation

    async def mark_booking_no_show(
        self,
        booking_id: int,
        marked_by_id: int,
        reason: NoShowReason,
        manual_fee_amount: Optional[float] = None,
        reason_notes: Optional[str] = None,
        current_time: Optional[datetime] = None
    ) -> Booking:
        """Mark a booking as no-show."""

        current_time = current_time or datetime.utcnow()

        # Get and validate booking
        booking = await self.booking_repository.get_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking not found: {booking_id}")

        if booking.marked_no_show_at:
            raise ValueError("Booking already marked as no-show")

        # Validate user marking the no-show
        marking_user = await self.user_repository.get_by_id(marked_by_id)
        if not marking_user:
            raise ValueError(f"User not found: {marked_by_id}")

        # Get evaluation if not manual override
        fee_amount = manual_fee_amount
        if fee_amount is None:
            evaluation = await self.evaluate_booking_for_no_show(
                booking_id, current_time
            )
            fee_amount = evaluation.fee_amount

        # Update booking
        booking.marked_no_show_at = current_time
        booking.marked_no_show_by_id = marked_by_id
        booking.no_show_fee_amount = fee_amount
        booking.no_show_reason = reason.value

        # Add reason notes if provided
        if reason_notes:
            full_reason = f"{reason.value}: {reason_notes}"
            booking.no_show_reason = full_reason[:255]  # Truncate if too long

        # Update booking status if not already completed/cancelled
        if booking.status in [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]:
            booking.status = BookingStatus.NO_SHOW

        # Save changes
        await self.booking_repository.update(booking)

        logger.info(
            f"Booking {booking_id} marked as no-show by user {marked_by_id}. "
            f"Reason: {reason.value}, Fee: {fee_amount}"
        )

        return booking

    async def auto_detect_no_shows(
        self,
        time_window_hours: int = 24,
        current_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Auto-detect and mark no-shows for recent bookings."""

        current_time = current_time or datetime.utcnow()

        # Find bookings that might be no-shows
        start_time = current_time - timedelta(hours=time_window_hours)

        # Get confirmed bookings in the time window
        candidate_bookings = await self.booking_repository.find_by_criteria(
            status=BookingStatus.CONFIRMED,
            scheduled_after=start_time,
            scheduled_before=current_time,
            exclude_no_show=True
        )

        results = []

        for booking in candidate_bookings:
            try:
                # Evaluate each booking
                evaluation = await self.evaluate_booking_for_no_show(
                    booking.id, current_time
                )

                if evaluation.should_mark_no_show:
                    # Auto-mark as no-show
                    marked_booking = await self.mark_booking_no_show(
                        booking_id=booking.id,
                        marked_by_id=1,  # System user ID
                        reason=evaluation.reason,
                        manual_fee_amount=evaluation.fee_amount,
                        reason_notes="Auto-detected by system",
                        current_time=current_time
                    )

                    results.append({
                        "booking_id": booking.id,
                        "action": "marked_no_show",
                        "reason": evaluation.reason.value,
                        "fee_amount": evaluation.fee_amount,
                        "marked_at": marked_booking.marked_no_show_at
                    })
                else:
                    results.append({
                        "booking_id": booking.id,
                        "action": "no_action",
                        "reason": "conditions_not_met",
                        "minutes_late": evaluation.minutes_late
                    })

            except Exception as e:
                logger.error(
                    f"Error evaluating booking {booking.id} for no-show: {e}"
                )
                results.append({
                    "booking_id": booking.id,
                    "action": "error",
                    "error": str(e)
                })

        logger.info(
            f"Auto no-show detection completed. Processed {len(candidate_bookings)} "
            f"bookings, marked {len([r for r in results if r['action'] == 'marked_no_show'])} as no-show"
        )

        return results

    async def dispute_no_show(
        self,
        booking_id: int,
        disputed_by_id: int,
        dispute_reason: str,
        current_time: Optional[datetime] = None
    ) -> Booking:
        """Dispute a no-show marking."""

        current_time = current_time or datetime.utcnow()

        # Get booking
        booking = await self.booking_repository.get_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking not found: {booking_id}")

        if not booking.marked_no_show_at:
            raise ValueError("Booking is not marked as no-show")

        # Check dispute window
        policy = await self.get_default_no_show_policy()
        dispute_deadline = booking.marked_no_show_at + timedelta(
            hours=policy.dispute_window_hours
        )

        if current_time > dispute_deadline:
            raise ValueError(
                f"Dispute window expired. Deadline was {dispute_deadline}"
            )

        # Validate disputing user
        disputing_user = await self.user_repository.get_by_id(disputed_by_id)
        if not disputing_user:
            raise ValueError(f"User not found: {disputed_by_id}")

        # For now, just log the dispute
        # TODO: Implement dispute workflow
        logger.info(
            f"No-show dispute filed for booking {booking_id} by user {disputed_by_id}. "
            f"Reason: {dispute_reason}"
        )

        return booking

    async def can_dispute_no_show(
        self,
        booking_id: int,
        user_id: int,
        current_time: Optional[datetime] = None
    ) -> Dict:
        """Check if user can dispute a no-show marking."""

        current_time = current_time or datetime.utcnow()

        # Get booking
        booking = await self.booking_repository.get_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking not found: {booking_id}")

        if not booking.marked_no_show_at:
            return {
                "can_dispute": False,
                "reason": "booking_not_marked_no_show"
            }

        # Check if user is the client
        if booking.client_id != user_id:
            return {
                "can_dispute": False,
                "reason": "not_booking_client"
            }

        # Check dispute window
        policy = await self.get_default_no_show_policy()
        dispute_deadline = booking.marked_no_show_at + timedelta(
            hours=policy.dispute_window_hours
        )

        if current_time > dispute_deadline:
            return {
                "can_dispute": False,
                "reason": "dispute_window_expired",
                "deadline": dispute_deadline
            }

        return {
            "can_dispute": True,
            "deadline": dispute_deadline,
            "hours_remaining": (dispute_deadline - current_time).total_seconds() / 3600
        }

    async def get_no_show_statistics(
        self,
        unit_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get no-show statistics for a period."""

        # Default to last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Build filter criteria
        criteria = {
            "scheduled_after": start_date,
            "scheduled_before": end_date
        }

        if unit_id:
            criteria["unit_id"] = unit_id
        if professional_id:
            criteria["professional_id"] = professional_id

        # Get all bookings in period
        all_bookings = await self.booking_repository.find_by_criteria(**criteria)

        # Calculate statistics
        total_bookings = len(all_bookings)
        no_show_bookings = [b for b in all_bookings if b.marked_no_show_at]

        total_no_shows = len(no_show_bookings)

        # Calculate fees
        total_fees = sum(
            float(b.no_show_fee_amount or 0) for b in no_show_bookings
        )

        # Calculate rates
        no_show_rate = (total_no_shows / total_bookings * 100) if total_bookings > 0 else 0

        # Reason breakdown
        reasons = {}
        for booking in no_show_bookings:
            reason = booking.no_show_reason or "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1

        return {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "totals": {
                "bookings": total_bookings,
                "no_shows": total_no_shows,
                "no_show_rate": round(no_show_rate, 2)
            },
            "financial": {
                "total_fees_charged": total_fees,
                "average_fee": round(total_fees / total_no_shows, 2) if total_no_shows > 0 else 0
            },
            "reasons": reasons,
            "filters": {
                "unit_id": unit_id,
                "professional_id": professional_id
            }
        }
