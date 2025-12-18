"""
Integration Tests for Refund Endpoints
Tests refund request, status, and history
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch, MagicMock


class TestRefundRequest:
    """Test refund request endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_success(
        self, auth_client: AsyncClient, test_license_with_payment
    ):
        """Test successful refund request"""
        with patch('stripe.Refund.create') as mock_refund:
            mock_refund.return_value = MagicMock(
                id="re_test_123",
                status="succeeded"
            )

            response = await auth_client.post(
                "/api/v1/refunds/request",
                json={
                    "license_id": str(test_license_with_payment.id),
                    "reason": "Not satisfied with the quality of the product"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "succeeded"
            assert "refund_id" in data
            assert data["amount"] > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_license_not_found(self, auth_client: AsyncClient):
        """Test refund request for non-existent license"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(uuid4()),
                "reason": "Testing non-existent license"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_not_your_license(
        self, auth_client: AsyncClient, other_user_license
    ):
        """Test cannot request refund for other user's license"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(other_user_license.id),
                "reason": "Trying to refund someone else's license"
            }
        )

        assert response.status_code == 403
        assert "not your license" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_already_refunded(
        self, auth_client: AsyncClient, refunded_license
    ):
        """Test cannot request refund for already refunded license"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(refunded_license.id),
                "reason": "Trying to double refund"
            }
        )

        assert response.status_code == 400
        assert "already refunded" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_window_expired(
        self, auth_client: AsyncClient, old_license
    ):
        """Test refund request after window expires"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(old_license.id),
                "reason": "Trying to refund after 14 days"
            }
        )

        assert response.status_code == 400
        assert "window expired" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_too_soon(
        self, auth_client: AsyncClient, very_recent_license
    ):
        """Test refund request within 1 hour of purchase"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(very_recent_license.id),
                "reason": "Trying to refund immediately"
            }
        )

        assert response.status_code == 400
        assert "wait at least" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_reason_too_short(
        self, auth_client: AsyncClient, test_license_with_payment
    ):
        """Test refund request with reason too short"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(test_license_with_payment.id),
                "reason": "Bad"  # Too short
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_request_refund_max_reached(
        self, auth_client: AsyncClient, user_with_max_refunds, new_license
    ):
        """Test refund request when user reached max refunds"""
        response = await auth_client.post(
            "/api/v1/refunds/request",
            json={
                "license_id": str(new_license.id),
                "reason": "Trying to get fourth refund"
            }
        )

        assert response.status_code == 400
        assert "maximum" in response.json()["error"]["message"].lower()


class TestRefundStatus:
    """Test refund status endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_refund_status(
        self, auth_client: AsyncClient, completed_refund
    ):
        """Test getting refund status"""
        with patch('stripe.Refund.retrieve') as mock_retrieve:
            mock_retrieve.return_value = MagicMock(
                status="succeeded",
                created=1234567890
            )

            response = await auth_client.get(
                f"/api/v1/refunds/status/{completed_refund.stripe_payment_intent_id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "amount" in data
            assert "created_at" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_refund_status_not_found(self, auth_client: AsyncClient):
        """Test getting status for non-existent refund"""
        response = await auth_client.get("/api/v1/refunds/status/re_nonexistent")

        assert response.status_code == 404


class TestRefundHistory:
    """Test refund history endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_refund_history(self, auth_client: AsyncClient):
        """Test getting user's refund history"""
        response = await auth_client.get("/api/v1/refunds/history")

        assert response.status_code == 200
        data = response.json()
        assert "refunds" in data
        assert "total" in data
        assert "remaining_refunds" in data
        assert isinstance(data["refunds"], list)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_refund_history_with_pagination(self, auth_client: AsyncClient):
        """Test refund history with pagination"""
        response = await auth_client.get(
            "/api/v1/refunds/history?limit=5&offset=0"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["refunds"]) <= 5


class TestRefundPolicy:
    """Test refund policy endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_refund_policy(self, client: AsyncClient):
        """Test getting refund policy (public endpoint)"""
        response = await client.get("/api/v1/refunds/policy")

        assert response.status_code == 200
        data = response.json()
        assert "refund_window_days" in data
        assert "max_refunds_per_user" in data
        assert "min_purchase_age_hours" in data
        assert "policy_summary" in data
        assert data["refund_window_days"] == 14
        assert data["max_refunds_per_user"] == 3


class TestAdminRefunds:
    """Test admin refund endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_pending_refunds_admin(self, admin_client: AsyncClient):
        """Test admin can view pending refunds"""
        response = await admin_client.get("/api/v1/refunds/admin/pending")

        assert response.status_code == 200
        data = response.json()
        assert "pending_refunds" in data
        assert isinstance(data["pending_refunds"], list)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_pending_refunds_non_admin(self, auth_client: AsyncClient):
        """Test non-admin cannot view pending refunds"""
        response = await auth_client.get("/api/v1/refunds/admin/pending")

        assert response.status_code == 403
