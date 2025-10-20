"""Repository for cancellation policy data access."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.app.db.models.cancellation_policy import (
    CancellationPolicy,
    CancellationTier,
    CancellationPolicyStatus,
)


class CancellationPolicyRepository:
    """Repository for cancellation policy operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_policy(
        self,
        name: str,
        description: Optional[str] = None,
        salon_id: Optional[int] = None,
        is_default: bool = False,
        effective_from: Optional[datetime] = None,
        effective_until: Optional[datetime] = None,
        status: CancellationPolicyStatus = CancellationPolicyStatus.DRAFT,
    ) -> CancellationPolicy:
        """Create a new cancellation policy."""
        if effective_from is None:
            effective_from = datetime.utcnow()

        policy = CancellationPolicy(
            name=name,
            description=description,
            salon_id=salon_id,
            is_default=is_default,
            effective_from=effective_from,
            effective_until=effective_until,
            status=status,
        )

        self.db.add(policy)
        self.db.flush()
        self.db.refresh(policy)
        return policy

    def get_by_id(self, policy_id: int) -> Optional[CancellationPolicy]:
        """Get policy by ID."""
        return (
            self.db.query(CancellationPolicy)
            .filter(CancellationPolicy.id == policy_id)
            .first()
        )

    def get_active_policies(
        self,
        salon_id: Optional[int] = None,
        evaluation_time: Optional[datetime] = None,
    ) -> List[CancellationPolicy]:
        """Get active policies for a salon."""
        if evaluation_time is None:
            evaluation_time = datetime.utcnow()

        query = self.db.query(CancellationPolicy).filter(
            CancellationPolicy.status == CancellationPolicyStatus.ACTIVE,
            CancellationPolicy.effective_from <= evaluation_time,
            or_(
                CancellationPolicy.effective_until.is_(None),
                CancellationPolicy.effective_until > evaluation_time,
            ),
        )

        if salon_id is not None:
            query = query.filter(CancellationPolicy.salon_id == salon_id)

        return query.all()

    def get_default_policy(
        self, evaluation_time: Optional[datetime] = None
    ) -> Optional[CancellationPolicy]:
        """Get the default cancellation policy."""
        if evaluation_time is None:
            evaluation_time = datetime.utcnow()

        return (
            self.db.query(CancellationPolicy)
            .filter(
                CancellationPolicy.status == CancellationPolicyStatus.ACTIVE,
                CancellationPolicy.is_default == True,
                CancellationPolicy.salon_id.is_(None),
                CancellationPolicy.effective_from <= evaluation_time,
                or_(
                    CancellationPolicy.effective_until.is_(None),
                    CancellationPolicy.effective_until > evaluation_time,
                ),
            )
            .first()
        )

    def get_salon_policy(
        self, salon_id: int, evaluation_time: Optional[datetime] = None
    ) -> Optional[CancellationPolicy]:
        """Get active policy for a specific salon."""
        if evaluation_time is None:
            evaluation_time = datetime.utcnow()

        return (
            self.db.query(CancellationPolicy)
            .filter(
                CancellationPolicy.status == CancellationPolicyStatus.ACTIVE,
                CancellationPolicy.salon_id == salon_id,
                CancellationPolicy.effective_from <= evaluation_time,
                or_(
                    CancellationPolicy.effective_until.is_(None),
                    CancellationPolicy.effective_until > evaluation_time,
                ),
            )
            .first()
        )

    def update_policy(
        self, policy_id: int, **updates
    ) -> Optional[CancellationPolicy]:
        """Update a cancellation policy."""
        policy = self.get_by_id(policy_id)
        if not policy:
            return None

        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)

        self.db.flush()
        self.db.refresh(policy)
        return policy

    def delete_policy(self, policy_id: int) -> bool:
        """Delete a cancellation policy."""
        policy = self.get_by_id(policy_id)
        if not policy:
            return False

        self.db.delete(policy)
        self.db.flush()
        return True

    def list_policies(
        self,
        salon_id: Optional[int] = None,
        status: Optional[CancellationPolicyStatus] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[CancellationPolicy]:
        """List policies with optional filters."""
        query = self.db.query(CancellationPolicy)

        if salon_id is not None:
            query = query.filter(CancellationPolicy.salon_id == salon_id)

        if status is not None:
            query = query.filter(CancellationPolicy.status == status)

        return query.offset(offset).limit(limit).all()


class CancellationTierRepository:
    """Repository for cancellation tier operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_tier(
        self,
        policy_id: int,
        name: str,
        advance_notice_hours: int,
        fee_type: str,
        fee_value: float,
        allows_refund: bool = True,
        display_order: Optional[int] = None,
    ) -> CancellationTier:
        """Create a new cancellation tier."""
        if display_order is None:
            # Get max display order for policy and add 1
            max_order = (
                self.db.query(self.db.func.max(CancellationTier.display_order))
                .filter(CancellationTier.policy_id == policy_id)
                .scalar()
            ) or 0
            display_order = max_order + 1

        tier = CancellationTier(
            policy_id=policy_id,
            name=name,
            advance_notice_hours=advance_notice_hours,
            fee_type=fee_type,
            fee_value=fee_value,
            allows_refund=allows_refund,
            display_order=display_order,
        )

        self.db.add(tier)
        self.db.flush()
        self.db.refresh(tier)
        return tier

    def get_by_id(self, tier_id: int) -> Optional[CancellationTier]:
        """Get tier by ID."""
        return (
            self.db.query(CancellationTier)
            .filter(CancellationTier.id == tier_id)
            .first()
        )

    def get_policy_tiers(self, policy_id: int) -> List[CancellationTier]:
        """Get all tiers for a policy, ordered by advance notice hours desc."""
        return (
            self.db.query(CancellationTier)
            .filter(CancellationTier.policy_id == policy_id)
            .order_by(CancellationTier.advance_notice_hours.desc())
            .all()
        )

    def update_tier(self, tier_id: int, **updates) -> Optional[CancellationTier]:
        """Update a cancellation tier."""
        tier = self.get_by_id(tier_id)
        if not tier:
            return None

        for key, value in updates.items():
            if hasattr(tier, key):
                setattr(tier, key, value)

        self.db.flush()
        self.db.refresh(tier)
        return tier

    def delete_tier(self, tier_id: int) -> bool:
        """Delete a cancellation tier."""
        tier = self.get_by_id(tier_id)
        if not tier:
            return False

        self.db.delete(tier)
        self.db.flush()
        return True

    def reorder_tiers(self, tier_orders: dict[int, int]) -> bool:
        """Reorder tiers by updating display_order."""
        try:
            for tier_id, new_order in tier_orders.items():
                tier = self.get_by_id(tier_id)
                if tier:
                    tier.display_order = new_order

            self.db.flush()
            return True
        except Exception:
            return False
