"""
Cancellation policy domain logic.

This module implements the business logic for cancellation policies,
including policy evaluation, fee calculation, and validation rules.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List
import logging

from backend.app.db.models.cancellation_policy import (
    CancellationPolicy as CancellationPolicyModel,
    CancellationTier as CancellationTierModel,
)

logger = logging.getLogger(__name__)


class CancellationResult(str, Enum):
    """Cancellation evaluation result."""

    ALLOWED_NO_FEE = "allowed_no_fee"
    ALLOWED_WITH_FEE = "allowed_with_fee"
    NOT_ALLOWED = "not_allowed"


@dataclass
class CancellationContext:
    """Context information for cancellation evaluation."""

    booking_id: int
    scheduled_time: datetime
    cancellation_time: datetime
    service_price: Decimal
    client_id: int
    professional_id: int
    salon_id: Optional[int] = None

    @property
    def advance_notice_hours(self) -> float:
        """Calculate advance notice in hours."""
        delta = self.scheduled_time - self.cancellation_time
        return delta.total_seconds() / 3600

    @property
    def advance_notice_timedelta(self) -> timedelta:
        """Get advance notice as timedelta."""
        return self.scheduled_time - self.cancellation_time


@dataclass
class CancellationEvaluation:
    """Result of cancellation policy evaluation."""

    result: CancellationResult
    applicable_tier: Optional["CancellationTier"]
    fee_amount: Decimal
    refund_amount: Decimal
    message: str
    policy_used: Optional["CancellationPolicy"]

    @property
    def is_allowed(self) -> bool:
        """Check if cancellation is allowed."""
        return self.result != CancellationResult.NOT_ALLOWED

    @property
    def has_fee(self) -> bool:
        """Check if cancellation has a fee."""
        return self.fee_amount > 0


@dataclass
class CancellationTier:
    """Domain representation of a cancellation tier."""

    id: int
    name: str
    advance_notice_hours: int
    fee_type: str  # 'percentage' or 'fixed'
    fee_value: Decimal
    allows_refund: bool
    display_order: int

    def calculate_fee(self, service_price: Decimal) -> Decimal:
        """Calculate cancellation fee for given service price."""
        if self.fee_type == "percentage":
            return service_price * (self.fee_value / 100)
        elif self.fee_type == "fixed":
            return self.fee_value
        else:
            raise ValueError(f"Invalid fee type: {self.fee_type}")

    def applies_to_advance_notice(self, advance_notice_hours: float) -> bool:
        """Check if this tier applies to the given advance notice."""
        return advance_notice_hours >= self.advance_notice_hours

    @classmethod
    def from_model(cls, model: CancellationTierModel) -> "CancellationTier":
        """Create domain object from database model."""
        return cls(
            id=model.id,
            name=model.name,
            advance_notice_hours=model.advance_notice_hours,
            fee_type=model.fee_type,
            fee_value=Decimal(str(model.fee_value)),
            allows_refund=model.allows_refund,
            display_order=model.display_order,
        )


@dataclass
class CancellationPolicy:
    """Domain representation of a cancellation policy."""

    id: int
    name: str
    description: Optional[str]
    salon_id: Optional[int]
    is_default: bool
    effective_from: datetime
    effective_until: Optional[datetime]
    tiers: List[CancellationTier]

    def is_effective_at(self, check_time: datetime) -> bool:
        """Check if policy is effective at given time."""
        if check_time < self.effective_from:
            return False
        if self.effective_until and check_time > self.effective_until:
            return False
        return True

    def find_applicable_tier(self, advance_notice_hours: float) -> Optional[CancellationTier]:
        """Find the tier that applies to given advance notice."""
        # Tiers are ordered by advance_notice_hours DESC
        # Find the first tier that applies (highest advance notice requirement met)
        for tier in self.tiers:
            if tier.applies_to_advance_notice(advance_notice_hours):
                return tier
        return None

    def evaluate_cancellation(self, context: CancellationContext) -> CancellationEvaluation:
        """Evaluate cancellation request against this policy."""
        if not self.is_effective_at(context.cancellation_time):
            return CancellationEvaluation(
                result=CancellationResult.NOT_ALLOWED,
                applicable_tier=None,
                fee_amount=Decimal("0"),
                refund_amount=Decimal("0"),
                message="Policy not effective at cancellation time",
                policy_used=self,
            )

        applicable_tier = self.find_applicable_tier(context.advance_notice_hours)

        if not applicable_tier:
            # No tier found - cancellation not allowed
            return CancellationEvaluation(
                result=CancellationResult.NOT_ALLOWED,
                applicable_tier=None,
                fee_amount=Decimal("0"),
                refund_amount=Decimal("0"),
                message="Insufficient advance notice for cancellation",
                policy_used=self,
            )

        if not applicable_tier.allows_refund:
            return CancellationEvaluation(
                result=CancellationResult.NOT_ALLOWED,
                applicable_tier=applicable_tier,
                fee_amount=Decimal("0"),
                refund_amount=Decimal("0"),
                message=f"Refund not allowed for tier '{applicable_tier.name}'",
                policy_used=self,
            )

        # Calculate fee and refund
        fee_amount = applicable_tier.calculate_fee(context.service_price)
        refund_amount = context.service_price - fee_amount

        result = (
            CancellationResult.ALLOWED_NO_FEE if fee_amount == 0
            else CancellationResult.ALLOWED_WITH_FEE
        )

        return CancellationEvaluation(
            result=result,
            applicable_tier=applicable_tier,
            fee_amount=fee_amount,
            refund_amount=refund_amount,
            message=f"Cancellation allowed under tier '{applicable_tier.name}'",
            policy_used=self,
        )

    @classmethod
    def from_model(cls, model: CancellationPolicyModel) -> "CancellationPolicy":
        """Create domain object from database model."""
        tiers = [CancellationTier.from_model(tier) for tier in model.tiers]

        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            salon_id=model.salon_id,
            is_default=model.is_default,
            effective_from=model.effective_from,
            effective_until=model.effective_until,
            tiers=tiers,
        )


class CancellationPolicyService:
    """Service for managing cancellation policies."""

    def __init__(self, db_session):
        """Initialize service with database session."""
        self.db_session = db_session

    async def get_applicable_policy(
        self,
        salon_id: Optional[int] = None,
        evaluation_time: Optional[datetime] = None
    ) -> Optional[CancellationPolicy]:
        """
        Get the applicable cancellation policy for a salon.

        Args:
            salon_id: Salon ID to find policy for
            evaluation_time: Time to evaluate policy effectiveness

        Returns:
            Applicable cancellation policy or None
        """
        if evaluation_time is None:
            evaluation_time = datetime.utcnow()

        # Try to find salon-specific active policy first
        if salon_id:
            salon_policy = await self._find_policy(
                salon_id=salon_id,
                evaluation_time=evaluation_time
            )
            if salon_policy:
                return salon_policy

        # Fall back to default policy
        default_policy = await self._find_policy(
            salon_id=None,
            evaluation_time=evaluation_time,
            is_default=True
        )

        return default_policy

    async def _find_policy(
        self,
        salon_id: Optional[int] = None,
        evaluation_time: Optional[datetime] = None,
        is_default: bool = False
    ) -> Optional[CancellationPolicy]:
        """Find policy based on criteria."""
        from sqlalchemy import and_, or_
        from backend.app.db.models.cancellation_policy import (
            CancellationPolicyStatus,
        )

        query = self.db_session.query(CancellationPolicyModel).filter(
            CancellationPolicyModel.status == CancellationPolicyStatus.ACTIVE,
            CancellationPolicyModel.effective_from <= evaluation_time,
            or_(
                CancellationPolicyModel.effective_until.is_(None),
                CancellationPolicyModel.effective_until > evaluation_time
            )
        )

        if salon_id is not None:
            query = query.filter(CancellationPolicyModel.salon_id == salon_id)
        else:
            query = query.filter(CancellationPolicyModel.salon_id.is_(None))

        if is_default:
            query = query.filter(CancellationPolicyModel.is_default == True)

        model = query.first()

        if model:
            return CancellationPolicy.from_model(model)

        return None

    async def evaluate_cancellation(
        self,
        context: CancellationContext
    ) -> CancellationEvaluation:
        """
        Evaluate a cancellation request.

        Args:
            context: Cancellation context with booking details

        Returns:
            Evaluation result with fee calculation
        """
        try:
            policy = await self.get_applicable_policy(
                salon_id=context.salon_id,
                evaluation_time=context.cancellation_time
            )

            if not policy:
                logger.warning(
                    f"No cancellation policy found for salon_id={context.salon_id}"
                )
                return CancellationEvaluation(
                    result=CancellationResult.NOT_ALLOWED,
                    applicable_tier=None,
                    fee_amount=Decimal("0"),
                    refund_amount=Decimal("0"),
                    message="No cancellation policy available",
                    policy_used=None,
                )

            evaluation = policy.evaluate_cancellation(context)

            logger.info(
                f"Cancellation evaluation for booking {context.booking_id}: "
                f"result={evaluation.result}, fee={evaluation.fee_amount}, "
                f"refund={evaluation.refund_amount}"
            )

            return evaluation

        except Exception as e:
            logger.error(
                f"Error evaluating cancellation for booking {context.booking_id}: {e}"
            )
            return CancellationEvaluation(
                result=CancellationResult.NOT_ALLOWED,
                applicable_tier=None,
                fee_amount=Decimal("0"),
                refund_amount=Decimal("0"),
                message=f"Error evaluating cancellation: {str(e)}",
                policy_used=None,
            )

    async def create_policy(
        self,
        name: str,
        description: Optional[str] = None,
        salon_id: Optional[int] = None,
        is_default: bool = False,
        effective_from: Optional[datetime] = None,
        effective_until: Optional[datetime] = None,
    ) -> CancellationPolicy:
        """Create a new cancellation policy."""
        if effective_from is None:
            effective_from = datetime.utcnow()

        policy_model = CancellationPolicyModel(
            name=name,
            description=description,
            salon_id=salon_id,
            is_default=is_default,
            effective_from=effective_from,
            effective_until=effective_until,
        )

        self.db_session.add(policy_model)
        await self.db_session.flush()

        return CancellationPolicy.from_model(policy_model)

    async def add_tier_to_policy(
        self,
        policy_id: int,
        name: str,
        advance_notice_hours: int,
        fee_type: str,
        fee_value: Decimal,
        allows_refund: bool = True,
        display_order: Optional[int] = None,
    ) -> CancellationTier:
        """Add a tier to an existing policy."""
        if display_order is None:
            # Get max display order and add 1
            max_order = self.db_session.query(
                self.db_session.query(CancellationTierModel.display_order)
                .filter(CancellationTierModel.policy_id == policy_id)
                .scalar()
            ) or 0
            display_order = max_order + 1

        tier_model = CancellationTierModel(
            policy_id=policy_id,
            name=name,
            advance_notice_hours=advance_notice_hours,
            fee_type=fee_type,
            fee_value=float(fee_value),
            allows_refund=allows_refund,
            display_order=display_order,
        )

        self.db_session.add(tier_model)
        await self.db_session.flush()

        return CancellationTier.from_model(tier_model)
