"""Admin tests -- superadmin access control, tenant listing, impersonation, suspend, stats.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.dependencies import get_current_user
from tests.conftest import (
    TEST_TENANT_ID,
    TEST_USER_ID,
    _make_fake_db,
    make_test_user,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant_obj(**overrides):
    """Create a MagicMock tenant."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Corp",
        "slug": "test-corp",
        "plan_tier": "starter",
        "status": "active",
        "credit_balance": Decimal("50.00"),
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "bandwidth_site_id": None,
        "bandwidth_location_id": None,
        "bandwidth_application_id": None,
        "settings": {},
        "deleted_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "owner_user_id": TEST_USER_ID,
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# Fixtures -- separate superadmin and regular clients
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def admin_db_session():
    """A separate mock db session for admin tests."""
    return _make_fake_db()


@pytest_asyncio.fixture
async def superadmin_user():
    return make_test_user(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="superadmin@blastwave.com",
        role="owner",
        is_superadmin=True,
    )


@pytest_asyncio.fixture
async def regular_user():
    return make_test_user(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="regular@customer.com",
        role="owner",
        is_superadmin=False,
    )


@pytest_asyncio.fixture
async def superadmin_client(admin_db_session, superadmin_user, override_settings):
    from app.main import app

    async def override_get_db():
        yield admin_db_session

    async def override_current_user():
        return superadmin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def regular_client(admin_db_session, regular_user, override_settings):
    from app.main import app

    async def override_get_db():
        yield admin_db_session

    async def override_current_user():
        return regular_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: admin list tenants requires superadmin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_list_tenants_requires_superadmin(regular_client: AsyncClient):
    resp = await regular_client.get("/api/v1/admin/tenants")
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert "superadmin" in detail.lower() or "Superadmin" in detail


# ---------------------------------------------------------------------------
# Test: admin list tenants success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_list_tenants_success(
    superadmin_client: AsyncClient, admin_db_session
):
    tenants = [
        _make_tenant_obj(name="Platform Admin", slug="platform-admin", plan_tier="enterprise"),
        _make_tenant_obj(name="Customer One", slug="customer-one-abc", plan_tier="starter"),
        _make_tenant_obj(name="Customer Two", slug="customer-two-def", plan_tier="growth"),
    ]

    # count query
    count_result = MagicMock()
    count_result.scalar.return_value = 3

    # data query
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = tenants

    # For each tenant: user_count, contact_count, number_count (3 tenants x 3 queries)
    def make_count(val):
        r = MagicMock()
        r.scalar.return_value = val
        return r

    per_tenant = []
    for _ in tenants:
        per_tenant.extend([make_count(1), make_count(3), make_count(1)])

    admin_db_session.execute = AsyncMock(
        side_effect=[count_result, data_result] + per_tenant
    )

    resp = await superadmin_client.get("/api/v1/admin/tenants")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    assert len(data["tenants"]) >= 3

    tenant_slugs = {t["slug"] for t in data["tenants"]}
    assert any("customer-one" in s for s in tenant_slugs)
    assert any("customer-two" in s for s in tenant_slugs)

    for t in data["tenants"]:
        assert "user_count" in t
        assert "contact_count" in t
        assert "phone_number_count" in t


# ---------------------------------------------------------------------------
# Test: admin impersonate tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_impersonate_tenant(
    superadmin_client: AsyncClient, admin_db_session
):
    tenant_id = uuid.uuid4()
    tenant = _make_tenant_obj(id=tenant_id, name="Customer One", slug="customer-one")

    owner = MagicMock()
    owner.id = uuid.uuid4()
    owner.email = "owner@customer.com"
    owner.role = "owner"
    owner.tenant_id = tenant_id
    owner.is_superadmin = False

    # Tenant lookup
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant

    # Owner lookup
    owner_result = MagicMock()
    owner_result.scalar_one_or_none.return_value = owner

    admin_db_session.execute = AsyncMock(side_effect=[tenant_result, owner_result])

    with patch("app.routers.admin.create_access_token") as mock_token:
        mock_token.return_value = "fake-impersonation-jwt"
        resp = await superadmin_client.post(
            f"/api/v1/admin/tenants/{tenant_id}/impersonate"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "fake-impersonation-jwt"
    assert data["tenant"]["id"] == str(tenant_id)
    assert data["impersonated_user"]["email"] == "owner@customer.com"


# ---------------------------------------------------------------------------
# Test: admin impersonate -- regular user gets 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_impersonate_requires_superadmin(regular_client: AsyncClient):
    tenant_id = uuid.uuid4()
    resp = await regular_client.post(
        f"/api/v1/admin/tenants/{tenant_id}/impersonate"
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: admin suspend tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_suspend_tenant(
    superadmin_client: AsyncClient, admin_db_session
):
    tenant_id = uuid.uuid4()
    tenant = _make_tenant_obj(id=tenant_id, status="active")

    # Tenant lookup
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant

    # Users query for suspension
    user_mock = MagicMock()
    user_mock.is_superadmin = False
    user_mock.is_active = True

    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [user_mock]

    admin_db_session.execute = AsyncMock(side_effect=[tenant_result, users_result])
    admin_db_session.refresh = AsyncMock()

    resp = await superadmin_client.put(
        f"/api/v1/admin/tenants/{tenant_id}",
        json={"status": "suspended"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant"]["status"] == "suspended"
    assert "updated" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test: admin suspend -- regular user gets 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_suspend_requires_superadmin(regular_client: AsyncClient):
    tenant_id = uuid.uuid4()
    resp = await regular_client.put(
        f"/api/v1/admin/tenants/{tenant_id}",
        json={"status": "suspended"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: admin platform stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_platform_stats(
    superadmin_client: AsyncClient, admin_db_session
):
    def make_scalar(val):
        r = MagicMock()
        r.scalar.return_value = val
        return r

    # plan breakdown query returns rows
    plan_result = MagicMock()
    plan_result.all.return_value = [
        ("starter", 2),
        ("growth", 1),
        ("enterprise", 1),
    ]

    admin_db_session.execute = AsyncMock(side_effect=[
        make_scalar(4),          # total_tenants
        make_scalar(4),          # active_tenants
        plan_result,             # plan_breakdown
        make_scalar(10),         # messages_today
        make_scalar(100),        # messages_month
        make_scalar(Decimal("25.00")),  # revenue_month
        make_scalar(5),          # total_users
        make_scalar(2),          # total_numbers
    ])

    resp = await superadmin_client.get("/api/v1/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tenants"] >= 3
    assert data["active_tenants"] >= 3
    assert "plan_breakdown" in data
    assert data["total_users"] >= 3
    assert data["total_phone_numbers"] >= 1
    assert "messages_today" in data
    assert "messages_this_month" in data
    assert "revenue_this_month" in data


# ---------------------------------------------------------------------------
# Test: admin platform stats -- regular user gets 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_platform_stats_requires_superadmin(regular_client: AsyncClient):
    resp = await regular_client.get("/api/v1/admin/stats")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: admin update tenant plan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_update_tenant_plan(
    superadmin_client: AsyncClient, admin_db_session
):
    tenant_id = uuid.uuid4()
    tenant = _make_tenant_obj(id=tenant_id, plan_tier="starter")

    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant
    admin_db_session.execute = AsyncMock(return_value=tenant_result)
    admin_db_session.refresh = AsyncMock()

    resp = await superadmin_client.put(
        f"/api/v1/admin/tenants/{tenant_id}",
        json={"plan_tier": "growth"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant"]["plan_tier"] == "growth"


# ---------------------------------------------------------------------------
# Test: admin update tenant -- invalid status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_update_tenant_invalid_status(
    superadmin_client: AsyncClient, admin_db_session
):
    tenant_id = uuid.uuid4()
    tenant = _make_tenant_obj(id=tenant_id)

    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant
    admin_db_session.execute = AsyncMock(return_value=tenant_result)

    resp = await superadmin_client.put(
        f"/api/v1/admin/tenants/{tenant_id}",
        json={"status": "invalid_status"},
    )
    assert resp.status_code == 400
