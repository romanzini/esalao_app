"""Comprehensive test suite for waitlist system."""

import pytest
from datetime import datetime, timedelta

from backend.app.db.models.waitlist import Waitlist, WaitlistStatus, WaitlistPriority
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.professional import Professional
from backend.app.db.models.service import Service
from backend.app.db.models.salon import Salon
from backend.app.db.repositories.waitlist import WaitlistRepository
from backend.app.services.waitlist import WaitlistService


class TestWaitlistModel:
    """Test waitlist model functionality."""

    def test_waitlist_creation(self, db_session):
        """Test basic waitlist creation."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            user_type=UserType.CLIENT
        )
        db_session.add(user)

        professional = Professional(
            id=uuid4(),
            name="Test Professional",
            email="prof@example.com"
        )
        db_session.add(professional)

        service = Service(
            id=uuid4(),
            name="Test Service",
            duration_minutes=60,
            price=100.0
        )
        db_session.add(service)

        unit = Unit(
            id=uuid4(),
            name="Test Unit",
            address="Test Address"
        )
        db_session.add(unit)

        db_session.commit()

        waitlist = Waitlist(
            id=uuid4(),
            user_id=user.id,
            professional_id=professional.id,
            service_id=service.id,
            unit_id=unit.id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.NORMAL
        )

        assert waitlist.status == WaitlistStatus.WAITING
        assert waitlist.priority == WaitlistPriority.NORMAL
        assert waitlist.position is None
        assert waitlist.offers_count == 0
        assert waitlist.last_offer_at is None

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

    def test_waitlist_is_active(self, db_session):
        """Test is_active property."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            user_type=UserType.CLIENT
        )
        db_session.add(user)
        db_session.commit()

        waitlist = Waitlist(
            id=uuid4(),
            user_id=user.id,
            professional_id=uuid4(),
            service_id=uuid4(),
            unit_id=uuid4(),
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING
        )

        # Active status
        assert waitlist.is_active is True

        # Inactive statuses
        waitlist.status = WaitlistStatus.ACCEPTED
        assert waitlist.is_active is False

        waitlist.status = WaitlistStatus.EXPIRED
        assert waitlist.is_active is False

        waitlist.status = WaitlistStatus.CANCELLED
        assert waitlist.is_active is False

    def test_waitlist_can_receive_offer(self, db_session):
        """Test can_receive_offer property."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            user_type=UserType.CLIENT
        )
        db_session.add(user)
        db_session.commit()

        waitlist = Waitlist(
            id=uuid4(),
            user_id=user.id,
            professional_id=uuid4(),
            service_id=uuid4(),
            unit_id=uuid4(),
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING
        )

        # Can receive offer when waiting
        assert waitlist.can_receive_offer is True

        # Cannot receive offer when already offered
        waitlist.status = WaitlistStatus.OFFERED
        assert waitlist.can_receive_offer is False

        # Cannot receive offer when accepted
        waitlist.status = WaitlistStatus.ACCEPTED
        assert waitlist.can_receive_offer is False


class TestWaitlistRepository:
    """Test waitlist repository operations."""

    @pytest.fixture
    def sample_data(self, db_session):
        """Create sample data for testing."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            user_type=UserType.CLIENT
        )
        db_session.add(user)

        professional = Professional(
            id=uuid4(),
            name="Test Professional",
            email="prof@example.com"
        )
        db_session.add(professional)

        service = Service(
            id=uuid4(),
            name="Test Service",
            duration_minutes=60,
            price=100.0
        )
        db_session.add(service)

        unit = Unit(
            id=uuid4(),
            name="Test Unit",
            address="Test Address"
        )
        db_session.add(unit)

        db_session.commit()

        return {
            "user": user,
            "professional": professional,
            "service": service,
            "unit": unit
        }

    async def test_create_waitlist(self, db_session, sample_data):
        """Test creating a waitlist entry."""
        repo = WaitlistRepository(db_session)

        waitlist_data = {
            "user_id": sample_data["user"].id,
            "professional_id": sample_data["professional"].id,
            "service_id": sample_data["service"].id,
            "unit_id": sample_data["unit"].id,
            "preferred_date": datetime(2025, 1, 15, 10, 0),
            "status": WaitlistStatus.WAITING,
            "priority": WaitlistPriority.NORMAL
        }

        waitlist = await repo.create(waitlist_data)

        assert waitlist.id is not None
        assert waitlist.user_id == sample_data["user"].id
        assert waitlist.professional_id == sample_data["professional"].id
        assert waitlist.service_id == sample_data["service"].id
        assert waitlist.unit_id == sample_data["unit"].id
        assert waitlist.status == WaitlistStatus.WAITING
        assert waitlist.priority == WaitlistPriority.NORMAL

    async def test_list_for_slot_offering(self, db_session, sample_data):
        """Test listing waitlist entries for slot offering."""
        repo = WaitlistRepository(db_session)

        # Create multiple waitlist entries with different priorities
        waitlist1 = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.HIGH,
            created_at=datetime.utcnow() - timedelta(hours=2)
        )

        waitlist2 = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 14, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.NORMAL,
            created_at=datetime.utcnow() - timedelta(hours=1)
        )

        db_session.add_all([waitlist1, waitlist2])
        db_session.commit()

        # Test slot offering for morning time
        slot_time = datetime(2025, 1, 15, 9, 0)
        results = await repo.list_for_slot_offering(
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            slot_time=slot_time,
            limit=10
        )

        assert len(results) == 2
        # Higher priority should come first
        assert results[0].priority == WaitlistPriority.HIGH

    async def test_update_position(self, db_session, sample_data):
        """Test updating waitlist position."""
        repo = WaitlistRepository(db_session)

        waitlist = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.NORMAL
        )

        db_session.add(waitlist)
        db_session.commit()

        # Update position
        updated_waitlist = await repo.update_position(waitlist.id, 5)

        assert updated_waitlist.position == 5

    async def test_get_statistics(self, db_session, sample_data):
        """Test getting waitlist statistics."""
        repo = WaitlistRepository(db_session)

        # Create waitlist entries with different statuses
        waitlists = [
            Waitlist(
                id=uuid4(),
                user_id=sample_data["user"].id,
                professional_id=sample_data["professional"].id,
                service_id=sample_data["service"].id,
                unit_id=sample_data["unit"].id,
                preferred_date=datetime(2025, 1, 15, 10, 0),
                status=WaitlistStatus.WAITING,
                priority=WaitlistPriority.NORMAL
            ),
            Waitlist(
                id=uuid4(),
                user_id=sample_data["user"].id,
                professional_id=sample_data["professional"].id,
                service_id=sample_data["service"].id,
                unit_id=sample_data["unit"].id,
                preferred_date=datetime(2025, 1, 15, 14, 0),
                status=WaitlistStatus.OFFERED,
                priority=WaitlistPriority.HIGH
            ),
            Waitlist(
                id=uuid4(),
                user_id=sample_data["user"].id,
                professional_id=sample_data["professional"].id,
                service_id=sample_data["service"].id,
                unit_id=sample_data["unit"].id,
                preferred_date=datetime(2025, 1, 15, 16, 0),
                status=WaitlistStatus.ACCEPTED,
                priority=WaitlistPriority.NORMAL
            )
        ]

        db_session.add_all(waitlists)
        db_session.commit()

        stats = await repo.get_statistics(
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id
        )

        assert stats["total_waiting"] == 1
        assert stats["total_offered"] == 1
        assert stats["total_accepted"] == 1
        assert stats["total_entries"] == 3


class TestWaitlistService:
    """Test waitlist service business logic."""

    @pytest.fixture
    def service_dependencies(self, db_session):
        """Setup service dependencies."""
        from backend.app.db.repositories.booking import BookingRepository
        from backend.app.services.slot import SlotService

        waitlist_repo = WaitlistRepository(db_session)
        booking_repo = BookingRepository(db_session)
        slot_service = SlotService(db_session)

        return {
            "waitlist_repo": waitlist_repo,
            "booking_repo": booking_repo,
            "slot_service": slot_service
        }

    @pytest.fixture
    def sample_data(self, db_session):
        """Create sample data for testing."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            user_type=UserType.CLIENT
        )
        db_session.add(user)

        professional = Professional(
            id=uuid4(),
            name="Test Professional",
            email="prof@example.com"
        )
        db_session.add(professional)

        service = Service(
            id=uuid4(),
            name="Test Service",
            duration_minutes=60,
            price=100.0
        )
        db_session.add(service)

        unit = Unit(
            id=uuid4(),
            name="Test Unit",
            address="Test Address"
        )
        db_session.add(unit)

        db_session.commit()

        return {
            "user": user,
            "professional": professional,
            "service": service,
            "unit": unit
        }

    async def test_join_waitlist(self, db_session, service_dependencies, sample_data):
        """Test joining waitlist."""
        waitlist_service = WaitlistService(
            waitlist_repository=service_dependencies["waitlist_repo"],
            booking_repository=service_dependencies["booking_repo"],
            slot_service=service_dependencies["slot_service"]
        )

        request_data = {
            "professional_id": sample_data["professional"].id,
            "service_id": sample_data["service"].id,
            "unit_id": sample_data["unit"].id,
            "preferred_date": datetime(2025, 1, 15, 10, 0),
            "priority": WaitlistPriority.NORMAL,
            "flexible_time": True,
            "time_range_start": datetime(2025, 1, 15, 9, 0).time(),
            "time_range_end": datetime(2025, 1, 15, 17, 0).time(),
            "max_distance_km": 10.0
        }

        waitlist = await waitlist_service.join_waitlist(
            user_id=sample_data["user"].id,
            request_data=request_data
        )

        assert waitlist.user_id == sample_data["user"].id
        assert waitlist.professional_id == sample_data["professional"].id
        assert waitlist.service_id == sample_data["service"].id
        assert waitlist.unit_id == sample_data["unit"].id
        assert waitlist.status == WaitlistStatus.WAITING
        assert waitlist.priority == WaitlistPriority.NORMAL

    async def test_join_waitlist_duplicate_entry(self, db_session, service_dependencies, sample_data):
        """Test joining waitlist with duplicate entry."""
        waitlist_service = WaitlistService(
            waitlist_repository=service_dependencies["waitlist_repo"],
            booking_repository=service_dependencies["booking_repo"],
            slot_service=service_dependencies["slot_service"]
        )

        # Create existing waitlist entry
        existing_waitlist = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.NORMAL
        )

        db_session.add(existing_waitlist)
        db_session.commit()

        request_data = {
            "professional_id": sample_data["professional"].id,
            "service_id": sample_data["service"].id,
            "unit_id": sample_data["unit"].id,
            "preferred_date": datetime(2025, 1, 15, 10, 0),
            "priority": WaitlistPriority.NORMAL
        }

        # Should raise validation error for duplicate entry
        with pytest.raises(ValidationError, match="already on the waitlist"):
            await waitlist_service.join_waitlist(
                user_id=sample_data["user"].id,
                request_data=request_data
            )

    async def test_leave_waitlist(self, db_session, service_dependencies, sample_data):
        """Test leaving waitlist."""
        waitlist_service = WaitlistService(
            waitlist_repository=service_dependencies["waitlist_repo"],
            booking_repository=service_dependencies["booking_repo"],
            slot_service=service_dependencies["slot_service"]
        )

        # Create waitlist entry
        waitlist = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.WAITING,
            priority=WaitlistPriority.NORMAL
        )

        db_session.add(waitlist)
        db_session.commit()

        # Leave waitlist
        result = await waitlist_service.leave_waitlist(
            user_id=sample_data["user"].id,
            waitlist_id=waitlist.id
        )

        assert result is True

        # Verify waitlist is cancelled
        updated_waitlist = await service_dependencies["waitlist_repo"].get_by_id(waitlist.id)
        assert updated_waitlist.status == WaitlistStatus.CANCELLED

    async def test_respond_to_offer_accept(self, db_session, service_dependencies, sample_data):
        """Test responding to offer with acceptance."""
        waitlist_service = WaitlistService(
            waitlist_repository=service_dependencies["waitlist_repo"],
            booking_repository=service_dependencies["booking_repo"],
            slot_service=service_dependencies["slot_service"]
        )

        # Create waitlist entry with offer
        waitlist = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.OFFERED,
            priority=WaitlistPriority.NORMAL,
            offered_slot_time=datetime(2025, 1, 15, 10, 0),
            offer_expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        db_session.add(waitlist)
        db_session.commit()

        # Accept offer
        result = await waitlist_service.respond_to_offer(
            user_id=sample_data["user"].id,
            waitlist_id=waitlist.id,
            accept=True
        )

        assert result["status"] == "accepted"
        assert "booking_id" in result

        # Verify waitlist is accepted
        updated_waitlist = await service_dependencies["waitlist_repo"].get_by_id(waitlist.id)
        assert updated_waitlist.status == WaitlistStatus.ACCEPTED

    async def test_respond_to_offer_decline(self, db_session, service_dependencies, sample_data):
        """Test responding to offer with decline."""
        waitlist_service = WaitlistService(
            waitlist_repository=service_dependencies["waitlist_repo"],
            booking_repository=service_dependencies["booking_repo"],
            slot_service=service_dependencies["slot_service"]
        )

        # Create waitlist entry with offer
        waitlist = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.OFFERED,
            priority=WaitlistPriority.NORMAL,
            offered_slot_time=datetime(2025, 1, 15, 10, 0),
            offer_expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        db_session.add(waitlist)
        db_session.commit()

        # Decline offer
        result = await waitlist_service.respond_to_offer(
            user_id=sample_data["user"].id,
            waitlist_id=waitlist.id,
            accept=False
        )

        assert result["status"] == "declined"

        # Verify waitlist is back to waiting
        updated_waitlist = await service_dependencies["waitlist_repo"].get_by_id(waitlist.id)
        assert updated_waitlist.status == WaitlistStatus.WAITING

    async def test_expire_old_offers(self, db_session, service_dependencies, sample_data):
        """Test expiring old offers."""
        waitlist_service = WaitlistService(
            waitlist_repository=service_dependencies["waitlist_repo"],
            booking_repository=service_dependencies["booking_repo"],
            slot_service=service_dependencies["slot_service"]
        )

        # Create expired offer
        expired_waitlist = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 10, 0),
            status=WaitlistStatus.OFFERED,
            priority=WaitlistPriority.NORMAL,
            offered_slot_time=datetime(2025, 1, 15, 10, 0),
            offer_expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )

        # Create valid offer
        valid_waitlist = Waitlist(
            id=uuid4(),
            user_id=sample_data["user"].id,
            professional_id=sample_data["professional"].id,
            service_id=sample_data["service"].id,
            unit_id=sample_data["unit"].id,
            preferred_date=datetime(2025, 1, 15, 14, 0),
            status=WaitlistStatus.OFFERED,
            priority=WaitlistPriority.NORMAL,
            offered_slot_time=datetime(2025, 1, 15, 14, 0),
            offer_expires_at=datetime.utcnow() + timedelta(hours=24)  # Valid
        )

        db_session.add_all([expired_waitlist, valid_waitlist])
        db_session.commit()

        # Expire old offers
        expired_count = await waitlist_service.expire_old_offers()

        assert expired_count == 1

        # Verify expired offer status
        updated_expired = await service_dependencies["waitlist_repo"].get_by_id(expired_waitlist.id)
        assert updated_expired.status == WaitlistStatus.EXPIRED

        # Verify valid offer unchanged
        updated_valid = await service_dependencies["waitlist_repo"].get_by_id(valid_waitlist.id)
        assert updated_valid.status == WaitlistStatus.OFFERED


if __name__ == "__main__":
    pytest.main([__file__])
