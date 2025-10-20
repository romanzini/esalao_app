"""
Cancellation policies domain module.

This module implements the cancellation policy system that defines
rules for booking cancellations based on advance notice periods.
"""

from .cancellation import (
    CancellationPolicy,
    CancellationTier,
    CancellationPolicyService,
    CancellationResult,
    CancellationContext,
)
from .booking_cancellation import BookingCancellationService

__all__ = [
    "CancellationPolicy",
    "CancellationTier",
    "CancellationPolicyService",
    "CancellationResult",
    "CancellationContext",
    "BookingCancellationService",
]
