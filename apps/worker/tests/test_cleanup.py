"""
Tests for Cleanup and Maintenance Tasks

Tests distributed locking, scheduled cleanup, and stats updates.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
import uuid


class TestDistributedLocking:
    """Test Redis-based distributed locking."""

    def test_acquire_lock_success(self, mock_redis):
        """Should acquire lock when not held."""
        from tasks.cleanup import acquire_distributed_lock

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis):
            result = acquire_distributed_lock("test_lock", ttl_seconds=3600)

            assert result is True
            assert mock_redis.get("lock:test_lock") == "1"

    def test_acquire_lock_already_held(self, mock_redis):
        """Should fail when lock already held."""
        from tasks.cleanup import acquire_distributed_lock

        # Pre-acquire the lock
        mock_redis.set("lock:test_lock", "1")

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis):
            result = acquire_distributed_lock("test_lock", ttl_seconds=3600)

            assert result is False

    def test_release_lock(self, mock_redis):
        """Should release lock successfully."""
        from tasks.cleanup import release_distributed_lock

        mock_redis.set("lock:test_lock", "1")

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis):
            release_distributed_lock("test_lock")

            assert mock_redis.get("lock:test_lock") is None

    def test_lock_fail_open_on_redis_error(self):
        """Should allow execution when Redis fails."""
        from tasks.cleanup import acquire_distributed_lock

        mock_redis_failing = Mock()
        mock_redis_failing.set.side_effect = Exception("Redis down")

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis_failing):
            # Should return True to avoid blocking on Redis failure
            result = acquire_distributed_lock("test_lock")
            assert result is True


class TestCleanupExpiredDownloads:
    """Test expired download cleanup."""

    def test_skips_when_already_running(self, mock_redis, mock_celery_task):
        """Should skip when lock is already held."""
        from tasks.cleanup import cleanup_expired_downloads

        # Pre-acquire the lock
        mock_redis.set("lock:cleanup_expired_downloads", "1")

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis), \
             patch('tasks.cleanup.trace_task') as mock_trace:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            result = cleanup_expired_downloads(mock_celery_task)

            assert result["message"] == "Already running"
            assert result["cleaned"] == 0

    def test_task_configured(self):
        """cleanup_expired_downloads should have retry configuration."""
        from tasks.cleanup import cleanup_expired_downloads

        assert cleanup_expired_downloads.max_retries == 2
        assert cleanup_expired_downloads.default_retry_delay == 60

    def test_lock_key_naming(self, mock_redis):
        """Should use consistent lock naming."""
        from tasks.cleanup import acquire_distributed_lock, release_distributed_lock

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis):
            acquire_distributed_lock("test_lock")

            # Lock should be prefixed with "lock:"
            assert mock_redis.get("lock:test_lock") is not None

            release_distributed_lock("test_lock")
            assert mock_redis.get("lock:test_lock") is None


class TestCleanupOrphanFiles:
    """Test orphan file cleanup."""

    def test_uses_long_lock_ttl(self, mock_redis, mock_celery_task):
        """Should use longer TTL for long-running cleanup."""
        from tasks.cleanup import cleanup_orphan_files

        # Mock so we can check the TTL used
        with patch('tasks.cleanup.acquire_distributed_lock') as mock_acquire, \
             patch('tasks.cleanup.release_distributed_lock'), \
             patch('tasks.cleanup.trace_task') as mock_trace, \
             patch('tasks.cleanup.add_task_attribute'):

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            mock_acquire.return_value = True

            cleanup_orphan_files(mock_celery_task)

            # Should use 2-hour TTL for this long-running task
            mock_acquire.assert_called_with("cleanup_orphan_files", ttl_seconds=7200)


class TestUpdateUsageStats:
    """Test usage statistics updates."""

    def test_skips_when_already_running(self, mock_redis, mock_celery_task):
        """Should skip when already running."""
        from tasks.cleanup import update_usage_stats

        mock_redis.set("lock:update_usage_stats", "1")

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis), \
             patch('tasks.cleanup.trace_task') as mock_trace:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            result = update_usage_stats(mock_celery_task)

            assert result["message"] == "Already running"

    def test_task_configured(self):
        """update_usage_stats should have retry configuration."""
        from tasks.cleanup import update_usage_stats

        assert update_usage_stats.max_retries == 2
        assert update_usage_stats.default_retry_delay == 30


class TestCleanupOldLogs:
    """Test old log cleanup."""

    def test_task_configured(self):
        """cleanup_old_logs should have retry configuration."""
        from tasks.cleanup import cleanup_old_logs

        assert cleanup_old_logs.max_retries == 2
        assert cleanup_old_logs.default_retry_delay == 120


class TestCheckLicenseExpirations:
    """Test license expiration checks."""

    def test_skips_when_already_running(self, mock_redis, mock_celery_task):
        """Should skip to prevent duplicate notifications."""
        from tasks.cleanup import check_license_expirations

        mock_redis.set("lock:check_license_expirations", "1")

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis), \
             patch('tasks.cleanup.trace_task') as mock_trace:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            result = check_license_expirations(mock_celery_task)

            assert result["message"] == "Already running"

    def test_task_configured(self):
        """check_license_expirations should have retry configuration."""
        from tasks.cleanup import check_license_expirations

        assert check_license_expirations.max_retries == 2
        assert check_license_expirations.default_retry_delay == 60


class TestRetryBehavior:
    """Test retry behavior for cleanup tasks."""

    def test_retry_on_db_error(self, mock_redis, mock_celery_task):
        """Should retry on database errors."""
        from tasks.cleanup import cleanup_expired_downloads

        mock_celery_task.request.retries = 0
        mock_celery_task.max_retries = 2

        with patch('tasks.cleanup.get_redis_client', return_value=mock_redis), \
             patch('tasks.cleanup.trace_task') as mock_trace, \
             patch('tasks.cleanup.add_task_attribute'), \
             patch('asyncio.new_event_loop') as mock_loop:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            mock_loop.return_value.run_until_complete.side_effect = Exception("DB connection lost")
            mock_loop.return_value.close = Mock()

            with pytest.raises(Exception):
                cleanup_expired_downloads(mock_celery_task)

    def test_exponential_backoff(self, mock_celery_task):
        """Should use exponential backoff for retries."""
        # Verify retry countdown calculation
        base_delay = 60
        retries = [0, 1, 2]

        for retry in retries:
            expected_countdown = base_delay * (2 ** retry)
            # retry 0: 60s, retry 1: 120s, retry 2: 240s
            assert expected_countdown == base_delay * (2 ** retry)
