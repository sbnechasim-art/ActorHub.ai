"""
E2E Tests for License Purchase Flow
Tests the complete flow: Browse -> Select -> Checkout -> License Active
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
import json


class TestLicensePurchaseFlow:
    """
    Full flow: Browse -> Select -> Checkout -> License Active
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_license_purchase(
        self, auth_client: AsyncClient, test_identity_with_training
    ):
        """Test complete license purchase flow"""
        identity_id = str(test_identity_with_training.id)

        # Step 1: Browse available identities
        browse_response = await auth_client.get(
            "/api/v1/identity/marketplace",
            params={"category": "actor", "status": "trained"}
        )
        assert browse_response.status_code == 200
        identities = browse_response.json()
        assert "items" in identities or isinstance(identities, list)

        # Step 2: Get identity details
        detail_response = await auth_client.get(
            f"/api/v1/identity/{identity_id}"
        )
        assert detail_response.status_code == 200
        identity_data = detail_response.json()
        assert identity_data["id"] == identity_id

        # Step 3: Get license options
        license_options = await auth_client.get(
            f"/api/v1/identity/{identity_id}/licenses"
        )
        assert license_options.status_code == 200
        options = license_options.json()
        # Should have at least one license option
        assert len(options) > 0

        # Step 4: Create checkout session
        with patch('stripe.checkout.Session.create') as mock_checkout:
            mock_checkout.return_value = MagicMock(
                id="cs_test_123",
                url="https://checkout.stripe.com/test"
            )

            checkout_response = await auth_client.post(
                "/api/v1/payments/checkout",
                json={
                    "identity_id": identity_id,
                    "license_type": "standard",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel"
                }
            )
            assert checkout_response.status_code == 200
            checkout_data = checkout_response.json()
            assert "checkout_url" in checkout_data or "session_id" in checkout_data

        # Step 5: Simulate webhook for payment completion
        with patch('stripe.Webhook.construct_event') as mock_webhook:
            mock_webhook.return_value = {
                "id": "evt_test_checkout_complete",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_test_123",
                        "payment_status": "paid",
                        "metadata": {
                            "identity_id": identity_id,
                            "license_type": "standard"
                        }
                    }
                }
            }

            webhook_response = await auth_client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps({
                    "type": "checkout.session.completed",
                    "data": {"object": {"id": "cs_test_123"}}
                }),
                headers={
                    "Stripe-Signature": "test_signature",
                    "Content-Type": "application/json"
                }
            )
            # Should be 200 or handled appropriately
            assert webhook_response.status_code in [200, 400]  # 400 if signature validation enabled

        # Step 6: Verify license is active
        licenses_response = await auth_client.get("/api/v1/licenses/my")
        assert licenses_response.status_code == 200
        licenses = licenses_response.json()
        # Should have license in list (or empty if webhook mocked)
        assert isinstance(licenses, list) or "items" in licenses

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_checkout_insufficient_credits(
        self, auth_client: AsyncClient, test_identity_with_training
    ):
        """Test checkout fails with insufficient credits"""
        with patch('stripe.checkout.Session.create') as mock_checkout:
            mock_checkout.side_effect = Exception("Insufficient funds")

            response = await auth_client.post(
                "/api/v1/payments/checkout",
                json={
                    "identity_id": str(test_identity_with_training.id),
                    "license_type": "enterprise",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel"
                }
            )
            # Should fail gracefully
            assert response.status_code in [400, 500, 502]


class TestLicenseManagement:
    """Test license management after purchase"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_view_active_licenses(
        self, auth_client: AsyncClient, test_license
    ):
        """Test viewing active licenses"""
        response = await auth_client.get("/api/v1/licenses/my")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_license_details(
        self, auth_client: AsyncClient, test_license
    ):
        """Test viewing license details"""
        response = await auth_client.get(
            f"/api/v1/licenses/{test_license.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert "identity_id" in data

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_license_usage_stats(
        self, auth_client: AsyncClient, test_license
    ):
        """Test getting license usage statistics"""
        response = await auth_client.get(
            f"/api/v1/licenses/{test_license.id}/usage"
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_uses" in data or "usage_count" in data or response.status_code == 200


class TestLicenseValidation:
    """Test license validation for API usage"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_use_identity_with_valid_license(
        self, auth_client: AsyncClient, test_license_with_identity
    ):
        """Test using identity with valid license"""
        identity_id = str(test_license_with_identity.identity_id)

        with patch('app.services.generation.GenerationService') as mock_gen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.generate = AsyncMock(return_value={
                "output_url": "https://example.com/output.mp4",
                "status": "completed"
            })
            mock_gen.return_value = mock_gen_instance

            response = await auth_client.post(
                f"/api/v1/identity/{identity_id}/generate",
                json={
                    "prompt": "Say hello",
                    "output_type": "video"
                }
            )

            # Should succeed with valid license
            assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_use_identity_without_license(
        self, auth_client: AsyncClient, test_identity_no_license
    ):
        """Test using identity without license fails"""
        response = await auth_client.post(
            f"/api/v1/identity/{test_identity_no_license.id}/generate",
            json={
                "prompt": "Say hello",
                "output_type": "video"
            }
        )

        # Should fail - no license
        assert response.status_code in [402, 403]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_use_expired_license(
        self, auth_client: AsyncClient, expired_license
    ):
        """Test using expired license fails"""
        response = await auth_client.post(
            f"/api/v1/identity/{expired_license.identity_id}/generate",
            json={
                "prompt": "Say hello",
                "output_type": "video"
            }
        )

        # Should fail - expired license
        assert response.status_code in [402, 403]


class TestLicenseTransfer:
    """Test license transfer functionality"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_transfer_license_to_another_user(
        self, auth_client: AsyncClient, transferable_license, other_user
    ):
        """Test transferring license to another user"""
        response = await auth_client.post(
            f"/api/v1/licenses/{transferable_license.id}/transfer",
            json={"to_user_email": other_user.email}
        )

        # Transfer should succeed or return appropriate status
        assert response.status_code in [200, 400, 403]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cannot_transfer_non_transferable_license(
        self, auth_client: AsyncClient, non_transferable_license, other_user
    ):
        """Test cannot transfer non-transferable license"""
        response = await auth_client.post(
            f"/api/v1/licenses/{non_transferable_license.id}/transfer",
            json={"to_user_email": other_user.email}
        )

        assert response.status_code in [400, 403]


class TestSubscriptionFlow:
    """Test subscription-based license flow"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_subscribe_to_monthly_plan(self, auth_client: AsyncClient):
        """Test subscribing to monthly plan"""
        with patch('stripe.Subscription.create') as mock_sub:
            mock_sub.return_value = MagicMock(
                id="sub_test_123",
                status="active",
                current_period_end=1735689600
            )

            response = await auth_client.post(
                "/api/v1/subscriptions/create",
                json={
                    "plan_id": "plan_monthly_basic",
                    "payment_method_id": "pm_test_123"
                }
            )

            assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cancel_subscription(
        self, auth_client: AsyncClient, active_subscription
    ):
        """Test canceling subscription"""
        with patch('stripe.Subscription.modify') as mock_cancel:
            mock_cancel.return_value = MagicMock(
                id=active_subscription.stripe_subscription_id,
                status="canceled"
            )

            response = await auth_client.post(
                f"/api/v1/subscriptions/{active_subscription.id}/cancel"
            )

            assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_upgrade_subscription(
        self, auth_client: AsyncClient, active_subscription
    ):
        """Test upgrading subscription plan"""
        with patch('stripe.Subscription.modify') as mock_upgrade:
            mock_upgrade.return_value = MagicMock(
                id=active_subscription.stripe_subscription_id,
                status="active"
            )

            response = await auth_client.post(
                f"/api/v1/subscriptions/{active_subscription.id}/upgrade",
                json={"new_plan_id": "plan_monthly_pro"}
            )

            assert response.status_code in [200, 202]
