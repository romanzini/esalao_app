"""
Tests for no-show detection workflow and jobs.

Tests the automated no-show detection system and manual job execution.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.booking import BookingStatus
from backend.app.jobs.no_show_detection import NoShowDetectionJob


class TestNoShowWorkflow:
    """Test suite for no-show detection workflow."""

    @pytest.fixture
    async def sample_booking_past_due(self, client: AsyncClient, admin_headers):
        """Create a booking that is past due for no-show detection."""
        booking_data = {
            "professional_id": 1,
            "service_id": 1,
            "scheduled_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
            "notes": "Past due booking for no-show test"
        }

        response = await client.post(
            "/v1/bookings",
            json=booking_data,
            headers=admin_headers
        )

        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    async def sample_booking_future(self, client: AsyncClient, admin_headers):
        """Create a future booking that should not trigger no-show."""
        booking_data = {
            "professional_id": 1,
            "service_id": 1,
            "scheduled_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "notes": "Future booking for no-show test"
        }

        response = await client.post(
            "/v1/bookings",
            json=booking_data,
            headers=admin_headers
        )

        assert response.status_code == 201
        return response.json()

    async def test_no_show_detection_job_basic(self, db_session: AsyncSession):
        """Test basic no-show detection job execution."""
        job = NoShowDetectionJob(detection_window_hours=2)

        # Mock the database operations
        with patch.object(job, '_find_eligible_bookings', return_value=[]):
            results = await job.run(db_session=db_session)

        assert "job_start_time" in results
        assert "bookings_evaluated" in results
        assert "no_shows_detected" in results
        assert "notifications_sent" in results
        assert "errors" in results
        assert "processing_time_seconds" in results
        assert results["bookings_evaluated"] == 0

    async def test_manual_no_show_detection_endpoint(self, client: AsyncClient, admin_headers):
        """Test manual execution of no-show detection via API."""
        with patch('backend.app.jobs.no_show_detection.NoShowDetectionJob.run') as mock_run:
            mock_run.return_value = {
                "job_start_time": datetime.utcnow(),
                "bookings_evaluated": 5,
                "no_shows_detected": 2,
                "notifications_sent": 2,
                "errors": [],
                "processing_time_seconds": 1.5
            }

            response = await client.post(
                "/v1/no-show/detect",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data["bookings_evaluated"] == 5
            assert data["no_shows_detected"] == 2
            assert data["triggered_by"] is not None
            assert data["trigger_type"] == "manual"

    async def test_manual_no_show_detection_with_window(self, client: AsyncClient, admin_headers):
        """Test manual no-show detection with custom detection window."""
        with patch('backend.app.jobs.no_show_detection.NoShowDetectionJob.run') as mock_run:
            mock_run.return_value = {
                "job_start_time": datetime.utcnow(),
                "bookings_evaluated": 3,
                "no_shows_detected": 1,
                "notifications_sent": 1,
                "errors": [],
                "processing_time_seconds": 0.8
            }

            response = await client.post(
                "/v1/no-show/detect?detection_window_hours=4",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["bookings_evaluated"] == 3

    async def test_evaluate_specific_bookings(self, client: AsyncClient, admin_headers, sample_booking_past_due):
        """Test evaluation of specific bookings."""
        booking_id = sample_booking_past_due["id"]

        with patch('backend.app.jobs.no_show_detection.NoShowDetectionJob.run_manual') as mock_run:
            mock_run.return_value = {
                "job_start_time": datetime.utcnow(),
                "bookings_evaluated": 1,
                "no_shows_detected": 1,
                "errors": [],
                "booking_results": {
                    booking_id: {
                        "should_mark": True,
                        "reason": "client_no_show",
                        "fee": 25.0
                    }
                }
            }

            response = await client.post(
                f"/v1/no-show/detect/bookings?booking_ids={booking_id}",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data["bookings_evaluated"] == 1
            assert str(booking_id) in data["booking_results"]
            assert data["booking_results"][str(booking_id)]["should_mark"] is True

    async def test_evaluate_specific_bookings_validation(self, client: AsyncClient, admin_headers):
        """Test validation for specific booking evaluation."""
        # Test empty booking list
        response = await client.post(
            "/v1/no-show/detect/bookings",
            headers=admin_headers
        )
        assert response.status_code == 422  # Missing required parameter

        # Test too many bookings
        booking_ids = list(range(1, 102))  # 101 bookings
        query_string = "&".join([f"booking_ids={bid}" for bid in booking_ids])

        response = await client.post(
            f"/v1/no-show/detect/bookings?{query_string}",
            headers=admin_headers
        )
        assert response.status_code == 400

    async def test_get_job_status(self, client: AsyncClient, admin_headers):
        """Test getting no-show job status."""
        response = await client.get(
            "/v1/no-show/job-status",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "system_status" in data
        assert "default_detection_window_hours" in data
        assert "automatic_detection_enabled" in data
        assert "configuration" in data
        assert "checked_at" in data

    async def test_configure_job_schedule(self, client: AsyncClient, admin_headers):
        """Test configuring job schedule."""
        response = await client.post(
            "/v1/no-show/job/schedule?enabled=true&interval_hours=2&detection_window_hours=3",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "configuration" in data
        assert data["configuration"]["automatic_detection_enabled"] is True
        assert data["configuration"]["run_interval_hours"] == 2
        assert data["configuration"]["detection_window_hours"] == 3

    async def test_no_show_detection_access_control(self, client: AsyncClient):
        """Test access control for no-show detection endpoints."""
        # Test without authentication
        response = await client.post("/v1/no-show/detect")
        assert response.status_code == 401

        response = await client.get("/v1/no-show/job-status")
        assert response.status_code == 401

        response = await client.post("/v1/no-show/job/schedule")
        assert response.status_code == 401

    async def test_no_show_job_error_handling(self, client: AsyncClient, admin_headers):
        """Test error handling in no-show detection job."""
        with patch('backend.app.jobs.no_show_detection.NoShowDetectionJob.run') as mock_run:
            mock_run.side_effect = Exception("Database connection failed")

            response = await client.post(
                "/v1/no-show/detect",
                headers=admin_headers
            )

            assert response.status_code == 500
            assert "No-show detection job failed" in response.json()["detail"]

    async def test_find_eligible_bookings_integration(self, db_session: AsyncSession):
        """Test finding eligible bookings for no-show detection."""
        from backend.app.db.repositories.booking import BookingRepository

        booking_repo = BookingRepository(db_session)
        job = NoShowDetectionJob(detection_window_hours=2)

        # Test with current time (should find past due bookings)
        current_time = datetime.utcnow()
        eligible = await job._find_eligible_bookings(booking_repo, current_time)

        # Should return a list (might be empty if no eligible bookings)
        assert isinstance(eligible, list)

    async def test_no_show_job_with_notifications(self, db_session: AsyncSession):
        """Test no-show job with notification sending."""
        job = NoShowDetectionJob(detection_window_hours=1)

        # Mock booking and services
        mock_booking = AsyncMock()
        mock_booking.id = 123
        mock_booking.scheduled_at = datetime.utcnow() - timedelta(hours=2)
        mock_booking.status = BookingStatus.CONFIRMED
        mock_booking.marked_no_show_at = None

        mock_evaluation = AsyncMock()
        mock_evaluation.should_mark_no_show = True
        mock_evaluation.reason = "client_no_show"
        mock_evaluation.calculated_fee = 25.0

        with patch.object(job, '_find_eligible_bookings', return_value=[mock_booking]):
            with patch('backend.app.services.no_show.NoShowService.evaluate_booking_for_no_show', return_value=mock_evaluation):
                with patch('backend.app.services.no_show.NoShowService.mark_booking_no_show'):
                    with patch('backend.app.services.booking_notifications.BookingNotificationService.notify_no_show_detected'):

                        results = await job.run(db_session=db_session)

                        assert results["bookings_evaluated"] == 1
                        assert results["no_shows_detected"] == 1

    async def test_no_show_job_statistics_accuracy(self, db_session: AsyncSession):
        """Test that job statistics are accurately calculated."""
        job = NoShowDetectionJob(detection_window_hours=2)

        # Mock multiple bookings with different outcomes
        mock_bookings = []
        for i in range(3):
            mock_booking = AsyncMock()
            mock_booking.id = i + 1
            mock_booking.scheduled_at = datetime.utcnow() - timedelta(hours=2)
            mock_booking.status = BookingStatus.CONFIRMED
            mock_booking.marked_no_show_at = None
            mock_bookings.append(mock_booking)

        # Mock evaluations: 2 should be marked, 1 should not
        evaluations = [
            AsyncMock(should_mark_no_show=True, reason="client_no_show", calculated_fee=25.0),
            AsyncMock(should_mark_no_show=True, reason="client_late_excessive", calculated_fee=15.0),
            AsyncMock(should_mark_no_show=False, reason=None, calculated_fee=0.0),
        ]

        with patch.object(job, '_find_eligible_bookings', return_value=mock_bookings):
            with patch('backend.app.services.no_show.NoShowService.evaluate_booking_for_no_show', side_effect=evaluations):
                with patch('backend.app.services.no_show.NoShowService.mark_booking_no_show'):
                    with patch('backend.app.services.booking_notifications.BookingNotificationService.notify_no_show_detected'):

                        results = await job.run(db_session=db_session)

                        assert results["bookings_evaluated"] == 3
                        assert results["no_shows_detected"] == 2
                        assert results["notifications_sent"] == 2
                        assert len(results["errors"]) == 0

    async def test_no_show_job_error_resilience(self, db_session: AsyncSession):
        """Test that job continues processing even when individual bookings fail."""
        job = NoShowDetectionJob(detection_window_hours=2)

        # Mock bookings where one will fail
        mock_bookings = []
        for i in range(3):
            mock_booking = AsyncMock()
            mock_booking.id = i + 1
            mock_bookings.append(mock_booking)

        # Mock service that fails for second booking
        def mock_evaluate(booking_id, current_time=None):
            if booking_id == 2:
                raise Exception("Service temporarily unavailable")
            return AsyncMock(should_mark_no_show=True, reason="client_no_show", calculated_fee=25.0)

        with patch.object(job, '_find_eligible_bookings', return_value=mock_bookings):
            with patch('backend.app.services.no_show.NoShowService.evaluate_booking_for_no_show', side_effect=mock_evaluate):
                with patch('backend.app.services.no_show.NoShowService.mark_booking_no_show'):
                    with patch('backend.app.services.booking_notifications.BookingNotificationService.notify_no_show_detected'):

                        results = await job.run(db_session=db_session)

                        assert results["bookings_evaluated"] == 3
                        assert results["no_shows_detected"] == 2  # 2 successful, 1 failed
                        assert len(results["errors"]) == 1
                        assert "booking 2" in results["errors"][0]
