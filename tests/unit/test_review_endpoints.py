"""Integration tests for review API endpoints."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.app.db.models.review import Review, ReviewStatus, ReviewModerationReason
from backend.app.db.models.user import User, UserRole
from backend.app.db.models.booking import Booking, BookingStatus


class TestReviewEndpoints:
    """Test review API endpoints."""

    @pytest.fixture
    def sample_review_data(self):
        """Sample review data for testing."""
        return {
            "booking_id": 1,
            "rating": 5,
            "title": "Great service!",
            "comment": "Very professional and clean.",
            "is_anonymous": False
        }

    @pytest.fixture
    def sample_review_response(self):
        """Sample review response data."""
        return {
            "id": 1,
            "booking_id": 1,
            "client_id": 1,
            "rating": 5,
            "title": "Great service!",
            "comment": "Very professional and clean.",
            "status": "approved",
            "is_anonymous": False,
            "is_verified": True,
            "helpfulness_score": 0,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        }

    async def test_create_review_success(self, async_client: AsyncClient, sample_review_data, sample_review_response, authenticated_client_headers):
        """Test successfully creating a review."""
        with patch('backend.app.services.review.ReviewService.create_review') as mock_create:
            # Mock service response
            mock_review = Review(**sample_review_response)
            mock_create.return_value = mock_review

            response = await async_client.post(
                "/api/v1/reviews/",
                json=sample_review_data,
                headers=authenticated_client_headers
            )

            assert response.status_code == 201
            data = response.json()
            assert data["rating"] == 5
            assert data["title"] == "Great service!"
            assert data["status"] == "approved"

    async def test_create_review_invalid_rating(self, async_client: AsyncClient, sample_review_data, authenticated_client_headers):
        """Test creating review with invalid rating."""
        # Test invalid rating
        invalid_data = sample_review_data.copy()
        invalid_data["rating"] = 6  # Invalid rating

        response = await async_client.post(
            "/api/v1/reviews/",
            json=invalid_data,
            headers=authenticated_client_headers
        )

        assert response.status_code == 422  # Validation error

    async def test_create_review_missing_booking_id(self, async_client: AsyncClient, sample_review_data, authenticated_client_headers):
        """Test creating review without booking ID."""
        # Remove required field
        invalid_data = sample_review_data.copy()
        del invalid_data["booking_id"]

        response = await async_client.post(
            "/api/v1/reviews/",
            json=invalid_data,
            headers=authenticated_client_headers
        )

        assert response.status_code == 422  # Validation error

    async def test_create_review_unauthorized(self, async_client: AsyncClient, sample_review_data):
        """Test creating review without authentication."""
        response = await async_client.post(
            "/api/v1/reviews/",
            json=sample_review_data
        )

        assert response.status_code == 401  # Unauthorized

    async def test_get_review_by_id(self, async_client: AsyncClient, sample_review_response):
        """Test getting a review by ID."""
        with patch('backend.app.services.review.ReviewService.get_review_by_id') as mock_get:
            # Mock service response
            mock_review = Review(**sample_review_response)
            mock_get.return_value = mock_review

            response = await async_client.get("/api/v1/reviews/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["rating"] == 5

    async def test_get_review_not_found(self, async_client: AsyncClient):
        """Test getting non-existent review."""
        with patch('backend.app.services.review.ReviewService.get_review_by_id') as mock_get:
            # Mock service response (not found)
            mock_get.return_value = None

            response = await async_client.get("/api/v1/reviews/999")

            assert response.status_code == 404

    async def test_update_review_success(self, async_client: AsyncClient, sample_review_response, authenticated_client_headers):
        """Test successfully updating a review."""
        update_data = {
            "rating": 4,
            "title": "Updated title",
            "comment": "Updated comment"
        }

        with patch('backend.app.services.review.ReviewService.update_review') as mock_update:
            # Mock service response
            updated_review = sample_review_response.copy()
            updated_review.update(update_data)
            mock_review = Review(**updated_review)
            mock_update.return_value = mock_review

            response = await async_client.put(
                "/api/v1/reviews/1",
                json=update_data,
                headers=authenticated_client_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["rating"] == 4
            assert data["title"] == "Updated title"

    async def test_list_reviews_with_filters(self, async_client: AsyncClient, sample_review_response):
        """Test listing reviews with filters."""
        with patch('backend.app.services.review.ReviewService.list_reviews') as mock_list:
            # Mock service response
            mock_reviews = [Review(**sample_review_response)]
            mock_total = 1
            mock_list.return_value = (mock_reviews, mock_total)

            response = await async_client.get(
                "/api/v1/reviews/?salon_id=1&min_rating=4&status=approved&page=1&size=10"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["reviews"]) == 1
            assert data["page"] == 1
            assert data["size"] == 10

    async def test_list_reviews_pagination(self, async_client: AsyncClient, sample_review_response):
        """Test reviews pagination."""
        with patch('backend.app.services.review.ReviewService.list_reviews') as mock_list:
            # Mock multiple reviews
            mock_reviews = [Review(**sample_review_response) for _ in range(5)]
            mock_total = 25
            mock_list.return_value = (mock_reviews, mock_total)

            response = await async_client.get("/api/v1/reviews/?page=2&size=5")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 25
            assert data["page"] == 2
            assert data["size"] == 5
            assert data["has_next"] is True

    async def test_get_review_by_booking(self, async_client: AsyncClient, sample_review_response):
        """Test getting review by booking ID."""
        with patch('backend.app.services.review.ReviewService.get_review_by_booking_id') as mock_get:
            # Mock service response
            mock_review = Review(**sample_review_response)
            mock_get.return_value = mock_review

            response = await async_client.get("/api/v1/reviews/booking/1")

            assert response.status_code == 200
            data = response.json()
            assert data["booking_id"] == 1

    async def test_get_review_by_booking_not_found(self, async_client: AsyncClient):
        """Test getting review by booking ID when not found."""
        with patch('backend.app.services.review.ReviewService.get_review_by_booking_id') as mock_get:
            # Mock service response (not found)
            mock_get.return_value = None

            response = await async_client.get("/api/v1/reviews/booking/999")

            assert response.status_code == 200
            assert response.json() is None

    async def test_add_professional_response(self, async_client: AsyncClient, sample_review_response, authenticated_professional_headers):
        """Test adding professional response to review."""
        response_data = {
            "response_text": "Thank you for your feedback!"
        }

        with patch('backend.app.services.review.ReviewService.add_professional_response') as mock_response:
            # Mock service response
            updated_review = sample_review_response.copy()
            updated_review["professional_response"] = response_data["response_text"]
            mock_review = Review(**updated_review)
            mock_response.return_value = mock_review

            response = await async_client.post(
                "/api/v1/reviews/1/response",
                json=response_data,
                headers=authenticated_professional_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["professional_response"] == "Thank you for your feedback!"

    async def test_add_professional_response_unauthorized(self, async_client: AsyncClient, authenticated_client_headers):
        """Test adding professional response without proper role."""
        response_data = {
            "response_text": "Thank you for your feedback!"
        }

        response = await async_client.post(
            "/api/v1/reviews/1/response",
            json=response_data,
            headers=authenticated_client_headers  # Client role, not professional
        )

        assert response.status_code == 403  # Forbidden

    async def test_vote_helpfulness(self, async_client: AsyncClient, authenticated_client_headers):
        """Test voting on review helpfulness."""
        vote_data = {
            "is_helpful": True
        }

        with patch('backend.app.services.review.ReviewService.vote_helpfulness') as mock_vote:
            # Mock service response
            mock_vote.return_value = None

            response = await async_client.post(
                "/api/v1/reviews/1/helpfulness",
                json=vote_data,
                headers=authenticated_client_headers
            )

            assert response.status_code == 204  # No content

    async def test_flag_review(self, async_client: AsyncClient, authenticated_client_headers):
        """Test flagging a review."""
        flag_data = {
            "reason": "spam",
            "description": "This looks like spam content"
        }

        with patch('backend.app.services.review.ReviewService.flag_review') as mock_flag:
            # Mock service response
            mock_flag_obj = {
                "id": 1,
                "review_id": 1,
                "reporter_id": 1,
                "reason": "spam",
                "description": "This looks like spam content",
                "is_resolved": False,
                "created_at": "2024-01-01T10:00:00Z"
            }
            mock_flag.return_value = mock_flag_obj

            response = await async_client.post(
                "/api/v1/reviews/1/flag",
                json=flag_data,
                headers=authenticated_client_headers
            )

            assert response.status_code == 201
            data = response.json()
            assert data["reason"] == "spam"
            assert data["is_resolved"] is False

    async def test_get_review_statistics(self, async_client: AsyncClient):
        """Test getting review statistics."""
        with patch('backend.app.services.review.ReviewService.get_rating_statistics') as mock_stats:
            # Mock service response
            mock_stats_data = {
                "average_rating": 4.5,
                "total_reviews": 100,
                "rating_distribution": {5: 50, 4: 30, 3: 15, 2: 3, 1: 2}
            }
            mock_stats.return_value = mock_stats_data

            response = await async_client.get("/api/v1/reviews/statistics?salon_id=1")

            assert response.status_code == 200
            data = response.json()
            assert data["average_rating"] == 4.5
            assert data["total_reviews"] == 100

    async def test_get_review_trends(self, async_client: AsyncClient):
        """Test getting review trends."""
        with patch('backend.app.services.review.ReviewService.get_review_trends') as mock_trends:
            # Mock service response
            mock_trends_data = {
                "period_stats": [
                    {"date": "2024-01-01", "count": 5, "average_rating": 4.2},
                    {"date": "2024-01-02", "count": 8, "average_rating": 4.5}
                ],
                "trend_direction": "increasing",
                "total_period_reviews": 13
            }
            mock_trends.return_value = mock_trends_data

            response = await async_client.get("/api/v1/reviews/trends?salon_id=1&days=30")

            assert response.status_code == 200
            data = response.json()
            assert "period_stats" in data
            assert data["trend_direction"] == "increasing"

    async def test_get_recent_reviews(self, async_client: AsyncClient, sample_review_response):
        """Test getting recent reviews."""
        with patch('backend.app.services.review.ReviewService.get_recent_reviews') as mock_recent:
            # Mock service response
            mock_reviews = [Review(**sample_review_response)]
            mock_recent.return_value = mock_reviews

            response = await async_client.get("/api/v1/reviews/recent?days=7&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == 1


class TestReviewModerationEndpoints:
    """Test review moderation API endpoints (admin only)."""

    async def test_moderate_review_success(self, async_client: AsyncClient, sample_review_response, authenticated_admin_headers):
        """Test successfully moderating a review."""
        moderation_data = {
            "status": "approved",
            "reason": "inappropriate_content",
            "notes": "Content reviewed and approved"
        }

        with patch('backend.app.services.review.ReviewService.moderate_review') as mock_moderate:
            # Mock service response
            moderated_review = sample_review_response.copy()
            moderated_review["status"] = "approved"
            mock_review = Review(**moderated_review)
            mock_moderate.return_value = mock_review

            response = await async_client.post(
                "/api/v1/reviews/1/moderate",
                json=moderation_data,
                headers=authenticated_admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "approved"

    async def test_moderate_review_unauthorized(self, async_client: AsyncClient, authenticated_client_headers):
        """Test moderating review without admin role."""
        moderation_data = {
            "status": "approved",
            "notes": "Content reviewed and approved"
        }

        response = await async_client.post(
            "/api/v1/reviews/1/moderate",
            json=moderation_data,
            headers=authenticated_client_headers  # Client role, not admin
        )

        assert response.status_code == 403  # Forbidden

    async def test_get_pending_reviews(self, async_client: AsyncClient, sample_review_response, authenticated_admin_headers):
        """Test getting reviews pending moderation."""
        with patch('backend.app.services.review.ReviewService.get_pending_reviews_for_moderation') as mock_pending:
            # Mock service response
            pending_review = sample_review_response.copy()
            pending_review["status"] = "pending"
            mock_reviews = [Review(**pending_review)]
            mock_total = 1
            mock_pending.return_value = (mock_reviews, mock_total)

            response = await async_client.get(
                "/api/v1/reviews/moderation/pending",
                headers=authenticated_admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["reviews"][0]["status"] == "pending"

    async def test_get_flagged_reviews(self, async_client: AsyncClient, sample_review_response, authenticated_admin_headers):
        """Test getting flagged reviews."""
        with patch('backend.app.services.review.ReviewService.get_flagged_reviews') as mock_flagged:
            # Mock service response
            flagged_review = sample_review_response.copy()
            mock_reviews = [Review(**flagged_review)]
            mock_total = 1
            mock_flagged.return_value = (mock_reviews, mock_total)

            response = await async_client.get(
                "/api/v1/reviews/moderation/flagged",
                headers=authenticated_admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1

    async def test_bulk_moderate_reviews(self, async_client: AsyncClient, sample_review_response, authenticated_admin_headers):
        """Test bulk moderating reviews."""
        bulk_data = {
            "review_ids": [1, 2, 3],
            "status": "approved",
            "notes": "Bulk approved after review"
        }

        with patch('backend.app.services.review.ReviewService.bulk_moderate_reviews') as mock_bulk:
            # Mock service response
            moderated_reviews = [Review(**sample_review_response) for _ in range(3)]
            mock_bulk.return_value = moderated_reviews

            response = await async_client.post(
                "/api/v1/reviews/moderation/bulk",
                json=bulk_data,
                headers=authenticated_admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3

    async def test_resolve_review_flag(self, async_client: AsyncClient, authenticated_admin_headers):
        """Test resolving a review flag."""
        with patch('backend.app.services.review.ReviewService.resolve_flag') as mock_resolve:
            # Mock service response
            resolved_flag = {
                "id": 1,
                "review_id": 1,
                "reporter_id": 1,
                "reason": "spam",
                "is_resolved": True,
                "resolved_by": 1,
                "resolution_notes": "Flag reviewed and resolved",
                "resolved_at": "2024-01-01T10:00:00Z"
            }
            mock_resolve.return_value = resolved_flag

            response = await async_client.post(
                "/api/v1/reviews/flags/1/resolve?notes=Flag reviewed and resolved",
                headers=authenticated_admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_resolved"] is True
            assert data["resolution_notes"] == "Flag reviewed and resolved"


# Fixtures for authentication headers would be defined in conftest.py
@pytest.fixture
def authenticated_client_headers():
    """Headers for authenticated client user."""
    return {"Authorization": "Bearer client_token"}

@pytest.fixture
def authenticated_professional_headers():
    """Headers for authenticated professional user."""
    return {"Authorization": "Bearer professional_token"}

@pytest.fixture
def authenticated_admin_headers():
    """Headers for authenticated admin user."""
    return {"Authorization": "Bearer admin_token"}
