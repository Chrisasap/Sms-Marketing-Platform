"""Billing tests -- overview, plans, checkout session, billing events.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_TENANT_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant_obj(**overrides):
    """Create a MagicMock tenant for billing tests."""
    defaults = {
        "id": TEST_TENANT_ID,
        "name": "Billing Corp",
        "slug": "billing-corp",
        "plan_tier": "starter",
        "status": "active",
        "credit_balance": Decimal("25.50"),
        "stripe_customer_id": "cus_test123",
        "stripe_subscription_id": None,
        "settings": {},
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_billing_event_obj(**overrides):
    """Create a MagicMock billing event."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "event_type": "sms_sent",
        "quantity": 10,
        "unit_cost": Decimal("0.0075"),
        "total_cost": Decimal("0.075"),
        "campaign_id": None,
        "stripe_invoice_item_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# Test: get billing overview
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_billing_overview(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/billing/ should return billing overview."""
    tenant = _make_tenant_obj()

    # tenant query
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant

    # sms count
    sms_result = MagicMock()
    sms_result.scalar.return_value = 50

    # mms count
    mms_result = MagicMock()
    mms_result.scalar.return_value = 5

    # overage cost
    overage_result = MagicMock()
    overage_result.scalar.return_value = Decimal("0.50")

    db_session.execute = AsyncMock(
        side_effect=[tenant_result, sms_result, mms_result, overage_result]
    )

    resp = await authenticated_client.get("/api/v1/billing/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan_tier"] == "starter"
    assert data["plan_name"] == "Starter"
    assert data["credit_balance"] == 25.50
    assert data["current_period_sms"] >= 0
    assert data["current_period_mms"] >= 0
    assert data["included_sms"] == 1000
    assert data["included_mms"] == 100


# ---------------------------------------------------------------------------
# Test: get plans
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_plans(authenticated_client: AsyncClient):
    """GET /api/v1/billing/plans should return available plans."""
    resp = await authenticated_client.get("/api/v1/billing/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert "plans" in data
    tiers = {p["tier"] for p in data["plans"]}
    assert "free_trial" in tiers
    assert "starter" in tiers
    assert "growth" in tiers
    assert "enterprise" in tiers

    starter = next(p for p in data["plans"] if p["tier"] == "starter")
    assert starter["price"] == 49.0
    assert starter["included_sms"] == 1000
    assert starter["max_users"] == 3


# ---------------------------------------------------------------------------
# Test: create checkout session (mock Stripe)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_checkout_session(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/billing/checkout should create a Stripe session."""
    tenant = _make_tenant_obj(stripe_customer_id="cus_test123")

    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant
    db_session.execute = AsyncMock(return_value=tenant_result)

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test_session"
    mock_session.id = "cs_test_abc123"

    # Patch PLANS so growth has a stripe_price_id (at module import time it
    # picks up the empty test settings value).
    patched_plans = {
        "free_trial": {
            "tier": "free_trial", "name": "Free Trial",
            "price": Decimal("0"), "included_sms": 100, "included_mms": 10,
            "max_numbers": 1, "max_users": 1, "max_contacts": 500,
            "max_ai_agents": 0, "stripe_price_id": None,
        },
        "starter": {
            "tier": "starter", "name": "Starter",
            "price": Decimal("49"), "included_sms": 1000, "included_mms": 100,
            "max_numbers": 3, "max_users": 3, "max_contacts": 5000,
            "max_ai_agents": 1, "stripe_price_id": "price_test_starter",
        },
        "growth": {
            "tier": "growth", "name": "Growth",
            "price": Decimal("149"), "included_sms": 5000, "included_mms": 500,
            "max_numbers": 10, "max_users": 10, "max_contacts": 25000,
            "max_ai_agents": 3, "stripe_price_id": "price_test_growth",
        },
        "enterprise": {
            "tier": "enterprise", "name": "Enterprise",
            "price": Decimal("499"), "included_sms": 25000, "included_mms": 2500,
            "max_numbers": 50, "max_users": 50, "max_contacts": 100000,
            "max_ai_agents": 10, "stripe_price_id": "price_test_enterprise",
        },
    }

    with patch("app.routers.billing.PLANS", patched_plans):
        with patch("app.routers.billing._get_stripe") as mock_stripe_fn:
            mock_stripe = MagicMock()
            mock_stripe_fn.return_value = mock_stripe
            mock_stripe.checkout.Session.create.return_value = mock_session

            with patch("app.routers.billing.settings") as mock_settings:
                mock_settings.app_url = "http://localhost:3000"
                mock_settings.stripe_secret_key = "sk_test_fake"

                resp = await authenticated_client.post(
                    "/api/v1/billing/checkout",
                    json={"plan": "growth"},
                )

    assert resp.status_code == 200
    data = resp.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/test_session"
    assert data["session_id"] == "cs_test_abc123"


# ---------------------------------------------------------------------------
# Test: billing events tracked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_billing_events_tracked(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/billing/events should return billing events."""
    events = [
        _make_billing_event_obj(event_type="sms_sent", quantity=10),
        _make_billing_event_obj(event_type="sms_sent", quantity=20),
        _make_billing_event_obj(event_type="sms_sent", quantity=30),
        _make_billing_event_obj(event_type="mms_sent", quantity=5),
    ]

    count_result = MagicMock()
    count_result.scalar.return_value = 4

    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = events

    db_session.execute = AsyncMock(side_effect=[count_result, data_result])

    resp = await authenticated_client.get("/api/v1/billing/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 4
    assert len(data["events"]) >= 4

    event_types = {e["event_type"] for e in data["events"]}
    assert "sms_sent" in event_types
    assert "mms_sent" in event_types


# ---------------------------------------------------------------------------
# Test: billing events filter by type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_billing_events_filter_by_type(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/billing/events?event_type=mms_sent should filter."""
    mms_event = _make_billing_event_obj(event_type="mms_sent", quantity=5)

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [mms_event]

    db_session.execute = AsyncMock(side_effect=[count_result, data_result])

    resp = await authenticated_client.get("/api/v1/billing/events?event_type=mms_sent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for ev in data["events"]:
        assert ev["event_type"] == "mms_sent"


# ---------------------------------------------------------------------------
# Test: invalid plan in checkout returns 400
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_checkout_invalid_plan(authenticated_client: AsyncClient):
    """POST /api/v1/billing/checkout with free_trial should return 400."""
    resp = await authenticated_client.post(
        "/api/v1/billing/checkout",
        json={"plan": "free_trial"},
    )
    assert resp.status_code == 400
    assert "Invalid plan" in resp.json()["detail"]
