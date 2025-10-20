"""
Seed data for cancellation policies.

Creates default cancellation policies that can be used across the platform.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from backend.app.db.models.cancellation_policy import (
    CancellationPolicy,
    CancellationTier,
    CancellationPolicyStatus,
)


def create_default_cancellation_policy(db: Session) -> CancellationPolicy:
    """Create the default platform-wide cancellation policy."""

    # Check if default policy already exists
    existing = (
        db.query(CancellationPolicy)
        .filter(
            CancellationPolicy.is_default == True,
            CancellationPolicy.salon_id.is_(None),
        )
        .first()
    )

    if existing:
        print(f"Default cancellation policy already exists: {existing.name}")
        return existing

    # Create default policy
    policy = CancellationPolicy(
        name="Default Platform Policy",
        description="Standard cancellation policy for all salons",
        salon_id=None,
        is_default=True,
        status=CancellationPolicyStatus.ACTIVE,
        effective_from=datetime.utcnow(),
        effective_until=None,
    )

    db.add(policy)
    db.flush()

    # Create tiers for the policy
    tiers = [
        {
            "name": "Early Bird (72h+)",
            "advance_notice_hours": 72,
            "fee_type": "percentage",
            "fee_value": 0,
            "allows_refund": True,
            "display_order": 1,
        },
        {
            "name": "Standard (24-72h)",
            "advance_notice_hours": 24,
            "fee_type": "percentage",
            "fee_value": 15,
            "allows_refund": True,
            "display_order": 2,
        },
        {
            "name": "Short Notice (4-24h)",
            "advance_notice_hours": 4,
            "fee_type": "percentage",
            "fee_value": 35,
            "allows_refund": True,
            "display_order": 3,
        },
        {
            "name": "Last Minute (2-4h)",
            "advance_notice_hours": 2,
            "fee_type": "percentage",
            "fee_value": 50,
            "allows_refund": True,
            "display_order": 4,
        },
    ]

    for tier_data in tiers:
        tier = CancellationTier(
            policy_id=policy.id,
            **tier_data
        )
        db.add(tier)

    db.commit()

    print(f"Created default cancellation policy: {policy.name} with {len(tiers)} tiers")
    return policy


def create_strict_cancellation_policy(db: Session) -> CancellationPolicy:
    """Create a strict cancellation policy for premium services."""

    policy = CancellationPolicy(
        name="Strict Premium Policy",
        description="Strict cancellation policy for premium/high-value services",
        salon_id=None,
        is_default=False,
        status=CancellationPolicyStatus.ACTIVE,
        effective_from=datetime.utcnow(),
        effective_until=None,
    )

    db.add(policy)
    db.flush()

    # Create strict tiers
    tiers = [
        {
            "name": "Early Bird (96h+)",
            "advance_notice_hours": 96,
            "fee_type": "percentage",
            "fee_value": 0,
            "allows_refund": True,
            "display_order": 1,
        },
        {
            "name": "Standard (48-96h)",
            "advance_notice_hours": 48,
            "fee_type": "percentage",
            "fee_value": 25,
            "allows_refund": True,
            "display_order": 2,
        },
        {
            "name": "Short Notice (24-48h)",
            "advance_notice_hours": 24,
            "fee_type": "percentage",
            "fee_value": 50,
            "allows_refund": True,
            "display_order": 3,
        },
        {
            "name": "Last Minute (12-24h)",
            "advance_notice_hours": 12,
            "fee_type": "percentage",
            "fee_value": 75,
            "allows_refund": True,
            "display_order": 4,
        },
        {
            "name": "Same Day (<12h)",
            "advance_notice_hours": 1,
            "fee_type": "percentage",
            "fee_value": 100,
            "allows_refund": False,
            "display_order": 5,
        },
    ]

    for tier_data in tiers:
        tier = CancellationTier(
            policy_id=policy.id,
            **tier_data
        )
        db.add(tier)

    db.commit()

    print(f"Created strict cancellation policy: {policy.name} with {len(tiers)} tiers")
    return policy


def create_lenient_cancellation_policy(db: Session) -> CancellationPolicy:
    """Create a lenient cancellation policy for competitive markets."""

    policy = CancellationPolicy(
        name="Lenient Customer-Friendly Policy",
        description="Customer-friendly cancellation policy for competitive markets",
        salon_id=None,
        is_default=False,
        status=CancellationPolicyStatus.ACTIVE,
        effective_from=datetime.utcnow(),
        effective_until=None,
    )

    db.add(policy)
    db.flush()

    # Create lenient tiers
    tiers = [
        {
            "name": "Early Bird (48h+)",
            "advance_notice_hours": 48,
            "fee_type": "percentage",
            "fee_value": 0,
            "allows_refund": True,
            "display_order": 1,
        },
        {
            "name": "Standard (12-48h)",
            "advance_notice_hours": 12,
            "fee_type": "percentage",
            "fee_value": 10,
            "allows_refund": True,
            "display_order": 2,
        },
        {
            "name": "Short Notice (4-12h)",
            "advance_notice_hours": 4,
            "fee_type": "percentage",
            "fee_value": 20,
            "allows_refund": True,
            "display_order": 3,
        },
        {
            "name": "Last Minute (1-4h)",
            "advance_notice_hours": 1,
            "fee_type": "fixed",
            "fee_value": 25.00,  # Fixed R$ 25 fee
            "allows_refund": True,
            "display_order": 4,
        },
    ]

    for tier_data in tiers:
        tier = CancellationTier(
            policy_id=policy.id,
            **tier_data
        )
        db.add(tier)

    db.commit()

    print(f"Created lenient cancellation policy: {policy.name} with {len(tiers)} tiers")
    return policy


def seed_cancellation_policies(db: Session):
    """Seed all default cancellation policies."""
    print("Seeding cancellation policies...")

    try:
        # Create default policies
        default_policy = create_default_cancellation_policy(db)
        strict_policy = create_strict_cancellation_policy(db)
        lenient_policy = create_lenient_cancellation_policy(db)

        print(f"Successfully seeded {3} cancellation policies:")
        print(f"  - {default_policy.name} (Default)")
        print(f"  - {strict_policy.name}")
        print(f"  - {lenient_policy.name}")

        return [default_policy, strict_policy, lenient_policy]

    except Exception as e:
        print(f"Error seeding cancellation policies: {e}")
        db.rollback()
        raise


if __name__ == "__main__":
    from backend.app.db.session import SyncSessionLocal

    with SyncSessionLocal() as db:
        seed_cancellation_policies(db)
