"""Simple tests for professional routes focused on coverage."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.models.professional import Professional


class TestProfessionalRoutesSimple:
    """Test professional routes for maximum coverage impact."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_professional(self):
        """Mock professional instance."""
        now = datetime.now()
        professional = Professional(
            id=1,
            user_id=1,
            salon_id=1,
            specialties=["Hair", "Nails"],
            bio="Professional hairstylist",
            commission_percentage=15.0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        return professional

    @patch('backend.app.api.v1.routes.professionals.ProfessionalRepository')
    def test_list_professionals_by_salon(self, mock_professional_repo_class, client, mock_professional):
        """Test listing professionals for specific salon."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_salon_id.return_value = [mock_professional]
        mock_professional_repo_class.return_value = mock_repo

        # Make request
        response = client.get("/api/v1/professionals/?salon_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "professionals" in data
        assert len(data["professionals"]) == 1
        assert data["professionals"][0]["specialties"] == ["Hair", "Nails"]

    @patch('backend.app.api.v1.routes.professionals.ProfessionalRepository')
    def test_list_professionals_empty(self, mock_professional_repo_class, client):
        """Test listing professionals with empty result."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_salon_id.return_value = []
        mock_professional_repo_class.return_value = mock_repo

        # Make request with salon_id to trigger repository call
        response = client.get("/api/v1/professionals/?salon_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "professionals" in data
        assert len(data["professionals"]) == 0

    def test_list_professionals_without_filters(self, client):
        """Test listing professionals without any filters."""
        # Make request without filters
        response = client.get("/api/v1/professionals/")

        # Assert - should return empty list when no salon_id provided
        assert response.status_code == 200
        data = response.json()
        assert len(data["professionals"]) == 0
        assert data["total"] == 0

    @patch('backend.app.api.v1.routes.professionals.ProfessionalRepository')
    def test_get_professional_by_id_success(self, mock_professional_repo_class, client, mock_professional):
        """Test getting professional by ID."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_professional
        mock_professional_repo_class.return_value = mock_repo

        # Make request
        response = client.get("/api/v1/professionals/1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["specialties"] == ["Hair", "Nails"]

    @patch('backend.app.api.v1.routes.professionals.ProfessionalRepository')
    def test_get_professional_by_id_not_found(self, mock_professional_repo_class, client):
        """Test getting non-existent professional."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_professional_repo_class.return_value = mock_repo

        # Make request
        response = client.get("/api/v1/professionals/999")

        # Assert
        assert response.status_code == 404


