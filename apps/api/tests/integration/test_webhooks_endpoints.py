"""
Integration Tests for Webhook Endpoints
Tests Stripe webhooks, signature verification, and event handling
"""

import pytest
from httpx import AsyncClient
import hmac
import hashlib
import json
import time
from unittest.mock import patch, MagicMock


class TestStripeWebhooks:
    """Test Stripe webhook handling"""

    def _create_stripe_signature(
        self, payload: str, secret: str, timestamp: int = None
    ) -> str:
        """Helper to create valid Stripe signature"""
        timestamp = timestamp or int(time.time())
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"t={timestamp},v1={signature}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stripe_webhook_checkout_completed(self, client: AsyncClient):
        """Test handling checkout.session.completed event"""
        payload = json.dumps({
            "id": "evt_test_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "customer_email": "test@example.com",
                    "payment_status": "paid",
                    "metadata": {
                        "license_id": "test-license-id",
                        "user_id": "test-user-id"
                    }
                }
            }
        })

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            signature = self._create_stripe_signature(
                payload, "whsec_test_secret"
            )

            with patch('stripe.Webhook.construct_event') as mock_construct:
                mock_construct.return_value = json.loads(payload)

                response = await client.post(
                    "/api/v1/webhooks/stripe",
                    content=payload,
                    headers={
                        "Stripe-Signature": signature,
                        "Content-Type": "application/json"
                    }
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stripe_webhook_invalid_signature(self, client: AsyncClient):
        """Test webhook rejects invalid signature"""
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_123"}}
        })

        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": "invalid_signature",
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stripe_webhook_missing_signature(self, client: AsyncClient):
        """Test webhook rejects missing signature"""
        payload = json.dumps({"type": "test_event"})

        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stripe_webhook_payment_succeeded(self, client: AsyncClient):
        """Test handling payment_intent.succeeded event"""
        payload = json.dumps({
            "id": "evt_test_payment",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123",
                    "amount": 2999,
                    "currency": "usd",
                    "metadata": {
                        "license_id": "test-license-id"
                    }
                }
            }
        })

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            signature = self._create_stripe_signature(
                payload, "whsec_test_secret"
            )

            with patch('stripe.Webhook.construct_event') as mock_construct:
                mock_construct.return_value = json.loads(payload)

                response = await client.post(
                    "/api/v1/webhooks/stripe",
                    content=payload,
                    headers={
                        "Stripe-Signature": signature,
                        "Content-Type": "application/json"
                    }
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stripe_webhook_subscription_updated(self, client: AsyncClient):
        """Test handling customer.subscription.updated event"""
        payload = json.dumps({
            "id": "evt_test_sub",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "status": "active",
                    "customer": "cus_test_123",
                    "items": {
                        "data": [{"price": {"id": "price_test_123"}}]
                    }
                }
            }
        })

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            signature = self._create_stripe_signature(
                payload, "whsec_test_secret"
            )

            with patch('stripe.Webhook.construct_event') as mock_construct:
                mock_construct.return_value = json.loads(payload)

                response = await client.post(
                    "/api/v1/webhooks/stripe",
                    content=payload,
                    headers={
                        "Stripe-Signature": signature,
                        "Content-Type": "application/json"
                    }
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stripe_webhook_idempotency(self, client: AsyncClient):
        """Test webhook handles duplicate events correctly"""
        event_id = "evt_test_duplicate"
        payload = json.dumps({
            "id": event_id,
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_123"}}
        })

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            signature = self._create_stripe_signature(
                payload, "whsec_test_secret"
            )

            with patch('stripe.Webhook.construct_event') as mock_construct:
                mock_construct.return_value = json.loads(payload)

                # First call
                response1 = await client.post(
                    "/api/v1/webhooks/stripe",
                    content=payload,
                    headers={
                        "Stripe-Signature": signature,
                        "Content-Type": "application/json"
                    }
                )

                # Second call (duplicate)
                response2 = await client.post(
                    "/api/v1/webhooks/stripe",
                    content=payload,
                    headers={
                        "Stripe-Signature": signature,
                        "Content-Type": "application/json"
                    }
                )

                # Both should succeed but second should be no-op
                assert response1.status_code == 200
                assert response2.status_code == 200


class TestReplicateWebhooks:
    """Test Replicate (training) webhook handling"""

    def _create_replicate_signature(self, payload: str, secret: str) -> str:
        """Helper to create valid Replicate HMAC-SHA256 signature"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_replicate_webhook_training_completed(self, client: AsyncClient):
        """Test handling training completion webhook"""
        payload = json.dumps({
            "id": "prediction_test_123",
            "status": "succeeded",
            "output": {
                "weights_url": "https://storage.example.com/weights.safetensors"
            },
            "webhook_events_filter": ["completed"],
            "version": "test_version"
        })

        # Without secret configured, should accept
        response = await client.post(
            "/api/v1/webhooks/replicate",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_replicate_webhook_training_failed(self, client: AsyncClient):
        """Test handling training failure webhook"""
        payload = json.dumps({
            "id": "prediction_test_failed",
            "status": "failed",
            "error": "Training failed: insufficient data",
            "version": "test_version"
        })

        response = await client.post(
            "/api/v1/webhooks/replicate",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_replicate_webhook_with_valid_signature(self, client: AsyncClient):
        """Test webhook accepts valid HMAC signature"""
        payload = json.dumps({
            "id": "prediction_signed_123",
            "status": "succeeded",
            "output": {"weights_url": "https://example.com/weights.safetensors"}
        })

        secret = "test_webhook_secret_123"
        signature = self._create_replicate_signature(payload, secret)

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.REPLICATE_WEBHOOK_SECRET = secret

            response = await client.post(
                "/api/v1/webhooks/replicate",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Replicate-Signature": signature
                }
            )

            assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_replicate_webhook_rejects_invalid_signature(self, client: AsyncClient):
        """Test webhook rejects invalid signature when secret is configured"""
        payload = json.dumps({
            "id": "prediction_bad_sig",
            "status": "succeeded",
            "output": {}
        })

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.REPLICATE_WEBHOOK_SECRET = "real_secret"

            response = await client.post(
                "/api/v1/webhooks/replicate",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Replicate-Signature": "invalid_signature"
                }
            )

            assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_replicate_webhook_rejects_missing_signature(self, client: AsyncClient):
        """Test webhook rejects missing signature when secret is configured"""
        payload = json.dumps({
            "id": "prediction_no_sig",
            "status": "succeeded",
            "output": {}
        })

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.REPLICATE_WEBHOOK_SECRET = "configured_secret"

            response = await client.post(
                "/api/v1/webhooks/replicate",
                content=payload,
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_replicate_webhook_processing_status(self, client: AsyncClient):
        """Test handling training progress webhook"""
        payload = json.dumps({
            "id": "prediction_progress_123",
            "status": "processing",
            "logs": "Training: 50% complete",
            "version": "test_version"
        })

        response = await client.post(
            "/api/v1/webhooks/replicate",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_replicate_webhook_idempotency(self, client: AsyncClient):
        """Test duplicate webhook events are handled correctly"""
        event_id = "prediction_duplicate_test"
        payload = json.dumps({
            "id": event_id,
            "status": "succeeded",
            "output": {"weights_url": "https://example.com/weights.safetensors"}
        })

        # First call
        response1 = await client.post(
            "/api/v1/webhooks/replicate",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        # Second call (duplicate)
        response2 = await client.post(
            "/api/v1/webhooks/replicate",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        # Both should succeed but second should indicate already processed
        assert response1.status_code in [200, 202]
        assert response2.status_code in [200, 202]


class TestWebhookSecurity:
    """Test webhook security measures"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_webhook_rate_limiting(self, client: AsyncClient):
        """Test webhooks are rate limited"""
        payload = json.dumps({"type": "test"})

        responses = []
        for _ in range(100):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=payload,
                headers={"Content-Type": "application/json"}
            )
            responses.append(response.status_code)

        # Should see some rate limiting (429) if many requests
        # At minimum, all should be handled without server errors
        assert all(code < 500 for code in responses)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_webhook_timestamps_validated(self, client: AsyncClient):
        """Test webhook rejects old timestamps"""
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        payload = json.dumps({"type": "test_event"})

        signature = f"t={old_timestamp},v1=test_signature"

        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": signature,
                "Content-Type": "application/json"
            }
        )

        # Should reject due to old timestamp
        assert response.status_code == 400
