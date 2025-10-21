"""Tests for overbooking system."""

import pytest
from datetime import datetime, time, timedelta
from uuid import uuid4

from backend.app.db.models.overbooking import OverbookingConfig, OverbookingScope, OverbookingTimeframe
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.salon import Salon
from backend.app.db.models.professional import Professional
from backend.app.db.models.service import Service


class TestOverbookingModel:
    """Test overbooking model functionality."""

    def test_overbooking_config_creation(self):
        """Test creating overbooking configuration."""
        config = OverbookingConfig(
            name="Test Overbooking Config",
            description="Test configuration for overbooking",
            scope=OverbookingScope.SALON,
            max_overbooking_percentage=15.0,
            timeframe=OverbookingTimeframe.HOURLY,
            min_historical_bookings=20,
            historical_period_days=30,
            min_no_show_rate=8.0,
            max_no_show_rate=40.0,
            is_active=True
        )

        assert config.name == "Test Overbooking Config"
        assert config.scope == OverbookingScope.SALON
        assert config.max_overbooking_percentage == 15.0
        assert config.is_active is True

    def test_overbooking_scope_enum(self):
        """Test overbooking scope enumeration."""
        assert OverbookingScope.GLOBAL == "global"
        assert OverbookingScope.SALON == "salon"
        assert OverbookingScope.PROFESSIONAL == "professional"
        assert OverbookingScope.SERVICE == "service"

    def test_overbooking_timeframe_enum(self):
        """Test overbooking timeframe enumeration."""
        assert OverbookingTimeframe.HOURLY == "hourly"
        assert OverbookingTimeframe.DAILY == "daily"
        assert OverbookingTimeframe.WEEKLY == "weekly"

    def test_is_currently_effective(self):
        """Test if configuration is currently effective."""
        # Active config without date restrictions
        config = OverbookingConfig(
            name="Test Config",
            scope=OverbookingScope.GLOBAL,
            max_overbooking_percentage=15.0,
            is_active=True
        )
        assert config.is_currently_effective is True

        # Inactive config
        config.is_active = False
        assert config.is_currently_effective is False

        # Config with future effective_from
        config.is_active = True
        config.effective_from = datetime.utcnow() + timedelta(days=1)
        assert config.is_currently_effective is False

        # Config with past effective_until
        config.effective_from = None
        config.effective_until = datetime.utcnow() - timedelta(days=1)
        assert config.is_currently_effective is False

    def test_max_overbooking_decimal(self):
        """Test conversion of percentage to decimal."""
        config = OverbookingConfig(
            name="Test Config",
            scope=OverbookingScope.GLOBAL,
            max_overbooking_percentage=20.0
        )
        assert config.max_overbooking_decimal == 0.20

    def test_applies_to_time(self):
        """Test time-based application of config."""
        config = OverbookingConfig(
            name="Test Config",
            scope=OverbookingScope.GLOBAL,
            max_overbooking_percentage=15.0,
            start_time=time(9, 0),
            end_time=time(17, 0)
        )

        # Within time range
        assert config.applies_to_time(time(10, 0)) is True
        assert config.applies_to_time(time(9, 0)) is True
        assert config.applies_to_time(time(17, 0)) is True

        # Outside time range
        assert config.applies_to_time(time(8, 0)) is False
        assert config.applies_to_time(time(18, 0)) is False

        # No time restrictions
        config.start_time = None
        config.end_time = None
        assert config.applies_to_time(time(2, 0)) is True

    def test_calculate_max_capacity(self):
        """Test maximum capacity calculation."""
        config = OverbookingConfig(
            name="Test Config",
            scope=OverbookingScope.GLOBAL,
            max_overbooking_percentage=25.0,
            is_active=True
        )

        # Base capacity: 4, 25% overbooking = 1 additional slot
        assert config.calculate_max_capacity(4) == 5

        # Base capacity: 10, 25% overbooking = 2 additional slots
        assert config.calculate_max_capacity(10) == 12

        # Inactive config should return base capacity
        config.is_active = False
        assert config.calculate_max_capacity(4) == 4
