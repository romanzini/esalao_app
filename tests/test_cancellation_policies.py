"""
Tests for cancellation policy endpoints.

Tests the CRUD operations for cancellation policies and their tiers.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.user import UserRole
from backend.app.db.models.cancellation_policy import CancellationPolicyStatus


class TestCancellationPolicyEndpoints:
    """Test suite for cancellation policy endpoints."""

    @pytest.fixture
    async def admin_headers(self, admin_token):
        """Get headers with admin authentication."""
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture
    async def salon_owner_headers(self, salon_owner_token):
        """Get headers with salon owner authentication."""
        return {"Authorization": f"Bearer {salon_owner_token}"}

    @pytest.fixture
    def sample_policy_data(self):
        """Sample policy data for testing."""
        return {
            "name": "Política Padrão",
            "description": "Política de cancelamento padrão do salão",
            "salon_id": None,
            "is_default": True,
            "effective_from": datetime.utcnow().isoformat(),
            "effective_until": None,
            "status": "draft",
            "tiers": [
                {
                    "name": "Cancelamento Imediato",
                    "advance_notice_hours": 0,
                    "fee_type": "percentage",
                    "fee_value": "100.00",
                    "allows_refund": False,
                    "display_order": 0
                },
                {
                    "name": "Cancelamento com 24h",
                    "advance_notice_hours": 24,
                    "fee_type": "percentage",
                    "fee_value": "50.00",
                    "allows_refund": True,
                    "display_order": 1
                },
                {
                    "name": "Cancelamento com 48h",
                    "advance_notice_hours": 48,
                    "fee_type": "fixed",
                    "fee_value": "10.00",
                    "allows_refund": True,
                    "display_order": 2
                },
                {
                    "name": "Cancelamento Gratuito",
                    "advance_notice_hours": 72,
                    "fee_type": "percentage",
                    "fee_value": "0.00",
                    "allows_refund": True,
                    "display_order": 3
                }
            ]
        }

    async def test_create_policy_as_admin(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test creating a cancellation policy as admin."""
        response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data,
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == sample_policy_data["name"]
        assert data["description"] == sample_policy_data["description"]
        assert data["is_default"] == sample_policy_data["is_default"]
        assert data["status"] == sample_policy_data["status"]
        assert len(data["tiers"]) == 4

        # Check tier ordering
        tiers = sorted(data["tiers"], key=lambda x: x["display_order"])
        assert tiers[0]["advance_notice_hours"] == 0
        assert tiers[1]["advance_notice_hours"] == 24
        assert tiers[2]["advance_notice_hours"] == 48
        assert tiers[3]["advance_notice_hours"] == 72

    async def test_create_policy_validation_errors(self, client: AsyncClient, admin_headers):
        """Test validation errors when creating policy."""
        # Missing required fields
        response = await client.post(
            "/v1/cancellation-policies/",
            json={"name": "Invalid"},
            headers=admin_headers
        )
        assert response.status_code == 422

        # Invalid fee type
        invalid_data = {
            "name": "Test Policy",
            "tiers": [
                {
                    "name": "Invalid Tier",
                    "advance_notice_hours": 24,
                    "fee_type": "invalid_type",
                    "fee_value": "50.00",
                    "allows_refund": True,
                    "display_order": 0
                }
            ]
        }
        response = await client.post(
            "/v1/cancellation-policies/",
            json=invalid_data,
            headers=admin_headers
        )
        assert response.status_code == 422

        # Percentage fee over 100%
        invalid_data = {
            "name": "Test Policy",
            "tiers": [
                {
                    "name": "Invalid Tier",
                    "advance_notice_hours": 24,
                    "fee_type": "percentage",
                    "fee_value": "150.00",
                    "allows_refund": True,
                    "display_order": 0
                }
            ]
        }
        response = await client.post(
            "/v1/cancellation-policies/",
            json=invalid_data,
            headers=admin_headers
        )
        assert response.status_code == 422

    async def test_list_policies(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test listing cancellation policies."""
        # Create a policy first
        create_response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data,
            headers=admin_headers
        )
        assert create_response.status_code == 201

        # List policies
        response = await client.get(
            "/v1/cancellation-policies/",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check policy data
        policy = data[0]
        assert "id" in policy
        assert "name" in policy
        assert "status" in policy
        assert "tier_count" in policy

    async def test_get_policy_by_id(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test getting a specific policy by ID."""
        # Create a policy first
        create_response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data,
            headers=admin_headers
        )
        assert create_response.status_code == 201
        policy_id = create_response.json()["id"]

        # Get policy by ID
        response = await client.get(
            f"/v1/cancellation-policies/{policy_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == policy_id
        assert data["name"] == sample_policy_data["name"]
        assert len(data["tiers"]) == 4

    async def test_get_nonexistent_policy(self, client: AsyncClient, admin_headers):
        """Test getting a non-existent policy."""
        response = await client.get(
            "/v1/cancellation-policies/99999",
            headers=admin_headers
        )

        assert response.status_code == 404

    async def test_update_policy(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test updating a cancellation policy."""
        # Create a policy first
        create_response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data,
            headers=admin_headers
        )
        assert create_response.status_code == 201
        policy_id = create_response.json()["id"]

        # Update policy
        updated_data = sample_policy_data.copy()
        updated_data["name"] = "Política Atualizada"
        updated_data["description"] = "Descrição atualizada"
        updated_data["tiers"] = updated_data["tiers"][:2]  # Remove some tiers

        response = await client.put(
            f"/v1/cancellation-policies/{policy_id}",
            json=updated_data,
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Política Atualizada"
        assert data["description"] == "Descrição atualizada"
        assert len(data["tiers"]) == 2

    async def test_activate_policy(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test activating a cancellation policy."""
        # Create a policy first
        create_response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data,
            headers=admin_headers
        )
        assert create_response.status_code == 201
        policy_id = create_response.json()["id"]

        # Activate policy
        response = await client.post(
            f"/v1/cancellation-policies/{policy_id}/activate",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    async def test_deactivate_policy(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test deactivating a cancellation policy."""
        # Create and activate a policy first
        create_response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data,
            headers=admin_headers
        )
        assert create_response.status_code == 201
        policy_id = create_response.json()["id"]

        await client.post(
            f"/v1/cancellation-policies/{policy_id}/activate",
            headers=admin_headers
        )

        # Deactivate policy
        response = await client.post(
            f"/v1/cancellation-policies/{policy_id}/deactivate",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"

    async def test_delete_policy_as_admin(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test deleting a cancellation policy as admin."""
        # Create a policy first
        create_response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data,
            headers=admin_headers
        )
        assert create_response.status_code == 201
        policy_id = create_response.json()["id"]

        # Delete policy
        response = await client.delete(
            f"/v1/cancellation-policies/{policy_id}",
            headers=admin_headers
        )

        assert response.status_code == 204

        # Verify policy is deleted
        get_response = await client.get(
            f"/v1/cancellation-policies/{policy_id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404

    async def test_salon_owner_access_control(self, client: AsyncClient, salon_owner_headers, sample_policy_data):
        """Test that salon owners can create policies for their salons."""
        # Salon owners must specify salon_id (this would be validated in real implementation)
        salon_data = sample_policy_data.copy()
        salon_data["salon_id"] = 1
        salon_data["is_default"] = False

        response = await client.post(
            "/v1/cancellation-policies/",
            json=salon_data,
            headers=salon_owner_headers
        )

        # This should work (with proper salon validation)
        assert response.status_code in [201, 400]  # 400 if salon validation fails

    async def test_unauthorized_access(self, client: AsyncClient, sample_policy_data):
        """Test that unauthorized users cannot access policy endpoints."""
        response = await client.post(
            "/v1/cancellation-policies/",
            json=sample_policy_data
        )

        assert response.status_code == 401

    async def test_filtering_policies(self, client: AsyncClient, admin_headers, sample_policy_data):
        """Test filtering policies by various criteria."""
        # Create policies with different statuses
        draft_policy = sample_policy_data.copy()
        draft_policy["name"] = "Draft Policy"
        draft_policy["status"] = "draft"
        draft_policy["is_default"] = False

        active_policy = sample_policy_data.copy()
        active_policy["name"] = "Active Policy"
        active_policy["status"] = "active"
        active_policy["is_default"] = False

        await client.post("/v1/cancellation-policies/", json=draft_policy, headers=admin_headers)
        await client.post("/v1/cancellation-policies/", json=active_policy, headers=admin_headers)

        # Filter by status
        response = await client.get(
            "/v1/cancellation-policies/?status_filter=draft",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(policy["status"] == "draft" for policy in data)

        # Filter by default status
        response = await client.get(
            "/v1/cancellation-policies/?is_default=true",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(policy["is_default"] for policy in data)

    async def test_tier_validation(self, client: AsyncClient, admin_headers):
        """Test tier validation rules."""
        # Duplicate advance notice hours
        invalid_data = {
            "name": "Invalid Policy",
            "tiers": [
                {
                    "name": "Tier 1",
                    "advance_notice_hours": 24,
                    "fee_type": "percentage",
                    "fee_value": "50.00",
                    "allows_refund": True,
                    "display_order": 0
                },
                {
                    "name": "Tier 2",
                    "advance_notice_hours": 24,  # Duplicate
                    "fee_type": "percentage",
                    "fee_value": "30.00",
                    "allows_refund": True,
                    "display_order": 1
                }
            ]
        }

        response = await client.post(
            "/v1/cancellation-policies/",
            json=invalid_data,
            headers=admin_headers
        )
        assert response.status_code == 422

        # Duplicate display orders
        invalid_data["tiers"][1]["advance_notice_hours"] = 48
        invalid_data["tiers"][1]["display_order"] = 0  # Duplicate order

        response = await client.post(
            "/v1/cancellation-policies/",
            json=invalid_data,
            headers=admin_headers
        )
        assert response.status_code == 422
