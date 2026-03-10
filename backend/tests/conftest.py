"""Shared test fixtures for the BlastWave SMS backend test suite.

Uses mocks for all external services (database, Redis, Bandwidth, Stripe)
so tests are fully self-contained and require no running infrastructure.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.database import get_db
from app.services.auth import (
    create_access_token,
    hash_password,
)

# ---------------------------------------------------------------------------
# Test settings override
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "test-secret-key-for-testing-only-32chars!"
TEST_JWT_ALGORITHM = "HS256"


def get_test_settings() -> Settings:
    """Return a Settings instance with deterministic test values."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        database_url_sync="sqlite:///:memory:",
        debug=False,
        jwt_secret=TEST_JWT_SECRET,
        jwt_algorithm=TEST_JWT_ALGORITHM,
        jwt_access_expire_minutes=15,
        jwt_refresh_expire_days=7,
        redis_url="redis://localhost:6379/15",
        bandwidth_account_id="test-account-id",
        bandwidth_api_token="test-api-token",
        bandwidth_api_secret="test-api-secret",
        bandwidth_application_id="test-app-id",
        stripe_secret_key="sk_test_fake",
        stripe_publishable_key="pk_test_fake",
        stripe_webhook_secret="whsec_test_fake",
    )


@pytest.fixture(autouse=True)
def override_settings():
    """Override the cached settings singleton for every test."""
    test_settings = get_test_settings()
    with patch("app.config.get_settings", return_value=test_settings):
        # Also patch wherever settings is imported at module level
        with patch("app.services.auth.settings", test_settings):
            with patch("app.services.rate_limiter.settings", test_settings):
                yield test_settings


# ---------------------------------------------------------------------------
# Fake in-memory database session
# ---------------------------------------------------------------------------


def _make_fake_db():
    """Create a mock AsyncSession with async context manager support.

    The mock stores objects in a list so tests can inspect what was added.
    It provides the basic interface needed by the service layer:
    add, flush, commit, refresh, execute, and close.
    """
    db = AsyncMock()
    db._added_objects = []

    def _add(obj):
        db._added_objects.append(obj)

    db.add = MagicMock(side_effect=_add)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.close = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()

    return db


@pytest_asyncio.fixture
async def db_session():
    """Provide a mock async database session."""
    return _make_fake_db()


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

TEST_TENANT_ID = uuid.uuid4()
TEST_USER_ID = uuid.uuid4()
TEST_USER_EMAIL = "testuser@example.com"
TEST_USER_PASSWORD = "S3cureP@ssw0rd!"
TEST_COMPANY_NAME = "Test Company"


def make_test_tenant(
    tenant_id: uuid.UUID | None = None,
    credit_balance: Decimal = Decimal("100.0000"),
    plan_tier: str = "free_trial",
):
    """Create a mock Tenant object."""
    tenant = MagicMock()
    tenant.id = tenant_id or TEST_TENANT_ID
    tenant.name = TEST_COMPANY_NAME
    tenant.slug = "test-company"
    tenant.owner_user_id = TEST_USER_ID
    tenant.plan_tier = plan_tier
    tenant.credit_balance = credit_balance
    tenant.status = "active"
    tenant.settings = {"timezone": "America/New_York"}
    tenant.stripe_customer_id = None
    tenant.stripe_subscription_id = None
    tenant.created_at = datetime.now(timezone.utc)
    tenant.updated_at = datetime.now(timezone.utc)
    tenant.deleted_at = None
    return tenant


def make_test_user(
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    email: str = TEST_USER_EMAIL,
    role: str = "owner",
    mfa_enabled: bool = False,
    mfa_secret: str | None = None,
    is_active: bool = True,
    is_superadmin: bool = False,
):
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or TEST_USER_ID
    user.tenant_id = tenant_id or TEST_TENANT_ID
    user.email = email
    user.password_hash = hash_password(TEST_USER_PASSWORD)
    user.first_name = "Test"
    user.last_name = "User"
    user.role = role
    user.mfa_enabled = mfa_enabled
    user.mfa_secret = mfa_secret
    user.is_active = is_active
    user.is_superadmin = is_superadmin
    user.last_login_at = None
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def make_test_contact(
    tenant_id: uuid.UUID | None = None,
    phone_number: str = "+15551234567",
    first_name: str = "Jane",
    last_name: str = "Doe",
    email: str = "jane@example.com",
    custom_fields: dict | None = None,
    status: str = "active",
):
    """Create a mock Contact object."""
    contact = MagicMock()
    contact.id = uuid.uuid4()
    contact.tenant_id = tenant_id or TEST_TENANT_ID
    contact.phone_number = phone_number
    contact.first_name = first_name
    contact.last_name = last_name
    contact.email = email
    contact.custom_fields = custom_fields or {}
    contact.status = status
    contact.opted_in_at = datetime.now(timezone.utc)
    contact.opted_out_at = None
    contact.opt_in_method = "manual"
    contact.last_messaged_at = None
    contact.message_count = 0
    return contact


def make_test_phone_number(
    tenant_id: uuid.UUID | None = None,
    number: str = "+15559876543",
    status: str = "active",
):
    """Create a mock PhoneNumber object."""
    phone = MagicMock()
    phone.id = uuid.uuid4()
    phone.tenant_id = tenant_id or TEST_TENANT_ID
    phone.number = number
    phone.number_type = "local"
    phone.status = status
    phone.capabilities = ["sms", "mms"]
    phone.monthly_cost = Decimal("1.0000")
    return phone


# ---------------------------------------------------------------------------
# Fixtures for test tenant and user
# ---------------------------------------------------------------------------


@pytest.fixture
def test_tenant():
    return make_test_tenant()


@pytest.fixture
def test_user():
    return make_test_user()


@pytest.fixture
def test_contact():
    return make_test_contact()


@pytest.fixture
def test_phone_number():
    return make_test_phone_number()


# ---------------------------------------------------------------------------
# FastAPI test client (with DB override)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with database dependency override."""
    # Import app lazily to allow settings patching to take effect
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient, db_session, test_user, test_tenant
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated test client with a valid JWT.

    Patches get_current_user so the test user is always returned,
    and sets the Authorization header with a real JWT.
    """
    from app.dependencies import get_current_user

    # Generate a real JWT for the test user
    access_token = create_access_token(
        str(test_user.id),
        str(test_user.tenant_id),
        test_user.role,
    )
    client.headers["Authorization"] = f"Bearer {access_token}"

    # Override the dependency so it returns the mock user without DB lookup
    async def override_current_user():
        return test_user

    from app.main import app

    app.dependency_overrides[get_current_user] = override_current_user

    yield client

    # Clean up the override (client fixture already clears get_db)
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Bandwidth mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_bandwidth():
    """Patch the bandwidth_client singleton with an AsyncMock."""
    with patch("app.services.bandwidth.bandwidth_client") as mock_bw:
        mock_bw.send_sms = AsyncMock(return_value={
            "id": "bw-msg-123",
            "owner": "+15559876543",
            "text": "Hello",
            "direction": "out",
        })
        mock_bw.send_mms = AsyncMock(return_value={
            "id": "bw-msg-456",
            "owner": "+15559876543",
            "text": "Hello",
            "media": ["https://example.com/image.jpg"],
            "direction": "out",
        })
        mock_bw.send_message = AsyncMock(return_value={
            "id": "bw-msg-789",
            "owner": "+15559876543",
            "text": "Hello",
            "direction": "out",
        })
        mock_bw.search_available_numbers = AsyncMock(return_value=[
            {"telephoneNumber": "+15551111111"},
            {"telephoneNumber": "+15552222222"},
        ])
        mock_bw.order_numbers = AsyncMock(return_value={
            "orderId": "order-123",
            "status": "COMPLETE",
        })
        mock_bw.register_brand = AsyncMock(return_value={
            "brandId": "brand-123",
            "entityName": "Test Corp",
            "status": "APPROVED",
        })
        mock_bw.register_campaign = AsyncMock(return_value={
            "campaignId": "camp-123",
            "status": "ACTIVE",
        })
        yield mock_bw


# ---------------------------------------------------------------------------
# Redis mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """Provide a mock Redis client that simulates basic operations."""
    redis_mock = AsyncMock()
    redis_mock.pipeline = MagicMock()

    # Pipeline mock
    pipe = AsyncMock()
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.incr = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[0, 0, True, True])
    redis_mock.pipeline.return_value = pipe

    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.zrem = AsyncMock(return_value=1)
    redis_mock.llen = AsyncMock(return_value=0)
    redis_mock.close = AsyncMock()

    return redis_mock


# ---------------------------------------------------------------------------
# Stripe mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_stripe():
    """Patch the stripe module for billing-related tests."""
    with patch("stripe.Customer") as mock_customer, \
         patch("stripe.Subscription") as mock_sub:
        mock_customer.create.return_value = MagicMock(id="cus_test123")
        mock_sub.create.return_value = MagicMock(id="sub_test123")
        yield {
            "Customer": mock_customer,
            "Subscription": mock_sub,
        }
