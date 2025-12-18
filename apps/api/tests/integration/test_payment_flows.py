"""
Integration Tests for Payment Flows
Tests Stripe checkout, payment processing, and refunds
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import uuid


class TestLicensePurchaseFlow:
    """Test complete license purchase flow"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_license_price(self, auth_client: AsyncClient, test_identity):
        """Test license price calculation endpoint"""
        response = await auth_client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "single_use",
                "usage_type": "personal",
                "duration_days": 30
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_price" in data
        assert "breakdown" in data
        assert data["total_price"] > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculate_price_commercial_higher(self, auth_client: AsyncClient, test_identity):
        """Test commercial license costs more than personal"""
        personal_response = await auth_client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "single_use",
                "usage_type": "personal",
                "duration_days": 30
            }
        )

        commercial_response = await auth_client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "single_use",
                "usage_type": "commercial",
                "duration_days": 30
            }
        )

        assert personal_response.status_code == 200
        assert commercial_response.status_code == 200

        personal_price = personal_response.json()["total_price"]
        commercial_price = commercial_response.json()["total_price"]
        assert commercial_price > personal_price

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_purchase_license_creates_checkout(self, auth_client: AsyncClient, test_identity):
        """Test license purchase creates Stripe checkout session"""
        with patch('stripe.Customer.create') as mock_customer, \
             patch('stripe.checkout.Session.create') as mock_session:

            mock_customer.return_value = MagicMock(id="cus_test_123")
            mock_session.return_value = MagicMock(
                id="cs_test_123",
                url="https://checkout.stripe.com/test",
                payment_intent="pi_test_123"
            )

            response = await auth_client.post(
                "/api/v1/marketplace/license/purchase",
                json={
                    "identity_id": str(test_identity.id),
                    "license_type": "single_use",
                    "usage_type": "personal",
                    "duration_days": 30,
                    "project_name": "Test Project"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "checkout_url" in data
            assert "session_id" in data
            assert "price_usd" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_purchase_requires_identity_allows_commercial(self, auth_client: AsyncClient, db_session: AsyncSession, test_user):
        """Test purchase requires identity to allow commercial use"""
        from app.models.identity import Identity, IdentityStatus

        # Create identity that doesn't allow commercial use
        identity = Identity(
            id=uuid.uuid4(),
            user_id=test_user.id,
            display_name="No Commercial Actor",
            status=IdentityStatus.VERIFIED,
            allow_commercial_use=False
        )
        db_session.add(identity)
        await db_session.commit()

        response = await auth_client.post(
            "/api/v1/marketplace/license/purchase",
            json={
                "identity_id": str(identity.id),
                "license_type": "single_use",
                "usage_type": "commercial",
                "duration_days": 30
            }
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_license_type_rejected(self, auth_client: AsyncClient, test_identity):
        """Test invalid license type is rejected"""
        response = await auth_client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "invalid_type",
                "usage_type": "personal",
                "duration_days": 30
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_duration_rejected(self, auth_client: AsyncClient, test_identity):
        """Test invalid duration (>365 days) is rejected"""
        response = await auth_client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "single_use",
                "usage_type": "personal",
                "duration_days": 500  # Over 365 limit
            }
        )

        assert response.status_code == 422


class TestRefundFlow:
    """Test refund request and processing flow"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_policy_endpoint(self, client: AsyncClient):
        """Test refund policy is accessible"""
        response = await client.get("/api/v1/refunds/policy")

        assert response.status_code == 200
        data = response.json()
        assert "refund_window_days" in data
        assert "max_refunds_per_user" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_history_requires_auth(self, client: AsyncClient):
        """Test refund history requires authentication"""
        response = await client.get("/api/v1/refunds/history")

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_history_authenticated(self, auth_client: AsyncClient):
        """Test authenticated user can see refund history"""
        response = await auth_client.get("/api/v1/refunds/history")

        assert response.status_code == 200
        data = response.json()
        assert "refunds" in data
        assert "total" in data
        assert "remaining_refunds" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_not_own_license_rejected(self, auth_client: AsyncClient, other_user_license):
        """Test cannot refund another user's license"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(other_user_license.id),
                "reason": "Testing refund for another user's license"
            }
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_already_refunded_rejected(self, auth_client: AsyncClient, refunded_license):
        """Test cannot refund already refunded license"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(refunded_license.id),
                "reason": "Testing double refund attempt"
            }
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_outside_window_rejected(self, auth_client: AsyncClient, old_license):
        """Test cannot refund license outside refund window"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(old_license.id),
                "reason": "Testing refund outside window"
            }
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_too_soon_rejected(self, auth_client: AsyncClient, very_recent_license):
        """Test cannot refund license purchased too recently"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(very_recent_license.id),
                "reason": "Testing immediate refund attempt"
            }
        )

        assert response.status_code == 400
        assert "wait" in response.json()["detail"].lower()


class TestMyLicenses:
    """Test license management endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_my_licenses(self, auth_client: AsyncClient, test_license):
        """Test user can see their licenses"""
        response = await auth_client.get("/api/v1/marketplace/licenses/mine")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_active_licenses_only(self, auth_client: AsyncClient, test_license, expired_license):
        """Test filtering to active licenses only"""
        response = await auth_client.get(
            "/api/v1/marketplace/licenses/mine",
            params={"active_only": True}
        )

        assert response.status_code == 200
        data = response.json()
        # All returned licenses should be active
        for license in data:
            assert license.get("is_active", False) is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_license_details(self, auth_client: AsyncClient, test_license):
        """Test getting specific license details"""
        response = await auth_client.get(
            f"/api/v1/marketplace/licenses/{test_license.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_license.id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cannot_access_other_user_license(self, auth_client: AsyncClient, other_user_license):
        """Test cannot access another user's license details"""
        response = await auth_client.get(
            f"/api/v1/marketplace/licenses/{other_user_license.id}"
        )

        assert response.status_code == 403
