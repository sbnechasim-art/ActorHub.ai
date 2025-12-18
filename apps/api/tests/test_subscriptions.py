"""
Tests for Subscription Endpoints
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock

from app.models.notifications import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import User


@pytest.fixture
async def active_subscription(db_session: AsyncSession, test_user: User):
    """Create an active subscription for test user"""
    subscription = Subscription(
        user_id=test_user.id,
        plan=SubscriptionPlan.PRO_MONTHLY,
        status=SubscriptionStatus.ACTIVE,
        amount=29.0,
        currency="USD",
        interval="month",
        current_period_start=datetime.utcnow() - timedelta(days=15),
        current_period_end=datetime.utcnow() + timedelta(days=15),
        stripe_subscription_id="sub_test123",
        identities_limit=25,
        api_calls_limit=10000,
        storage_limit_mb=1000,
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription


class TestSubscriptionEndpoints:
    """Test subscription API endpoints"""

    @pytest.mark.asyncio
    async def test_get_current_subscription_none(self, auth_client: AsyncClient):
        """Test getting current subscription when none exists"""
        response = await auth_client.get("/api/v1/subscriptions/current")
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_get_current_subscription(
        self, auth_client: AsyncClient, active_subscription
    ):
        """Test getting current subscription"""
        response = await auth_client.get("/api/v1/subscriptions/current")
        assert response.status_code == 200

        data = response.json()
        assert data["plan"] == "PRO_MONTHLY"
        assert data["status"] == "ACTIVE"
        assert data["amount"] == 29.0
        assert data["identities_limit"] == 25

    @pytest.mark.asyncio
    async def test_get_available_plans(self, auth_client: AsyncClient):
        """Test getting available subscription plans"""
        response = await auth_client.get("/api/v1/subscriptions/plans")
        assert response.status_code == 200

        data = response.json()
        assert "plans" in data
        plans = data["plans"]
        assert len(plans) >= 3  # FREE, PRO, ENTERPRISE

        # Verify plan structure
        for plan in plans:
            assert "id" in plan
            assert "name" in plan
            assert "price_monthly" in plan
            assert "features" in plan
            assert "identities_limit" in plan

    @pytest.mark.asyncio
    async def test_get_usage(
        self, auth_client: AsyncClient, active_subscription
    ):
        """Test getting usage statistics"""
        response = await auth_client.get("/api/v1/subscriptions/usage")
        assert response.status_code == 200

        data = response.json()
        assert "usage" in data
        assert "limits" in data
        assert "identities" in data["usage"]
        assert "api_calls" in data["usage"]

    @pytest.mark.asyncio
    async def test_get_usage_free_tier(self, auth_client: AsyncClient):
        """Test getting usage for free tier"""
        response = await auth_client.get("/api/v1/subscriptions/usage")
        assert response.status_code == 200

        data = response.json()
        # Free tier limits
        assert data["limits"]["identities"] == 3
        assert data["limits"]["api_calls"] == 100

    @pytest.mark.asyncio
    async def test_cancel_subscription(
        self, auth_client: AsyncClient, active_subscription
    ):
        """Test canceling a subscription"""
        with patch("stripe.Subscription.modify") as mock_modify:
            mock_modify.return_value = MagicMock()

            response = await auth_client.post("/api/v1/subscriptions/cancel")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "period_end" in data

    @pytest.mark.asyncio
    async def test_cancel_no_subscription(self, auth_client: AsyncClient):
        """Test canceling when no subscription exists"""
        response = await auth_client.post("/api/v1/subscriptions/cancel")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_checkout_free_plan_error(self, auth_client: AsyncClient):
        """Test that free plan checkout is rejected"""
        response = await auth_client.post(
            "/api/v1/subscriptions/checkout",
            json={"plan": "FREE", "interval": "month"}
        )
        assert response.status_code == 400
        assert "free plan" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_create_checkout_session(
        self, auth_client: AsyncClient, test_user: User
    ):
        """Test creating a checkout session"""
        with patch("stripe.Customer.create") as mock_customer, \
             patch("stripe.checkout.Session.create") as mock_session:
            mock_customer.return_value = MagicMock(id="cus_test123")
            mock_session.return_value = MagicMock(
                url="https://checkout.stripe.com/test",
                id="cs_test123"
            )

            response = await auth_client.post(
                "/api/v1/subscriptions/checkout",
                json={
                    "plan": "PRO_MONTHLY",
                    "interval": "month",
                }
            )
            assert response.status_code == 200

            data = response.json()
            assert "checkout_url" in data
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected"""
        response = await client.get("/api/v1/subscriptions/current")
        assert response.status_code == 401


class TestSubscriptionReactivation:
    """Test subscription reactivation"""

    @pytest.fixture
    async def canceled_subscription(
        self, db_session: AsyncSession, test_user: User
    ):
        """Create a canceled subscription"""
        subscription = Subscription(
            user_id=test_user.id,
            plan=SubscriptionPlan.PRO_MONTHLY,
            status=SubscriptionStatus.ACTIVE,
            cancel_at_period_end=True,
            amount=29.0,
            stripe_subscription_id="sub_canceled123",
            current_period_end=datetime.utcnow() + timedelta(days=10),
        )
        db_session.add(subscription)
        await db_session.commit()
        return subscription

    @pytest.mark.asyncio
    async def test_reactivate_subscription(
        self, auth_client: AsyncClient, canceled_subscription
    ):
        """Test reactivating a canceled subscription"""
        with patch("stripe.Subscription.modify") as mock_modify:
            mock_modify.return_value = MagicMock()

            response = await auth_client.post("/api/v1/subscriptions/reactivate")
            assert response.status_code == 200
            assert response.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_reactivate_no_canceled_subscription(
        self, auth_client: AsyncClient
    ):
        """Test reactivating when no canceled subscription"""
        response = await auth_client.post("/api/v1/subscriptions/reactivate")
        assert response.status_code == 404
