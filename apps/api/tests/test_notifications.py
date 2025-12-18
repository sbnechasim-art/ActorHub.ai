"""
Tests for Notification Endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification, NotificationType, NotificationChannel
from app.models.user import User


@pytest.fixture
async def test_notifications(db_session: AsyncSession, test_user: User):
    """Create test notifications"""
    notifications = [
        Notification(
            user_id=test_user.id,
            type=NotificationType.SYSTEM,
            title="Welcome",
            message="Welcome to ActorHub.ai!",
            channel=NotificationChannel.IN_APP,
            is_read=False,
        ),
        Notification(
            user_id=test_user.id,
            type=NotificationType.BILLING,
            title="Payment Received",
            message="Your payment has been processed.",
            channel=NotificationChannel.EMAIL,
            is_read=True,
        ),
        Notification(
            user_id=test_user.id,
            type=NotificationType.SECURITY,
            title="New Login",
            message="New login from a new device.",
            channel=NotificationChannel.IN_APP,
            is_read=False,
        ),
    ]
    for n in notifications:
        db_session.add(n)
    await db_session.commit()
    return notifications


class TestNotificationEndpoints:
    """Test notification API endpoints"""

    @pytest.mark.asyncio
    async def test_get_notifications(
        self, auth_client: AsyncClient, test_notifications
    ):
        """Test getting user notifications"""
        response = await auth_client.get("/api/v1/notifications")
        assert response.status_code == 200

        data = response.json()
        assert "notifications" in data
        assert "total" in data
        assert "unread_count" in data
        assert len(data["notifications"]) == 3
        assert data["unread_count"] == 2

    @pytest.mark.asyncio
    async def test_get_notifications_filtered_by_read(
        self, auth_client: AsyncClient, test_notifications
    ):
        """Test filtering notifications by read status"""
        response = await auth_client.get("/api/v1/notifications?is_read=false")
        assert response.status_code == 200

        data = response.json()
        assert len(data["notifications"]) == 2
        for n in data["notifications"]:
            assert n["is_read"] is False

    @pytest.mark.asyncio
    async def test_get_notifications_filtered_by_type(
        self, auth_client: AsyncClient, test_notifications
    ):
        """Test filtering notifications by type"""
        response = await auth_client.get("/api/v1/notifications?type=SECURITY")
        assert response.status_code == 200

        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["type"] == "SECURITY"

    @pytest.mark.asyncio
    async def test_get_unread_count(
        self, auth_client: AsyncClient, test_notifications
    ):
        """Test getting unread notification count"""
        response = await auth_client.get("/api/v1/notifications/unread-count")
        assert response.status_code == 200

        data = response.json()
        assert data["unread_count"] == 2

    @pytest.mark.asyncio
    async def test_mark_notification_as_read(
        self, auth_client: AsyncClient, test_notifications
    ):
        """Test marking a notification as read"""
        notification = test_notifications[0]
        response = await auth_client.post(
            f"/api/v1/notifications/{notification.id}/read"
        )
        assert response.status_code == 200

        # Verify unread count decreased
        response = await auth_client.get("/api/v1/notifications/unread-count")
        assert response.json()["unread_count"] == 1

    @pytest.mark.asyncio
    async def test_mark_all_as_read(
        self, auth_client: AsyncClient, test_notifications
    ):
        """Test marking all notifications as read"""
        response = await auth_client.post("/api/v1/notifications/read-all")
        assert response.status_code == 200

        # Verify all are read
        response = await auth_client.get("/api/v1/notifications/unread-count")
        assert response.json()["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_notification(
        self, auth_client: AsyncClient, test_notifications
    ):
        """Test deleting a notification"""
        notification = test_notifications[0]
        response = await auth_client.delete(
            f"/api/v1/notifications/{notification.id}"
        )
        assert response.status_code == 200

        # Verify notification is gone
        response = await auth_client.get("/api/v1/notifications")
        assert len(response.json()["notifications"]) == 2

    @pytest.mark.asyncio
    async def test_get_notification_preferences(self, auth_client: AsyncClient):
        """Test getting notification preferences"""
        response = await auth_client.get("/api/v1/notifications/preferences")
        assert response.status_code == 200

        data = response.json()
        assert "email_security" in data
        assert "push_enabled" in data

    @pytest.mark.asyncio
    async def test_update_notification_preferences(self, auth_client: AsyncClient):
        """Test updating notification preferences"""
        response = await auth_client.put(
            "/api/v1/notifications/preferences",
            json={
                "email_security": True,
                "email_billing": False,
                "email_marketing": True,
                "push_enabled": False,
                "sms_enabled": True,
            }
        )
        assert response.status_code == 200

        # Verify preferences updated
        response = await auth_client.get("/api/v1/notifications/preferences")
        data = response.json()
        assert data["email_marketing"] is True
        assert data["push_enabled"] is False

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected"""
        response = await client.get("/api/v1/notifications")
        assert response.status_code == 401
