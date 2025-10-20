"""Simplified test suite for waitlist system."""

import pytest
from datetime import datetime, timedelta

from backend.app.db.models.waitlist import Waitlist, WaitlistStatus, WaitlistPriority


class TestWaitlistModel:
    """Test waitlist model functionality."""

    def test_waitlist_enums(self):
        """Test waitlist enum values."""
        # Test WaitlistStatus
        assert WaitlistStatus.WAITING == "waiting"
        assert WaitlistStatus.OFFERED == "offered"
        assert WaitlistStatus.ACCEPTED == "accepted"
        assert WaitlistStatus.EXPIRED == "expired"
        assert WaitlistStatus.CANCELLED == "cancelled"

        # Test WaitlistPriority
        assert WaitlistPriority.LOW == "low"
        assert WaitlistPriority.NORMAL == "normal"
        assert WaitlistPriority.HIGH == "high"
        assert WaitlistPriority.URGENT == "urgent"

    def test_waitlist_model_creation(self):
        """Test basic waitlist model creation without database."""
        # Test that the model can be instantiated
        waitlist = Waitlist(
            client_id=1,
            professional_id=1,
            service_id=1,
            unit_id=1,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.NORMAL
        )

        assert waitlist.status == WaitlistStatus.WAITING
        assert waitlist.priority == WaitlistPriority.NORMAL
        assert waitlist.client_id == 1
        assert waitlist.professional_id == 1
        assert waitlist.service_id == 1
        assert waitlist.unit_id == 1

    def test_waitlist_properties(self):
        """Test waitlist property methods."""
        waitlist = Waitlist(
            client_id=1,
            professional_id=1,
            service_id=1,
            unit_id=1,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.NORMAL
        )

        # Test is_active for waiting status
        assert waitlist.is_active is True

        # Test can_receive_offer for waiting status
        assert waitlist.can_receive_offer is True

        # Test inactive status
        waitlist.status = WaitlistStatus.ACCEPTED
        assert waitlist.is_active is False

        # Test cannot receive offer when already offered
        waitlist.status = WaitlistStatus.OFFERED
        assert waitlist.can_receive_offer is False


if __name__ == "__main__":
    pytest.main([__file__])
