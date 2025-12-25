"""
Tests for Notification Tasks

Tests email, push, and webhook notifications.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
import uuid


class TestSendGridIntegration:
    """Test SendGrid email integration."""

    def test_get_sendgrid_client_caches(self):
        """Should cache SendGrid client instance."""
        from tasks import notifications

        # Reset the cached client
        notifications._sendgrid_client = None

        with patch.dict('sys.modules', {'sendgrid': Mock()}):
            with patch('tasks.notifications.settings') as mock_settings:
                mock_settings.SENDGRID_API_KEY = "SG.test_key"

                client1 = notifications.get_sendgrid_client()
                client2 = notifications.get_sendgrid_client()

                # Should return same instance (cached)
                assert client1 is client2

        # Reset for other tests
        notifications._sendgrid_client = None

    def test_no_sendgrid_key_logs_only(self, caplog):
        """Should log emails when no SendGrid key configured."""
        from tasks.notifications import _send_email_sync

        with patch('tasks.notifications.get_sendgrid_client', return_value=None):
            result = _send_email_sync(
                to="test@example.com",
                subject="Test Subject",
                body="Test body"
            )

            # Should return True (logged successfully)
            assert result is True


class TestSendEmail:
    """Test send_email task."""

    def test_send_email_success(self, mock_sendgrid):
        """Should send email successfully via SendGrid."""
        from tasks.notifications import _send_email_sync

        # Test the sync function directly
        result = _send_email_sync(
            to="test@example.com",
            subject="Test Subject",
            body="Test body content"
        )

        assert result is True
        assert len(mock_sendgrid.sent_emails) == 1

    def test_send_email_with_html(self, mock_sendgrid):
        """Should send email with HTML content."""
        from tasks.notifications import _send_email_sync

        result = _send_email_sync(
            to="test@example.com",
            subject="Test Subject",
            body="Plain text fallback",
            html="<h1>HTML Content</h1>"
        )

        assert result is True

    def test_send_email_task_configured(self):
        """send_email task should have retry configuration."""
        from tasks.notifications import send_email

        assert send_email.max_retries == 3
        assert send_email.default_retry_delay == 30

    def test_send_email_retry_on_failure(self, mock_celery_task):
        """Should retry on SendGrid failure."""
        from tasks.notifications import send_email

        mock_celery_task.request.retries = 0
        mock_celery_task.max_retries = 3

        with patch('tasks.notifications.trace_task') as mock_trace, \
             patch('tasks.notifications.add_task_attribute'), \
             patch('tasks.notifications._send_email_sync', return_value=False):

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            with pytest.raises(Exception):
                send_email(
                    mock_celery_task,
                    to="test@example.com",
                    subject="Test",
                    body="Test"
                )


class TestSendWebhook:
    """Test webhook delivery."""

    @pytest.mark.asyncio
    async def test_webhook_success(self, mock_http_client):
        """Should deliver webhook successfully."""
        from tasks.notifications import _send_webhook_async

        mock_http_client.responses["https://example.com/webhook"] = Mock(
            status_code=200
        )

        with patch('httpx.AsyncClient', return_value=mock_http_client):
            result = await _send_webhook_async(
                url="https://example.com/webhook",
                payload={"event": "test", "data": {"id": "123"}}
            )

            assert result["success"] is True
            assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_webhook_failure(self, mock_http_client):
        """Should report failure for non-2xx responses."""
        from tasks.notifications import _send_webhook_async

        mock_http_client.responses["https://example.com/webhook"] = Mock(
            status_code=500
        )

        with patch('httpx.AsyncClient', return_value=mock_http_client):
            result = await _send_webhook_async(
                url="https://example.com/webhook",
                payload={"event": "test"}
            )

            assert result["success"] is False

    def test_webhook_retry_with_exponential_backoff(self, mock_celery_task):
        """Should retry webhooks with exponential backoff."""
        from tasks.notifications import send_webhook

        mock_celery_task.request.retries = 0
        mock_celery_task.max_retries = 5

        with patch('tasks.notifications.trace_task') as mock_trace, \
             patch('tasks.notifications.add_task_attribute'), \
             patch('asyncio.new_event_loop') as mock_loop:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            # Mock the async result to be a failure
            mock_loop.return_value.run_until_complete.return_value = {
                "success": False,
                "error": "Connection timeout"
            }
            mock_loop.return_value.close = Mock()

            with pytest.raises(Exception):
                send_webhook(
                    mock_celery_task,
                    url="https://example.com/webhook",
                    payload={"event": "test"}
                )


class TestNotifyTrainingComplete:
    """Test training completion notifications."""

    def test_sends_email_and_push(self, mock_celery_task):
        """Should send both email and push notification."""
        from tasks.notifications import notify_training_complete

        with patch('tasks.notifications.trace_task') as mock_trace, \
             patch('tasks.notifications.get_trace_headers_for_subtask', return_value={}), \
             patch('tasks.notifications.send_email') as mock_email, \
             patch('tasks.notifications.send_push_notification') as mock_push:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            mock_email.delay = Mock()
            mock_push.delay = Mock()

            result = notify_training_complete(
                user_id=str(uuid.uuid4()),
                actor_pack_id=str(uuid.uuid4()),
                quality_score=92.5
            )

            assert result["success"] is True
            mock_email.delay.assert_called_once()
            mock_push.delay.assert_called_once()


class TestNotifyLicensePurchased:
    """Test license purchase notifications."""

    def test_notifies_seller(self):
        """Should notify seller of license purchase."""
        from tasks.notifications import notify_license_purchased

        with patch('tasks.notifications.trace_task') as mock_trace, \
             patch('tasks.notifications.get_trace_headers_for_subtask', return_value={}), \
             patch('tasks.notifications.send_email') as mock_email:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            mock_email.delay = Mock()

            result = notify_license_purchased(
                seller_id=str(uuid.uuid4()),
                buyer_id=str(uuid.uuid4()),
                license_id=str(uuid.uuid4()),
                amount=49.99
            )

            assert result["success"] is True
            mock_email.delay.assert_called_once()


class TestNotifyUnauthorizedUse:
    """Test unauthorized use detection notifications."""

    def test_logs_warning(self, caplog):
        """Should log unauthorized use detection."""
        from tasks.notifications import notify_unauthorized_use

        with patch('tasks.notifications.trace_task') as mock_trace:
            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            result = notify_unauthorized_use(
                identity_id=str(uuid.uuid4()),
                platform="youtube.com",
                image_url="https://example.com/image.jpg"
            )

            assert result["success"] is True
            assert result["platform"] == "youtube.com"


class TestPushNotifications:
    """Test push notification handling."""

    def test_push_notification_task_configured(self):
        """send_push_notification task should have retry configuration."""
        from tasks.notifications import send_push_notification

        assert send_push_notification.max_retries == 2
        assert send_push_notification.default_retry_delay == 15
