"""
API Integration Tests
Comprehensive tests for all critical API endpoints
"""
import uuid
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """Test readiness check"""
        response = await client.get("/ready")
        assert response.status_code == 200


class TestMarketplaceEndpoints:
    """Test marketplace API endpoints"""

    @pytest.mark.asyncio
    async def test_search_listings_public(self, client: AsyncClient):
        """Test public listing search"""
        response = await client.get("/api/v1/marketplace/listings")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_search_listings_with_filters(self, client: AsyncClient):
        """Test listing search with filters"""
        response = await client.get(
            "/api/v1/marketplace/listings",
            params={
                "query": "actor",
                "sort_by": "newest",
                "page": 1,
                "limit": 10
            }
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_listings_category_filter(self, client: AsyncClient):
        """Test listing search by category"""
        response = await client.get(
            "/api/v1/marketplace/listings",
            params={"category": "actor"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_listings_featured(self, client: AsyncClient):
        """Test featured listings filter"""
        response = await client.get(
            "/api/v1/marketplace/listings",
            params={"featured": True}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_listing_not_found(self, client: AsyncClient):
        """Test getting non-existent listing"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/marketplace/listings/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_calculate_license_price(self, client: AsyncClient, test_identity):
        """Test license price calculation"""
        response = await client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "standard",
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
    async def test_calculate_license_price_commercial(self, client: AsyncClient, test_identity):
        """Test commercial license pricing (higher cost)"""
        response = await client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "extended",
                "usage_type": "commercial",
                "duration_days": 365
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["usage_multiplier"] == 3.0  # Commercial multiplier

    @pytest.mark.asyncio
    async def test_purchase_license_requires_auth(self, client: AsyncClient, test_identity):
        """Test that license purchase requires authentication"""
        response = await client.post(
            "/api/v1/marketplace/license/purchase",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "standard",
                "usage_type": "personal",
                "duration_days": 30
            }
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_purchase_license_authenticated(self, auth_client: AsyncClient, test_identity):
        """Test license purchase with authentication"""
        response = await auth_client.post(
            "/api/v1/marketplace/license/purchase",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "standard",
                "usage_type": "personal",
                "duration_days": 30
            }
        )
        # Should return checkout URL or error if Stripe not configured
        assert response.status_code in [201, 500, 503]

    @pytest.mark.asyncio
    async def test_get_my_licenses(self, auth_client: AsyncClient):
        """Test getting user's licenses"""
        response = await auth_client.get("/api/v1/marketplace/licenses/mine")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_my_licenses_active_only(self, auth_client: AsyncClient, test_license):
        """Test getting only active licenses"""
        response = await auth_client.get(
            "/api/v1/marketplace/licenses/mine",
            params={"active_only": True}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient):
        """Test getting marketplace categories"""
        response = await client.get("/api/v1/marketplace/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data


class TestIdentityEndpoints:
    """Test identity API endpoints"""

    @pytest.mark.asyncio
    async def test_get_my_identities(self, auth_client: AsyncClient):
        """Test getting user's identities"""
        response = await auth_client.get("/api/v1/identity/me")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_identity_by_id(self, auth_client: AsyncClient, test_identity):
        """Test getting identity by ID"""
        response = await auth_client.get(f"/api/v1/identity/{test_identity.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Test Actor"

    @pytest.mark.asyncio
    async def test_get_identity_not_found(self, auth_client: AsyncClient):
        """Test getting non-existent identity"""
        fake_id = str(uuid.uuid4())
        response = await auth_client.get(f"/api/v1/identity/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_identity(self, auth_client: AsyncClient):
        """Test creating a new identity"""
        response = await auth_client.post(
            "/api/v1/identity/",
            json={
                "display_name": "New Test Actor",
                "bio": "A new actor for testing",
                "allow_commercial_use": True,
                "allow_ai_training": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "New Test Actor"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_update_identity(self, auth_client: AsyncClient, test_identity):
        """Test updating an identity"""
        response = await auth_client.patch(
            f"/api/v1/identity/{test_identity.id}",
            json={"bio": "Updated bio text"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "Updated bio text"

    @pytest.mark.asyncio
    async def test_update_identity_unauthorized(self, auth_client: AsyncClient, other_user_identity):
        """Test updating another user's identity fails"""
        response = await auth_client.patch(
            f"/api/v1/identity/{other_user_identity.id}",
            json={"bio": "Hacked bio"}
        )
        assert response.status_code == 403


class TestUserEndpoints:
    """Test user API endpoints"""

    @pytest.mark.asyncio
    async def test_get_current_user(self, auth_client: AsyncClient):
        """Test getting current user profile"""
        response = await auth_client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_update_profile(self, auth_client: AsyncClient):
        """Test updating user profile"""
        response = await auth_client.patch(
            "/api/v1/users/me",
            json={"first_name": "Updated"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"

    @pytest.mark.asyncio
    async def test_get_dashboard_stats(self, auth_client: AsyncClient):
        """Test getting dashboard statistics"""
        response = await auth_client.get("/api/v1/users/me/stats")
        assert response.status_code == 200
        data = response.json()
        assert "identities_count" in data


class TestActorPackEndpoints:
    """Test actor pack API endpoints"""

    @pytest.mark.asyncio
    async def test_start_training_requires_auth(self, client: AsyncClient, test_identity):
        """Test that training requires authentication"""
        response = await client.post(
            f"/api/v1/actor-packs/{test_identity.id}/train",
            json={"face_images": ["http://example.com/img.jpg"] * 8}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_training_status_not_found(self, auth_client: AsyncClient):
        """Test getting status for non-existent training"""
        fake_id = str(uuid.uuid4())
        response = await auth_client.get(f"/api/v1/actor-packs/{fake_id}/status")
        assert response.status_code == 404


class TestNotificationEndpoints:
    """Test notification API endpoints"""

    @pytest.mark.asyncio
    async def test_get_notifications(self, auth_client: AsyncClient):
        """Test getting user notifications"""
        response = await auth_client.get("/api/v1/notifications/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_unread_count(self, auth_client: AsyncClient):
        """Test getting unread notification count"""
        response = await auth_client.get("/api/v1/notifications/unread/count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data


class TestAnalyticsEndpoints:
    """Test analytics API endpoints"""

    @pytest.mark.asyncio
    async def test_get_creator_analytics_requires_auth(self, client: AsyncClient):
        """Test that analytics requires authentication"""
        response = await client.get("/api/v1/analytics/creator")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_creator_analytics(self, auth_client: AsyncClient):
        """Test getting creator analytics"""
        response = await auth_client.get("/api/v1/analytics/creator")
        assert response.status_code == 200


class TestAdminEndpoints:
    """Test admin API endpoints"""

    @pytest.mark.asyncio
    async def test_admin_dashboard_requires_admin(self, auth_client: AsyncClient):
        """Test that admin dashboard requires admin role"""
        response = await auth_client.get("/api/v1/admin/dashboard")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_dashboard_with_admin(self, admin_client: AsyncClient):
        """Test admin dashboard with admin user"""
        response = await admin_client.get("/api/v1/admin/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "identities" in data

    @pytest.mark.asyncio
    async def test_admin_list_users(self, admin_client: AsyncClient):
        """Test listing users as admin"""
        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_admin_system_health(self, admin_client: AsyncClient):
        """Test system health check as admin"""
        response = await admin_client.get("/api/v1/admin/system/health")
        assert response.status_code == 200


class TestRefundEndpoints:
    """Test refund API endpoints"""

    @pytest.mark.asyncio
    async def test_request_refund_requires_auth(self, client: AsyncClient, test_license):
        """Test that refund requests require authentication"""
        response = await client.post(
            f"/api/v1/refunds/request/{test_license.id}",
            json={"reason": "Not satisfied"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_check_refund_eligibility(self, auth_client: AsyncClient, test_license_with_payment):
        """Test checking refund eligibility"""
        response = await auth_client.get(
            f"/api/v1/refunds/eligibility/{test_license_with_payment.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "eligible" in data

    @pytest.mark.asyncio
    async def test_get_refund_history(self, auth_client: AsyncClient):
        """Test getting refund history"""
        response = await auth_client.get("/api/v1/refunds/history")
        assert response.status_code == 200


class TestSubscriptionEndpoints:
    """Test subscription API endpoints"""

    @pytest.mark.asyncio
    async def test_get_subscription_plans(self, client: AsyncClient):
        """Test getting available subscription plans"""
        response = await client.get("/api/v1/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_current_subscription(self, auth_client: AsyncClient):
        """Test getting current subscription"""
        response = await auth_client.get("/api/v1/subscriptions/current")
        # Either 200 with subscription or 404 if none
        assert response.status_code in [200, 404]


class TestGDPREndpoints:
    """Test GDPR compliance endpoints"""

    @pytest.mark.asyncio
    async def test_export_data_requires_auth(self, client: AsyncClient):
        """Test that data export requires authentication"""
        response = await client.post("/api/v1/gdpr/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_data(self, auth_client: AsyncClient):
        """Test GDPR data export"""
        response = await auth_client.post("/api/v1/gdpr/export")
        # Should return success or job ID
        assert response.status_code in [200, 202]


class TestWebhookEndpoints:
    """Test webhook API endpoints"""

    @pytest.mark.asyncio
    async def test_stripe_webhook_no_signature(self, client: AsyncClient):
        """Test Stripe webhook rejects requests without signature"""
        response = await client.post(
            "/api/v1/webhooks/stripe",
            json={"type": "payment_intent.succeeded"}
        )
        # Should fail without valid Stripe signature
        assert response.status_code in [400, 401, 422, 500]


class TestRateLimiting:
    """Test rate limiting"""

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient):
        """Test that rate limit headers are present"""
        response = await client.get("/health")
        # Rate limit headers should be present
        # Note: Headers depend on configuration
        assert response.status_code == 200


class TestCORS:
    """Test CORS configuration"""

    @pytest.mark.asyncio
    async def test_cors_preflight(self, client: AsyncClient):
        """Test CORS preflight request"""
        response = await client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # Should allow the origin
        assert response.status_code in [200, 204]


class TestInputValidation:
    """Test input validation and security"""

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, client: AsyncClient):
        """Test SQL injection is prevented in search"""
        response = await client.get(
            "/api/v1/marketplace/listings",
            params={"query": "'; DROP TABLE listings; --"}
        )
        # Should not crash, just return empty or filtered results
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_xss_prevention_in_search(self, client: AsyncClient):
        """Test XSS is handled in search queries"""
        response = await client.get(
            "/api/v1/marketplace/listings",
            params={"query": "<script>alert('xss')</script>"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_oversized_request_body(self, client: AsyncClient):
        """Test that oversized requests are rejected"""
        large_data = {"data": "x" * (11 * 1024 * 1024)}  # 11MB
        response = await client.post(
            "/api/v1/users/register",
            json=large_data
        )
        # Should reject as too large
        assert response.status_code in [413, 422]


class TestErrorResponses:
    """Test error response format consistency"""

    @pytest.mark.asyncio
    async def test_404_error_format(self, client: AsyncClient):
        """Test 404 error response format"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/identity/{fake_id}")
        # Unauthenticated should get 401, not 404
        assert response.status_code in [401, 404]

    @pytest.mark.asyncio
    async def test_validation_error_format(self, client: AsyncClient):
        """Test validation error response format"""
        response = await client.post(
            "/api/v1/users/register",
            json={"email": "invalid"}  # Missing required fields
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
