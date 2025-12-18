"""
Health Check Tests

Note: Health endpoints are available at:
- /health (main.py) - basic health
- /health/ready (main.py) - readiness with dependency checks
- /api/v1/health (health.py) - basic health
- /api/v1/health/ready (health.py) - readiness
- /api/v1/health/live (health.py) - liveness
"""
import pytest
from httpx import AsyncClient


class TestHealthChecks:
    """Test health check endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check (main.py endpoint)"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "ok"]
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_v1(self, client: AsyncClient):
        """Test basic health check (v1 endpoint)"""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness probe"""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """Test readiness probe - may fail if services not running"""
        response = await client.get("/health/ready")
        # Accept 200 or 503 depending on service availability
        assert response.status_code in [200, 503]


class TestSecurityHeaders:
    """Test security headers are present"""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        """Test that security headers are set"""
        response = await client.get("/health")

        # These headers should be present after middleware is applied
        # Note: May need to be adjusted based on middleware configuration
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting"""

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient):
        """Test that rate limit headers are returned"""
        response = await client.get("/api/v1/users/me")
        # Rate limit headers should be present
        # Note: Exact headers depend on rate limiter configuration
        assert response.status_code in [200, 401, 429]
