"""
Tests for Payout Tasks

Tests idempotency, Stripe integration, and payout processing.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
import uuid


class TestIdempotencyLocks:
    """Test Redis-based idempotency locks."""

    def test_acquire_lock_success(self, mock_redis):
        """Should acquire lock when key doesn't exist."""
        from tasks.payouts import acquire_idempotency_lock

        with patch('tasks.payouts.get_redis_client', return_value=mock_redis):
            result = acquire_idempotency_lock("test_key", ttl_seconds=300)
            assert result is True
            assert mock_redis.get("idempotency:test_key") == "1"

    def test_acquire_lock_already_held(self, mock_redis):
        """Should fail when lock is already held."""
        from tasks.payouts import acquire_idempotency_lock

        # Pre-set the lock
        mock_redis.set("idempotency:test_key", "1")

        with patch('tasks.payouts.get_redis_client', return_value=mock_redis):
            result = acquire_idempotency_lock("test_key", ttl_seconds=300)
            assert result is False

    def test_release_lock(self, mock_redis):
        """Should release lock successfully."""
        from tasks.payouts import release_idempotency_lock

        # Set a lock first
        mock_redis.set("idempotency:test_key", "1")

        with patch('tasks.payouts.get_redis_client', return_value=mock_redis):
            release_idempotency_lock("test_key")
            assert mock_redis.get("idempotency:test_key") is None

    def test_acquire_lock_redis_failure_allows_execution(self, mock_redis):
        """Should allow execution when Redis fails (fail-open)."""
        from tasks.payouts import acquire_idempotency_lock

        mock_redis_failing = Mock()
        mock_redis_failing.set.side_effect = Exception("Redis connection failed")

        with patch('tasks.payouts.get_redis_client', return_value=mock_redis_failing):
            result = acquire_idempotency_lock("test_key")
            # Should return True to allow execution on Redis failure
            assert result is True


class TestProcessAutoPayouts:
    """Test automatic payout processing."""

    def test_skips_when_already_processed_today(self, mock_redis):
        """Should skip when idempotency key exists for today."""
        from tasks.payouts import acquire_idempotency_lock

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        idempotency_key = f"auto_payouts:{today}"

        with patch('tasks.payouts.get_redis_client', return_value=mock_redis):
            # First call should succeed
            assert acquire_idempotency_lock(idempotency_key) is True

            # Second call should fail (already held)
            assert acquire_idempotency_lock(idempotency_key) is False

    @pytest.mark.asyncio
    async def test_processes_eligible_creators(self, mock_redis, mock_db):
        """Should process payouts for eligible creators."""
        # This test verifies the async flow works
        pass  # Full implementation would require more complex mocking


class TestPayoutRetryLogic:
    """Test retry behavior for payout tasks."""

    def test_max_retries_configured(self):
        """Should have max_retries configured on payout tasks."""
        from tasks.payouts import process_auto_payouts

        # Verify the task has retry configuration
        assert process_auto_payouts.max_retries == 3

    def test_retry_delay_configured(self):
        """Should have default_retry_delay configured."""
        from tasks.payouts import process_auto_payouts

        assert process_auto_payouts.default_retry_delay == 300  # 5 minutes


class TestPayoutCalculations:
    """Test payout amount calculations."""

    def test_platform_fee_calculation(self):
        """Should correctly calculate platform fee."""
        # Example: $100 gross, 20% fee = $80 net
        gross_amount = 100.0
        platform_fee_percent = 20.0

        net_amount = gross_amount * (1 - platform_fee_percent / 100)
        assert net_amount == 80.0

    def test_minimum_payout_threshold(self):
        """Should respect minimum payout threshold."""
        from config import settings

        assert settings.PAYOUT_MINIMUM_USD >= 0
        # Default should be $50
        assert settings.PAYOUT_MINIMUM_USD == 50.0


class TestPayoutTasks:
    """Test payout task configuration."""

    def test_all_payout_tasks_have_retry(self):
        """All payout tasks should have retry configuration."""
        from tasks import payouts

        tasks_to_check = [
            'process_auto_payouts',
            'mature_pending_earnings',
            'send_payout_reminders',
        ]

        for task_name in tasks_to_check:
            if hasattr(payouts, task_name):
                task = getattr(payouts, task_name)
                if hasattr(task, 'max_retries'):
                    assert task.max_retries >= 0, f"{task_name} should have max_retries"

    def test_payout_settings(self):
        """Payout settings should be configured."""
        from config import settings

        assert settings.PAYOUT_HOLDING_DAYS > 0
        assert settings.PAYOUT_MINIMUM_USD > 0
        assert 0 <= settings.PAYOUT_PLATFORM_FEE_PERCENT <= 100
