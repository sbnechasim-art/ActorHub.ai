"""
Integration Tests for Analytics Endpoints
Tests analytics dashboard, usage, and revenue endpoints
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from uuid import uuid4


class TestAnalyticsDashboard:
    """Test analytics dashboard endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_dashboard_authenticated(self, auth_client: AsyncClient):
        """Test getting dashboard with valid auth"""
        response = await auth_client.get("/api/v1/analytics/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "usage" in data
        assert "revenue" in data
        assert "top_identities" in data
        assert "usage_trend" in data
        assert "revenue_trend" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_dashboard_unauthenticated(self, client: AsyncClient):
        """Test dashboard requires authentication"""
        response = await client.get("/api/v1/analytics/dashboard")

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_dashboard_with_days_param(self, auth_client: AsyncClient):
        """Test dashboard with custom days parameter"""
        response = await auth_client.get("/api/v1/analytics/dashboard?days=7")

        assert response.status_code == 200
        data = response.json()
        # Usage should have period matching 7 days
        assert data["usage"]["period_start"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_dashboard_invalid_days(self, auth_client: AsyncClient):
        """Test dashboard with invalid days parameter"""
        response = await auth_client.get("/api/v1/analytics/dashboard?days=0")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_dashboard_days_too_large(self, auth_client: AsyncClient):
        """Test dashboard with days > 365"""
        response = await auth_client.get("/api/v1/analytics/dashboard?days=400")

        assert response.status_code == 422


class TestUsageAnalytics:
    """Test usage analytics endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_usage_analytics(self, auth_client: AsyncClient):
        """Test getting usage analytics"""
        response = await auth_client.get("/api/v1/analytics/usage")

        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "by_action" in data
        assert "totals" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_usage_with_identity_filter(
        self, auth_client: AsyncClient, test_identity
    ):
        """Test usage analytics filtered by identity"""
        response = await auth_client.get(
            f"/api/v1/analytics/usage?identity_id={test_identity.id}"
        )

        assert response.status_code == 200


class TestRevenueAnalytics:
    """Test revenue analytics endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_revenue_analytics(self, auth_client: AsyncClient):
        """Test getting revenue analytics"""
        response = await auth_client.get("/api/v1/analytics/revenue")

        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "daily" in data
        assert "by_identity" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_revenue_daily_data_format(self, auth_client: AsyncClient):
        """Test revenue daily data has correct format"""
        response = await auth_client.get("/api/v1/analytics/revenue?days=30")

        assert response.status_code == 200
        data = response.json()

        for day in data.get("daily", []):
            assert "date" in day
            assert "revenue" in day
            assert "transactions" in day


class TestIdentityAnalytics:
    """Test identity-specific analytics endpoint"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_identity_analytics(
        self, auth_client: AsyncClient, test_identity
    ):
        """Test getting analytics for specific identity"""
        response = await auth_client.get(
            f"/api/v1/analytics/identity/{test_identity.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "identity_id" in data
        assert "identity_name" in data
        assert "usage_by_action" in data
        assert "daily_usage" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_identity_analytics_not_found(self, auth_client: AsyncClient):
        """Test analytics for non-existent identity"""
        fake_id = str(uuid4())
        response = await auth_client.get(f"/api/v1/analytics/identity/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_identity_analytics_forbidden(
        self, auth_client: AsyncClient, other_user_identity
    ):
        """Test cannot access other user's identity analytics"""
        response = await auth_client.get(
            f"/api/v1/analytics/identity/{other_user_identity.id}"
        )

        assert response.status_code == 403


class TestPlatformAnalytics:
    """Test platform-wide analytics (admin only)"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_platform_analytics_admin(self, admin_client: AsyncClient):
        """Test admin can access platform analytics"""
        response = await admin_client.get("/api/v1/analytics/admin/platform")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "identities" in data
        assert "revenue" in data
        assert "api_calls" in data
        assert "daily_active_users" in data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_platform_analytics_non_admin(self, auth_client: AsyncClient):
        """Test non-admin cannot access platform analytics"""
        response = await auth_client.get("/api/v1/analytics/admin/platform")

        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_platform_analytics_unauthenticated(self, client: AsyncClient):
        """Test unauthenticated cannot access platform analytics"""
        response = await client.get("/api/v1/analytics/admin/platform")

        assert response.status_code == 401
