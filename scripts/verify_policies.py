#!/usr/bin/env python3
"""
Verificação das políticas de cancelamento criadas
"""
import sys
import os

# Add backend path to sys.path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from app.db.database import get_db
from app.db.models.cancellation_policy import CancellationPolicy, CancellationTier

def main():
    """Verificar políticas criadas"""
    db = next(get_db())

    try:
        # Query policies
        policies = db.query(CancellationPolicy).all()
        print('Cancellation Policies Created:')
        print('=' * 50)

        for policy in policies:
            tier_count = len(policy.tiers)
            default_flag = '(DEFAULT)' if policy.is_default else ''
            print(f'• {policy.name} {default_flag}')
            print(f'  - {tier_count} tiers configured')
            print(f'  - Status: {policy.status}')

            # Show tier details
            for tier in sorted(policy.tiers, key=lambda t: t.display_order):
                fee_display = f"{tier.fee_value}%" if tier.fee_type == 'percentage' else f"R$ {tier.fee_value:.2f}"
                refund_status = "✓" if tier.allows_refund else "✗"
                print(f'    {tier.display_order}. {tier.name} ({tier.advance_notice_hours}h) - Fee: {fee_display} - Refund: {refund_status}')
            print()

        print(f'Total: {len(policies)} policies created successfully!')

    finally:
        db.close()

if __name__ == "__main__":
    main()
