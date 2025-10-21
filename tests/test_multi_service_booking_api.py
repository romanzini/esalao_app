"""Tests for multi-service booking API endpoints."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.app.db.models.multi_service_booking import MultiServiceBookingStatus
from backend.app.db.models.booking import BookingStatus
from backend.app.db.models.user import User


class TestMultiServiceBookingAPI:
    """Test multi-service booking API endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = AsyncMock(spec=User)
        user.id = 1
        user.role = "CLIENT"
        user.professional_profile = None
        return user

    @pytest.fixture
    def mock_professional_user(self):
        """Create mock professional user."""
        user = AsyncMock(spec=User)
        user.id = 2
        user.role = "PROFESSIONAL"
        user.professional_profile = AsyncMock()
        user.professional_profile.id = 1
        return user

    @pytest.fixture
    def mock_admin_user(self):
        """Create mock admin user."""
        user = AsyncMock(spec=User)
        user.id = 3
        user.role = "ADMIN"
        return user

    @pytest.mark.asyncio
    async def test_check_package_availability_success(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test successful package availability check."""
        # Mock service response
        availability_response = {
            "is_available": True,
            "suggested_times": [
                {
                    "service_id": 1,
                    "professional_id": 1,
                    "service_name": "Haircut",
                    "suggested_time": datetime.now() + timedelta(days=1),
                    "duration_minutes": 60,
                    "price": 50.0
                }
            ],
            "total_duration_minutes": 60,
            "total_price": 50.0,
            "conflicts": [],
            "package_start": datetime.now() + timedelta(days=1),
            "package_end": datetime.now() + timedelta(days=1, hours=1)
        }

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.check_package_availability = AsyncMock(return_value=availability_response)

            # Request data
            request_data = {
                "services": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
                    }
                ],
                "max_gap_minutes": 30
            }

            # Execute
            response = await async_client.post(
                "/api/v1/multi-service-bookings/check-availability",
                json=request_data
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["is_available"] is True
            assert len(data["suggested_times"]) == 1

    @pytest.mark.asyncio
    async def test_check_package_availability_conflict(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test package availability check with conflicts."""
        # Mock service response with conflicts
        availability_response = {
            "is_available": False,
            "suggested_times": [],
            "total_duration_minutes": 0,
            "total_price": 0.0,
            "conflicts": ["Service 1 slot not available"],
            "package_start": None,
            "package_end": None
        }

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.check_package_availability = AsyncMock(return_value=availability_response)

            # Request data
            request_data = {
                "services": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
                    }
                ],
                "max_gap_minutes": 30
            }

            # Execute
            response = await async_client.post(
                "/api/v1/multi-service-bookings/check-availability",
                json=request_data
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["is_available"] is False
            assert len(data["conflicts"]) == 1

    @pytest.mark.asyncio
    async def test_create_multi_service_booking_success(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test successful multi-service booking creation."""
        # Mock booking response
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.client_id = 1
        mock_booking.package_name = "Test Package"
        mock_booking.status = MultiServiceBookingStatus.PENDING
        mock_booking.total_price = 75.0
        mock_booking.created_at = datetime.now()

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.create_multi_service_booking = AsyncMock(return_value=mock_booking)
            mock_service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)

            # Request data
            request_data = {
                "package_name": "Test Package",
                "services": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
                    },
                    {
                        "service_id": 2,
                        "professional_id": 1,
                        "scheduled_at": (datetime.now() + timedelta(days=1, hours=1)).isoformat()
                    }
                ],
                "notes": "Test notes"
            }

            # Execute
            response = await async_client.post(
                "/api/v1/multi-service-bookings/",
                json=request_data
            )

            # Verify
            assert response.status_code == 200
            mock_service.create_multi_service_booking.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_multi_service_booking_unavailable(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test multi-service booking creation with unavailable slots."""
        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.create_multi_service_booking = AsyncMock(
                side_effect=ValueError("Package not available: Service not available")
            )

            # Request data
            request_data = {
                "package_name": "Test Package",
                "services": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
                    }
                ]
            }

            # Execute
            response = await async_client.post(
                "/api/v1/multi-service-bookings/",
                json=request_data
            )

            # Verify
            assert response.status_code == 400
            assert "Package not available" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_multi_service_bookings_client(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test listing multi-service bookings as client."""
        # Mock bookings
        mock_bookings = [AsyncMock(), AsyncMock()]
        total_count = 2

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.list_with_pagination = AsyncMock(
                return_value=(mock_bookings, total_count)
            )

            # Execute
            response = await async_client.get("/api/v1/multi-service-bookings/")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert data["page"] == 1

            # Verify client filter was applied
            mock_service.multi_booking_repo.list_with_pagination.assert_called_once()
            call_kwargs = mock_service.multi_booking_repo.list_with_pagination.call_args.kwargs
            assert call_kwargs["client_id"] == mock_user.id

    @pytest.mark.asyncio
    async def test_list_multi_service_bookings_professional(
        self,
        async_client: AsyncClient,
        mock_professional_user
    ):
        """Test listing multi-service bookings as professional."""
        # Mock bookings
        mock_bookings = []
        total_count = 0

        with patch('backend.app.api.deps.get_current_user', return_value=mock_professional_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.list_with_pagination = AsyncMock(
                return_value=(mock_bookings, total_count)
            )

            # Execute
            response = await async_client.get("/api/v1/multi-service-bookings/")

            # Verify
            assert response.status_code == 200

            # Verify professional filter was applied
            call_kwargs = mock_service.multi_booking_repo.list_with_pagination.call_args.kwargs
            assert call_kwargs["professional_id"] == mock_professional_user.professional_profile.id

    @pytest.mark.asyncio
    async def test_get_multi_service_booking_success(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test getting specific multi-service booking."""
        # Mock booking
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.client_id = 1
        mock_booking.individual_bookings = []

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)

            # Execute
            response = await async_client.get("/api/v1/multi-service-bookings/1")

            # Verify
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_multi_service_booking_not_found(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test getting non-existent multi-service booking."""
        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.get_by_id = AsyncMock(return_value=None)

            # Execute
            response = await async_client.get("/api/v1/multi-service-bookings/999")

            # Verify
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_multi_service_booking_unauthorized(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test getting multi-service booking without authorization."""
        # Mock booking belonging to different user
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.client_id = 999  # Different user
        mock_booking.individual_bookings = []

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)

            # Execute
            response = await async_client.get("/api/v1/multi-service-bookings/1")

            # Verify
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_confirm_multi_service_booking_success(
        self,
        async_client: AsyncClient,
        mock_professional_user
    ):
        """Test confirming multi-service booking as professional."""
        # Mock booking
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.individual_bookings = [
            AsyncMock(professional_id=1)  # Professional involved
        ]

        mock_confirmed_booking = AsyncMock()

        with patch('backend.app.api.deps.get_current_user', return_value=mock_professional_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)
            mock_service.confirm_multi_service_booking = AsyncMock(return_value=mock_confirmed_booking)

            # Execute
            response = await async_client.post("/api/v1/multi-service-bookings/1/confirm")

            # Verify
            assert response.status_code == 200
            mock_service.confirm_multi_service_booking.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_confirm_multi_service_booking_client_forbidden(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test that clients cannot confirm bookings."""
        with patch('backend.app.api.deps.get_current_user', return_value=mock_user):
            # Execute
            response = await async_client.post("/api/v1/multi-service-bookings/1/confirm")

            # Verify
            assert response.status_code == 403
            assert "Clients cannot confirm bookings" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_multi_service_booking_success(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test cancelling multi-service booking."""
        # Mock booking
        mock_booking = AsyncMock()
        mock_booking.id = 1
        mock_booking.client_id = 1
        mock_booking.individual_bookings = []

        mock_cancelled_booking = AsyncMock()

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.get_by_id = AsyncMock(return_value=mock_booking)
            mock_service.cancel_multi_service_booking = AsyncMock(return_value=mock_cancelled_booking)

            # Execute
            response = await async_client.post(
                "/api/v1/multi-service-bookings/1/cancel",
                params={
                    "cancellation_reason": "User request",
                    "partial_cancel": False
                }
            )

            # Verify
            assert response.status_code == 200
            mock_service.cancel_multi_service_booking.assert_called_once_with(
                1, "User request", mock_user.id, False
            )

    @pytest.mark.asyncio
    async def test_get_package_suggestions(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test getting package suggestions."""
        # Mock suggestions
        mock_suggestions = [
            {
                "name": "Hair Package",
                "description": "Complete hair treatment",
                "estimated_duration": 120,
                "estimated_price": 150.0,
                "popularity_score": 95,
                "services": ["Haircut", "Hair Wash"]
            }
        ]

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.get_package_suggestions = AsyncMock(return_value=mock_suggestions)

            # Execute
            response = await async_client.get(
                "/api/v1/multi-service-bookings/packages/suggestions",
                params={"duration_preference": "medium"}
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Hair Package"

    @pytest.mark.asyncio
    async def test_calculate_package_pricing(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test calculating package pricing."""
        # Mock pricing calculation
        pricing_result = {
            "total_individual_price": 100.0,
            "discount_percentage": 10.0,
            "discount_amount": 10.0,
            "package_price": 90.0,
            "savings": 10.0,
            "service_details": []
        }

        with patch('backend.app.api.deps.get_current_user', return_value=mock_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.calculate_package_discount = AsyncMock(return_value=pricing_result)

            # Request data
            request_data = {
                "services": [
                    {
                        "service_id": 1,
                        "professional_id": 1,
                        "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat()
                    }
                ]
            }

            # Execute
            response = await async_client.post(
                "/api/v1/multi-service-bookings/pricing/calculate",
                json=request_data,
                params={"discount_percentage": 10.0}
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["total_individual_price"] == 100.0
            assert data["package_price"] == 90.0
            assert data["savings"] == 10.0

    @pytest.mark.asyncio
    async def test_get_multi_service_stats_admin(
        self,
        async_client: AsyncClient,
        mock_admin_user
    ):
        """Test getting multi-service statistics as admin."""
        # Mock stats
        mock_stats = {
            "total_bookings": 100,
            "confirmed_bookings": 80,
            "cancelled_bookings": 15,
            "completed_bookings": 70,
            "total_revenue": 15000.0,
            "average_booking_value": 150.0,
            "average_services_count": 2.5
        }

        with patch('backend.app.api.deps.get_current_admin_user', return_value=mock_admin_user), \
             patch('backend.app.services.multi_service_booking.MultiServiceBookingService') as MockService:

            mock_service = MockService.return_value
            mock_service.multi_booking_repo.get_booking_statistics = AsyncMock(return_value=mock_stats)

            # Execute
            response = await async_client.get("/api/v1/multi-service-bookings/admin/stats")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["total_packages"] == 100
            assert data["total_revenue"] == 15000.0
            assert data["average_services_per_package"] == 2.5
