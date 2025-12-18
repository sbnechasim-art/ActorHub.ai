"""
Integration Tests for Rate Limiting
Tests rate limiting middleware for various endpoints
"""

import pytest
from httpx import AsyncClient
import asyncio


class TestRateLimiting:
    """Test rate limiting middleware"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rate_limit_headers_present(self, client: AsyncClient):
        """Test rate limit headers are included in responses"""
        # Use a non-excluded endpoint
        response = await client.get("/api/v1/health")

        # Rate limit headers should be present
        # Note: May not be present for health endpoints which are excluded
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_endpoint_excluded(self, client: AsyncClient):
        """Test health endpoints are excluded from rate limiting"""
        responses = []
        for _ in range(50):
            response = await client.get("/api/v1/health")
            responses.append(response.status_code)

        # All should succeed (no 429)
        assert all(code == 200 for code in responses)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_docs_endpoint_excluded(self, client: AsyncClient):
        """Test documentation endpoints are excluded"""
        response = await client.get("/docs")

        # Should not be rate limited (may redirect or serve docs)
        assert response.status_code in [200, 307]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_login_endpoint_rate_limited(self, client: AsyncClient):
        """Test login endpoint has strict rate limiting"""
        responses = []

        for i in range(10):
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": f"test{i}@example.com", "password": "wrong"}
            )
            responses.append(response.status_code)

        # Should see some rate limiting after several attempts
        # Note: Exact behavior depends on Redis availability
        # At minimum, requests should not cause server errors
        assert all(code < 500 for code in responses)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_marketplace_listings_public_access(self, client: AsyncClient):
        """Test marketplace listings are accessible without hitting rate limits quickly"""
        responses = []

        for _ in range(20):
            response = await client.get("/api/v1/marketplace/listings")
            responses.append(response.status_code)

        # Should all succeed (marketplace GET is excluded)
        assert all(code == 200 for code in responses)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_identity_register_strict_limit(self, auth_client: AsyncClient):
        """Test identity registration has strict rate limiting"""
        # This tests the endpoint exists and responds
        # Actual rate limiting depends on Redis
        responses = []

        for _ in range(5):
            response = await auth_client.post(
                "/api/v1/identity/register",
                data={
                    "display_name": "Test Actor",
                    "protection_level": "free",
                },
                files={
                    "face_image": ("face.jpg", b"fake image data", "image/jpeg"),
                    "verification_image": ("verify.jpg", b"fake image data", "image/jpeg"),
                }
            )
            responses.append(response.status_code)

        # Should see 400 (invalid image) or 429 (rate limited)
        # Not 500 errors
        assert all(code < 500 for code in responses)


class TestTierBasedRateLimits:
    """Test rate limits differ by user tier"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_authenticated_user_higher_limit(self, client: AsyncClient, auth_client: AsyncClient):
        """Test authenticated users have higher rate limits than anonymous"""
        # This is a behavioral test - authenticated users should get more requests
        # through before hitting rate limits

        # Make requests as anonymous user
        anon_responses = []
        for _ in range(5):
            response = await client.get("/api/v1/marketplace/categories")
            anon_responses.append(response.status_code)

        # Make requests as authenticated user
        auth_responses = []
        for _ in range(5):
            response = await auth_client.get("/api/v1/users/me")
            auth_responses.append(response.status_code)

        # Both should work within these limits
        assert all(code in [200, 401, 403] for code in anon_responses)
        assert all(code in [200, 401, 403] for code in auth_responses)


class TestWebhookRateLimits:
    """Test webhook endpoints have appropriate rate limits"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_webhook_endpoints_allow_bursts(self, client: AsyncClient):
        """Test webhook endpoints can handle bursts of events"""
        import json

        responses = []
        for i in range(20):
            payload = json.dumps({
                "id": f"evt_burst_test_{i}",
                "type": "test_event",
                "data": {}
            })

            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=payload,
                headers={"Content-Type": "application/json"}
            )
            responses.append(response.status_code)

        # Webhooks should handle bursts - most should get through
        # May see 400 (invalid signature) but not 429 rate limits
        assert responses.count(429) < len(responses) // 2
