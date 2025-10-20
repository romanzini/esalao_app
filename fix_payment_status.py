#!/usr/bin/env python3
"""
Script to fix PaymentStatus enum comparisons in metrics service
"""

import os
import re

def fix_file(filepath):
    """Fix PaymentStatus enum comparisons to string comparisons"""
    print(f"Fixing {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace enum comparisons with string comparisons
    replacements = [
        ('p.status == PaymentStatus.SUCCEEDED', 'p.status == "succeeded"'),
        ('p.status == PaymentStatus.FAILED', 'p.status == "failed"'),
        ('p.status == PaymentStatus.PENDING', 'p.status == "pending"'),
        ('payment.status == PaymentStatus.SUCCEEDED', 'payment.status == "succeeded"'),
    ]

    updated_content = content
    for old, new in replacements:
        updated_content = updated_content.replace(old, new)

    # Check if any changes were made
    if content != updated_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"  Updated {filepath}")
        return True
    else:
        print(f"  No changes needed in {filepath}")
        return False

if __name__ == "__main__":
    # Fix the metrics service
    metrics_file = "backend/app/domain/payments/services/metrics_service.py"
    fix_file(metrics_file)

    print("Done!")
