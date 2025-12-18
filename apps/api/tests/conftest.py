"""
Pytest Configuration and Fixtures
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.core.security import create_access_token, hash_password


# Test database URL - Docker exposes PostgreSQL on port 5433
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/actorhub_test"
)

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_token(test_user: User) -> str:
    """Create auth token for test user"""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
async def auth_client(
    client: AsyncClient,
    test_user_token: str
) -> AsyncClient:
    """Client with authentication headers"""
    client.headers["Authorization"] = f"Bearer {test_user_token}"
    return client


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user"""
    from app.models.user import UserRole, UserTier

    user = User(
        email="admin@actorhub.ai",
        hashed_password=hash_password("adminpassword123"),
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_verified=True,
        role=UserRole.ADMIN,
        tier=UserTier.ENTERPRISE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_token(admin_user: User) -> str:
    """Create auth token for admin user"""
    return create_access_token(data={"sub": str(admin_user.id)})


@pytest.fixture
async def admin_client(
    client: AsyncClient,
    admin_token: str
) -> AsyncClient:
    """Client with admin authentication"""
    client.headers["Authorization"] = f"Bearer {admin_token}"
    return client


@pytest.fixture
async def creator_user(db_session: AsyncSession) -> User:
    """Create a creator user"""
    from app.models.user import UserRole, UserTier

    user = User(
        email="creator@example.com",
        hashed_password=hash_password("creatorpass123"),
        first_name="Creator",
        last_name="User",
        is_active=True,
        is_verified=True,
        role=UserRole.CREATOR,
        tier=UserTier.PRO,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_identity(db_session: AsyncSession, test_user: User):
    """Create a test identity"""
    from app.models.identity import Identity, IdentityStatus
    import uuid

    identity = Identity(
        id=uuid.uuid4(),
        user_id=test_user.id,
        display_name="Test Actor",
        bio="Test actor for testing",
                status=IdentityStatus.VERIFIED,
        allow_commercial_use=True,
        allow_ai_training=True
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)
    return identity


@pytest.fixture
async def test_identity_with_embedding(db_session: AsyncSession, test_user: User):
    """Create identity with embedding data"""
    from app.models.identity import Identity, IdentityStatus
    import uuid

    identity = Identity(
        id=uuid.uuid4(),
        user_id=test_user.id,
        display_name="Embedded Actor",
                status=IdentityStatus.VERIFIED
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)
    return identity


@pytest.fixture
async def test_identity_with_training(db_session: AsyncSession, test_user: User):
    """Create identity with completed training"""
    from app.models.identity import Identity, ActorPack, IdentityStatus, TrainingStatus
    import uuid

    identity = Identity(
        id=uuid.uuid4(),
        user_id=test_user.id,
        display_name="Trained Actor",
                status=IdentityStatus.VERIFIED
    )
    db_session.add(identity)
    await db_session.flush()

    actor_pack = ActorPack(
        id=uuid.uuid4(),
        identity_id=identity.id,
        training_status=TrainingStatus.COMPLETED.value,
        version="1.0.0"
    )
    db_session.add(actor_pack)
    await db_session.commit()
    await db_session.refresh(identity)
    return identity


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create another user"""
    user = User(
        email="other@example.com",
        hashed_password=hash_password("otherpassword123"),
        first_name="Other",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user_identity(db_session: AsyncSession, other_user: User):
    """Create identity for another user"""
    from app.models.identity import Identity, IdentityStatus
    import uuid

    identity = Identity(
        id=uuid.uuid4(),
        user_id=other_user.id,
        display_name="Other Actor",
                status=IdentityStatus.VERIFIED
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)
    return identity


@pytest.fixture
async def test_license(db_session: AsyncSession, test_user: User, test_identity):
    """Create a test license"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=True,
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow()
    )
    db_session.add(license_obj)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def test_license_with_payment(db_session: AsyncSession, test_user: User, test_identity):
    """Create license with payment info"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus, Transaction, TransactionType
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=True,
        stripe_payment_intent_id="pi_test_123",
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow() - timedelta(hours=2)
    )
    db_session.add(license_obj)
    await db_session.flush()

    # Create associated transaction
    transaction = Transaction(
        id=uuid.uuid4(),
        license_id=license_obj.id,
        user_id=test_user.id,
        type=TransactionType.PURCHASE,
        amount_usd=29.99,
        status=PaymentStatus.COMPLETED,
        stripe_payment_intent_id="pi_test_123",
        completed_at=datetime.utcnow() - timedelta(hours=2)
    )
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def test_license_with_identity(db_session: AsyncSession, test_user: User, test_identity):
    """Create license with identity reference"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.COMMERCIAL,
        price_usd=99.99,
        is_active=True,
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow()
    )
    db_session.add(license_obj)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def other_user_license(db_session: AsyncSession, other_user: User, other_user_identity):
    """Create license for another user"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus, Transaction, TransactionType
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=other_user_identity.id,
        licensee_id=other_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=True,
        stripe_payment_intent_id="pi_other_123",
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow()
    )
    db_session.add(license_obj)
    await db_session.flush()

    transaction = Transaction(
        id=uuid.uuid4(),
        license_id=license_obj.id,
        user_id=other_user.id,
        type=TransactionType.PURCHASE,
        amount_usd=29.99,
        status=PaymentStatus.COMPLETED,
        stripe_payment_intent_id="pi_other_123",
        completed_at=datetime.utcnow()
    )
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def refunded_license(db_session: AsyncSession, test_user: User, test_identity):
    """Create a refunded license"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=False,
        payment_status=PaymentStatus.REFUNDED,
        valid_until=datetime.utcnow() + timedelta(days=365),
        paid_at=datetime.utcnow() - timedelta(days=5)
    )
    db_session.add(license_obj)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def old_license(db_session: AsyncSession, test_user: User, test_identity):
    """Create an old license (outside refund window)"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus, Transaction, TransactionType
    from datetime import datetime, timedelta
    import uuid

    license_id = uuid.uuid4()
    license_obj = License(
        id=license_id,
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=True,
        stripe_payment_intent_id="pi_old_123",
        valid_until=datetime.utcnow() + timedelta(days=350),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow() - timedelta(days=15)
    )
    db_session.add(license_obj)
    await db_session.flush()

    # Old license was created 15 days ago
    license_obj.created_at = datetime.utcnow() - timedelta(days=15)

    transaction = Transaction(
        id=uuid.uuid4(),
        license_id=license_id,
        user_id=test_user.id,
        type=TransactionType.PURCHASE,
        amount_usd=29.99,
        status=PaymentStatus.COMPLETED,
        stripe_payment_intent_id="pi_old_123",
        completed_at=datetime.utcnow() - timedelta(days=15)
    )
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def very_recent_license(db_session: AsyncSession, test_user: User, test_identity):
    """Create a very recent license (within cooling period)"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus, Transaction, TransactionType
    from datetime import datetime, timedelta
    import uuid

    license_id = uuid.uuid4()
    license_obj = License(
        id=license_id,
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=True,
        stripe_payment_intent_id="pi_recent_123",
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow() - timedelta(minutes=30)
    )
    db_session.add(license_obj)
    await db_session.flush()

    # Very recent - created 30 minutes ago
    license_obj.created_at = datetime.utcnow() - timedelta(minutes=30)

    transaction = Transaction(
        id=uuid.uuid4(),
        license_id=license_id,
        user_id=test_user.id,
        type=TransactionType.PURCHASE,
        amount_usd=29.99,
        status=PaymentStatus.COMPLETED,
        stripe_payment_intent_id="pi_recent_123",
        completed_at=datetime.utcnow() - timedelta(minutes=30)
    )
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def user_with_max_refunds(db_session: AsyncSession):
    """Create user who has maxed out refunds"""
    user = User(
        email="maxrefunds@example.com",
        hashed_password=hash_password("password123"),
        first_name="Max",
        last_name="Refunds",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def new_license(db_session: AsyncSession, user_with_max_refunds, test_identity):
    """Create new license for max refunds user"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus, Transaction, TransactionType
    from datetime import datetime, timedelta
    import uuid

    license_id = uuid.uuid4()
    license_obj = License(
        id=license_id,
        identity_id=test_identity.id,
        licensee_id=user_with_max_refunds.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=True,
        stripe_payment_intent_id="pi_new_123",
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow() - timedelta(hours=2)
    )
    db_session.add(license_obj)
    await db_session.flush()

    license_obj.created_at = datetime.utcnow() - timedelta(hours=2)

    transaction = Transaction(
        id=uuid.uuid4(),
        license_id=license_id,
        user_id=user_with_max_refunds.id,
        type=TransactionType.PURCHASE,
        amount_usd=29.99,
        status=PaymentStatus.COMPLETED,
        stripe_payment_intent_id="pi_new_123",
        completed_at=datetime.utcnow() - timedelta(hours=2)
    )
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def completed_refund(db_session: AsyncSession, test_user: User, test_identity):
    """Create a completed refund record - returns the refund Transaction"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus, Transaction, TransactionType
    from datetime import datetime, timedelta
    import uuid

    license_id = uuid.uuid4()
    license_obj = License(
        id=license_id,
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=False,
        stripe_payment_intent_id="pi_original_123",
        valid_until=datetime.utcnow() + timedelta(days=364),
        payment_status=PaymentStatus.REFUNDED,
        paid_at=datetime.utcnow() - timedelta(days=2)
    )
    db_session.add(license_obj)
    await db_session.flush()

    # Original purchase transaction
    purchase_txn = Transaction(
        id=uuid.uuid4(),
        license_id=license_id,
        user_id=test_user.id,
        type=TransactionType.PURCHASE,
        amount_usd=29.99,
        status=PaymentStatus.COMPLETED,
        stripe_payment_intent_id="pi_original_123",
        completed_at=datetime.utcnow() - timedelta(days=2)
    )
    db_session.add(purchase_txn)

    # Refund transaction - this is what the test expects to look up
    refund_txn = Transaction(
        id=uuid.uuid4(),
        license_id=license_id,
        user_id=test_user.id,
        type=TransactionType.REFUND,
        amount_usd=-29.99,
        status=PaymentStatus.COMPLETED,
        stripe_payment_intent_id="re_test_completed_123",  # Stripe refund ID
        completed_at=datetime.utcnow() - timedelta(days=1)
    )
    db_session.add(refund_txn)
    await db_session.commit()
    await db_session.refresh(refund_txn)
    return refund_txn  # Return the refund transaction for tests


@pytest.fixture
async def test_identity_no_license(db_session: AsyncSession, test_user: User):
    """Create identity without any license"""
    from app.models.identity import Identity, IdentityStatus
    import uuid

    identity = Identity(
        id=uuid.uuid4(),
        user_id=test_user.id,
        display_name="No License Actor",
                status=IdentityStatus.VERIFIED
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)
    return identity


@pytest.fixture
async def expired_license(db_session: AsyncSession, test_user: User, test_identity):
    """Create an expired license"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=False,
        valid_until=datetime.utcnow() - timedelta(days=30),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow() - timedelta(days=395)
    )
    db_session.add(license_obj)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def transferable_license(db_session: AsyncSession, test_user: User, test_identity):
    """Create a transferable license"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.COMMERCIAL,
        price_usd=99.99,
        is_active=True,
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow()
    )
    db_session.add(license_obj)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def non_transferable_license(db_session: AsyncSession, test_user: User, test_identity):
    """Create a non-transferable license"""
    from app.models.marketplace import License, LicenseType, UsageType, PaymentStatus
    from datetime import datetime, timedelta
    import uuid

    license_obj = License(
        id=uuid.uuid4(),
        identity_id=test_identity.id,
        licensee_id=test_user.id,
        license_type=LicenseType.SINGLE_USE,
        usage_type=UsageType.PERSONAL,
        price_usd=29.99,
        is_active=True,
        valid_until=datetime.utcnow() + timedelta(days=365),
        payment_status=PaymentStatus.COMPLETED,
        paid_at=datetime.utcnow()
    )
    db_session.add(license_obj)
    await db_session.commit()
    await db_session.refresh(license_obj)
    return license_obj


@pytest.fixture
async def active_subscription(db_session: AsyncSession, test_user: User):
    """Create an active subscription"""
    from app.models.notifications import Subscription, SubscriptionStatus, SubscriptionPlan
    from datetime import datetime, timedelta
    import uuid

    subscription = Subscription(
        id=uuid.uuid4(),
        user_id=test_user.id,
        plan=SubscriptionPlan.PRO_MONTHLY,
        status=SubscriptionStatus.ACTIVE,
        stripe_subscription_id="sub_test_123",
        stripe_customer_id="cus_test_123",
        amount=29.99,
        currency="USD",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription
