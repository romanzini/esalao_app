"""Unit tests for services routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole


class TestServicesRoutes:
    """Test services routes."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_service(self):
        """Mock service instance."""
        return Service(
            id=1,
            salon_id=1,
            name="Hair Cut",
            description="Professional hair cutting service",
            category="hair",
            price=50.00,
            duration_minutes=60,
            is_active=True,
        )

    @pytest.fixture
    def valid_service_data(self):
        """Valid service creation data."""
        return {
            "salon_id": 1,
            "name": "Hair Cut",
            "description": "Professional hair cutting service",
            "category": "hair",
            "price": 50.00,
            "duration_minutes": 60,
        }

    @patch('backend.app.api.v1.routes.services.get_current_user')
    @patch('backend.app.api.v1.routes.services.ServiceRepository')
    @patch('backend.app.api.v1.routes.services.SalonRepository')
    def test_create_service_success(self, mock_salon_repo_class, mock_service_repo_class, mock_get_current_user, client, valid_service_data, mock_service):
        """Test successful service creation."""
        # Mock current user as admin
        mock_user = MagicMock()
        mock_user.role = "admin"
        mock_get_current_user.return_value = mock_user

        # Mock salon repository
        mock_salon_repo = AsyncMock()
        mock_salon = MagicMock()
        mock_salon.id = 1
        mock_salon_repo.get_by_id.return_value = mock_salon
        mock_salon_repo_class.return_value = mock_salon_repo

        # Mock service repository
        mock_service_repo = AsyncMock()
        mock_service_repo.create.return_value = mock_service
        mock_service_repo_class.return_value = mock_service_repo

        # Make request
        response = client.post("/api/v1/services/", json=valid_service_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Hair Cut"
        assert data["price"] == 50.00

    def test_create_service_invalid_data(self, client):
        """Test service creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name
            "price": -10,  # Negative price
        }

        response = client.post("/api/v1/services/", json=invalid_data)
        assert response.status_code == 422

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_get_service_by_id_success(self, mock_get_repo, client, mock_service):
        """Test successful service retrieval by ID."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_service
        mock_get_repo.return_value = mock_repo

        # Make request
        response = client.get("/api/v1/services/1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Hair Cut"

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_get_service_by_id_not_found(self, mock_get_repo, client):
        """Test service retrieval with non-existent ID."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_get_repo.return_value = mock_repo

        # Make request
        response = client.get("/api/v1/services/999")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_list_services(self, mock_get_repo, client, mock_service):
        """Test listing services."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.list_all.return_value = [mock_service]
        mock_get_repo.return_value = mock_repo

        # Make request
        response = client.get("/api/v1/services/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Hair Cut"

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_list_services_by_salon(self, mock_get_repo, client, mock_service):
        """Test listing services by salon ID."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_salon_id.return_value = [mock_service]
        mock_get_repo.return_value = mock_repo

        # Make request with salon_id query parameter
        response = client.get("/api/v1/services/?salon_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["salon_id"] == 1

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_list_services_by_category(self, mock_get_repo, client, mock_service):
        """Test listing services by category."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_category.return_value = [mock_service]
        mock_get_repo.return_value = mock_repo

        # Make request with category query parameter
        response = client.get("/api/v1/services/?category=hair")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "hair"

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_search_services(self, mock_get_repo, client, mock_service):
        """Test searching services by name."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.search_by_name.return_value = [mock_service]
        mock_get_repo.return_value = mock_repo

        # Make request
        response = client.get("/api/v1/services/search?query=hair")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Hair" in data[0]["name"]

    def test_search_services_missing_query(self, client):
        """Test search services without query parameter."""
        response = client.get("/api/v1/services/search")
        assert response.status_code == 422

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_update_service_success(self, mock_get_repo, client, mock_service):
        """Test successful service update."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_service
        mock_repo.update.return_value = mock_service
        mock_get_repo.return_value = mock_repo

        update_data = {
            "name": "Premium Hair Cut",
            "price": 75.00,
        }

        # Make request
        response = client.put("/api/v1/services/1", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_update_service_not_found(self, mock_get_repo, client):
        """Test updating non-existent service."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_get_repo.return_value = mock_repo

        update_data = {
            "name": "Updated Service",
        }

        # Make request
        response = client.put("/api/v1/services/999", json=update_data)

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_delete_service_success(self, mock_get_repo, client, mock_service):
        """Test successful service deletion (soft delete)."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_service
        mock_repo.soft_delete.return_value = mock_service
        mock_get_repo.return_value = mock_repo

        # Make request
        response = client.delete("/api/v1/services/1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

    @patch('backend.app.api.v1.routes.services.get_service_repository')
    def test_delete_service_not_found(self, mock_get_repo, client):
        """Test deleting non-existent service."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_get_repo.return_value = mock_repo

        # Make request
        response = client.delete("/api/v1/services/999")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_service_categories(self, client):
        """Test getting service categories."""
        response = client.get("/api/v1/services/categories")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        # Should contain categories like 'hair', 'nails', etc.
        category_values = [item["value"] for item in data]
        assert "hair" in category_values

    def test_invalid_service_id_parameter(self, client):
        """Test routes with invalid service ID parameter."""
        # Test with non-integer ID
        response = client.get("/api/v1/services/invalid_id")
        assert response.status_code == 422

    def test_create_service_missing_required_fields(self, client):
        """Test service creation with missing required fields."""
        incomplete_data = {
            "name": "Test Service",
            # Missing other required fields
        }

        response = client.post("/api/v1/services/", json=incomplete_data)
        assert response.status_code == 422
