"""
Test Fixtures for Worker Tests

Provides mocked Redis, database, and Celery infrastructure.
"""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Generator, Dict, Any
import uuid


# ==============================================================================
# Event Loop Fixtures
# ==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# Redis Fixtures
# ==============================================================================

class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}

    def set(self, key: str, value: str, nx: bool = False, ex: int = None) -> bool:
        """Set a key with optional NX (set if not exists) and EX (expiry)."""
        if nx and key in self._data:
            return False
        self._data[key] = value
        if ex:
            self._expires[key] = ex
        return True

    def get(self, key: str) -> str:
        """Get a key value."""
        return self._data.get(key)

    def delete(self, key: str) -> int:
        """Delete a key."""
        if key in self._data:
            del self._data[key]
            self._expires.pop(key, None)
            return 1
        return 0

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._data

    def keys(self, pattern: str = "*") -> list:
        """Get keys matching pattern."""
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

    def clear(self):
        """Clear all data (for test cleanup)."""
        self._data.clear()
        self._expires.clear()


@pytest.fixture
def mock_redis():
    """Provide a mock Redis instance."""
    return MockRedis()


@pytest.fixture
def mock_redis_client(mock_redis):
    """Patch the get_redis_client function to return mock Redis."""
    with patch('tasks.payouts.get_redis_client', return_value=mock_redis), \
         patch('tasks.cleanup.get_redis_client', return_value=mock_redis):
        yield mock_redis


# ==============================================================================
# Database Fixtures
# ==============================================================================

class MockDBSession:
    """Mock async database session."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self._results = {}

    async def execute(self, query, params=None):
        """Mock execute - returns configured result."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        mock_result.rowcount = 0
        return mock_result

    async def commit(self):
        """Mock commit."""
        self.committed = True

    async def rollback(self):
        """Mock rollback."""
        self.rolled_back = True

    async def refresh(self, obj):
        """Mock refresh."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MockDBSession()


# ==============================================================================
# Celery Fixtures
# ==============================================================================

class MockCeleryTask:
    """Mock Celery task with request context."""

    def __init__(self):
        self.request = Mock()
        self.request.id = str(uuid.uuid4())
        self.request.retries = 0
        self.max_retries = 3
        self._state = None
        self._meta = None

    def update_state(self, state: str, meta: dict = None):
        """Track state updates."""
        self._state = state
        self._meta = meta

    def retry(self, exc=None, countdown=None):
        """Mock retry - raises the exception for testing."""
        self.request.retries += 1
        raise exc if exc else Exception("Retry triggered")


@pytest.fixture
def mock_celery_task():
    """Provide a mock Celery task context."""
    return MockCeleryTask()


# ==============================================================================
# Stripe Fixtures
# ==============================================================================

class MockStripeTransfer:
    """Mock Stripe Transfer object."""

    def __init__(self, id: str, amount: int, destination: str):
        self.id = id
        self.amount = amount
        self.destination = destination
        self.created = int(datetime.now(timezone.utc).timestamp())


class MockStripe:
    """Mock Stripe module."""

    class Transfer:
        @staticmethod
        def create(amount: int, currency: str, destination: str,
                   transfer_group: str = None, idempotency_key: str = None, **kwargs):
            return MockStripeTransfer(
                id=f"tr_{uuid.uuid4().hex[:16]}",
                amount=amount,
                destination=destination
            )


@pytest.fixture
def mock_stripe():
    """Provide mocked Stripe."""
    with patch('tasks.payouts.stripe', MockStripe()):
        yield MockStripe()


# ==============================================================================
# SendGrid Fixtures
# ==============================================================================

class MockSendGridResponse:
    """Mock SendGrid API response."""

    def __init__(self, status_code: int = 202):
        self.status_code = status_code


class MockSendGridClient:
    """Mock SendGrid client."""

    def __init__(self):
        self.sent_emails = []

    def send(self, message):
        """Track sent emails."""
        self.sent_emails.append(message)
        return MockSendGridResponse(202)


@pytest.fixture
def mock_sendgrid():
    """Provide mocked SendGrid."""
    client = MockSendGridClient()
    with patch('tasks.notifications.get_sendgrid_client', return_value=client):
        yield client


# ==============================================================================
# HTTP Client Fixtures
# ==============================================================================

class MockHTTPResponse:
    """Mock HTTPX response."""

    def __init__(self, status_code: int = 200, json_data: dict = None, content: bytes = b""):
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content

    def json(self):
        return self._json


class MockAsyncHTTPClient:
    """Mock async HTTP client."""

    def __init__(self, responses: dict = None):
        self.responses = responses or {}
        self.requests = []

    async def get(self, url: str, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return self.responses.get(url, MockHTTPResponse(200))

    async def post(self, url: str, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return self.responses.get(url, MockHTTPResponse(200))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_http_client():
    """Provide a mock HTTP client."""
    return MockAsyncHTTPClient()


# ==============================================================================
# Settings Fixtures
# ==============================================================================

@pytest.fixture
def mock_settings():
    """Provide mock settings."""
    settings = Mock()
    settings.DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test"
    settings.CELERY_BROKER_URL = "redis://localhost:6379/0"
    settings.REDIS_URL = "redis://localhost:6379/0"
    settings.STRIPE_SECRET_KEY = "sk_test_xxx"
    settings.SENDGRID_API_KEY = "SG.test_key"
    settings.EMAIL_FROM = "test@actorhub.ai"
    settings.EMAIL_FROM_NAME = "ActorHub Test"
    settings.PAYOUT_HOLDING_DAYS = 7
    settings.PAYOUT_MINIMUM_USD = 50.0
    settings.PAYOUT_PLATFORM_FEE_PERCENT = 20.0
    settings.QDRANT_HOST = "localhost"
    settings.QDRANT_PORT = 6333
    settings.QDRANT_COLLECTION = "test_embeddings"
    settings.S3_BUCKET_ACTOR_PACKS = "test-actor-packs"
    return settings


# ==============================================================================
# Tracing Fixtures (No-op) - Not autouse, applied per-test as needed
# ==============================================================================

# Note: Tracing mocks are applied per-test in individual test files
# to avoid import errors when modules don't use all tracing functions


# ==============================================================================
# Sample Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_creator():
    """Sample creator data."""
    return {
        "id": str(uuid.uuid4()),
        "email": "creator@example.com",
        "full_name": "Test Creator",
        "stripe_connect_id": "acct_test123",
        "payout_enabled": True,
    }


@pytest.fixture
def sample_identity():
    """Sample identity data."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "display_name": "Test Actor",
        "verification_status": "verified",
    }


@pytest.fixture
def sample_embedding():
    """Sample face embedding."""
    import numpy as np
    embedding = np.random.randn(512).astype(np.float32)
    return (embedding / np.linalg.norm(embedding)).tolist()
