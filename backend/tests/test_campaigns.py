"""Campaign tests -- create, launch, pause, resume, cancel, stats, filtering.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_TENANT_ID


# ---------------------------------------------------------------------------
# Pre-register the task module as a mock to avoid Celery import issues.
# The campaigns router does a lazy `from app.tasks.send_messages import ...`
# inside the launch/resume handlers.
# ---------------------------------------------------------------------------

_mock_send_mod = MagicMock()
_mock_send_mod.send_campaign_messages = MagicMock()
if "app.tasks.send_messages" not in sys.modules:
    sys.modules.setdefault("app.tasks.send_messages", _mock_send_mod)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_campaign_obj(**overrides):
    """Create a MagicMock campaign that passes Pydantic model_validate."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "name": "Test Campaign",
        "campaign_type": "blast",
        "status": "draft",
        "from_number_id": None,
        "message_template": "Hello!",
        "media_urls": [],
        "total_recipients": 0,
        "sent_count": 0,
        "delivered_count": 0,
        "failed_count": 0,
        "opted_out_count": 0,
        "scheduled_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# Test: create campaign in draft status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_campaign_draft(authenticated_client: AsyncClient):
    """POST /api/v1/campaigns/ should create a draft campaign."""
    campaign = _make_campaign_obj(
        name="Test Blast",
        campaign_type="blast",
        status="draft",
        total_recipients=3,
    )

    with patch(
        "app.routers.campaigns.svc_create",
        new_callable=AsyncMock,
        return_value=campaign,
    ):
        resp = await authenticated_client.post(
            "/api/v1/campaigns/",
            json={
                "name": "Test Blast",
                "campaign_type": "blast",
                "message_template": "Hello {{first_name}}!",
                "target_list_ids": [str(uuid.uuid4())],
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["campaign"]["status"] == "draft"
    assert data["campaign"]["name"] == "Test Blast"
    assert data["campaign"]["total_recipients"] == 3


# ---------------------------------------------------------------------------
# Test: create campaign with schedule
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_campaign_with_schedule(authenticated_client: AsyncClient):
    """POST /api/v1/campaigns/ with scheduled_at should include it."""
    scheduled = datetime.now(timezone.utc) + timedelta(hours=2)
    campaign = _make_campaign_obj(
        name="Scheduled Blast",
        scheduled_at=scheduled,
    )

    with patch(
        "app.routers.campaigns.svc_create",
        new_callable=AsyncMock,
        return_value=campaign,
    ):
        resp = await authenticated_client.post(
            "/api/v1/campaigns/",
            json={
                "name": "Scheduled Blast",
                "campaign_type": "blast",
                "message_template": "Hello!",
                "target_list_ids": [str(uuid.uuid4())],
                "scheduled_at": scheduled.isoformat(),
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["campaign"]["status"] == "draft"
    assert data["campaign"]["scheduled_at"] is not None


# ---------------------------------------------------------------------------
# Test: launch campaign
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_launch_campaign(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/campaigns/{id}/launch should transition to sending."""
    campaign_id = uuid.uuid4()
    campaign = _make_campaign_obj(
        id=campaign_id,
        status="sending",
        total_recipients=3,
    )

    # _get_campaign_or_404 uses db.execute
    camp_result = MagicMock()
    camp_result.scalar_one_or_none.return_value = campaign
    db_session.execute = AsyncMock(return_value=camp_result)

    with patch(
        "app.routers.campaigns.svc_launch",
        new_callable=AsyncMock,
        return_value=campaign,
    ):
        with patch("app.tasks.send_messages.send_campaign_messages") as mock_task:
            mock_task.delay = MagicMock()
            resp = await authenticated_client.post(
                f"/api/v1/campaigns/{campaign_id}/launch"
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign"]["status"] == "sending"
    assert data["campaign"]["total_recipients"] == 3


# ---------------------------------------------------------------------------
# Test: pause campaign
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pause_campaign(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/campaigns/{id}/pause should transition to paused."""
    campaign_id = uuid.uuid4()
    campaign = _make_campaign_obj(id=campaign_id, status="paused")

    camp_result = MagicMock()
    camp_result.scalar_one_or_none.return_value = campaign
    db_session.execute = AsyncMock(return_value=camp_result)

    with patch(
        "app.routers.campaigns.svc_pause",
        new_callable=AsyncMock,
        return_value=campaign,
    ):
        resp = await authenticated_client.post(
            f"/api/v1/campaigns/{campaign_id}/pause"
        )

    assert resp.status_code == 200
    assert resp.json()["campaign"]["status"] == "paused"


# ---------------------------------------------------------------------------
# Test: resume campaign
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_campaign(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/campaigns/{id}/resume should transition to sending."""
    campaign_id = uuid.uuid4()
    campaign = _make_campaign_obj(id=campaign_id, status="sending")

    camp_result = MagicMock()
    camp_result.scalar_one_or_none.return_value = campaign
    db_session.execute = AsyncMock(return_value=camp_result)

    with patch(
        "app.routers.campaigns.svc_resume",
        new_callable=AsyncMock,
        return_value=campaign,
    ):
        with patch("app.tasks.send_messages.send_campaign_messages") as mock_task:
            mock_task.delay = MagicMock()
            resp = await authenticated_client.post(
                f"/api/v1/campaigns/{campaign_id}/resume"
            )

    assert resp.status_code == 200
    assert resp.json()["campaign"]["status"] == "sending"


# ---------------------------------------------------------------------------
# Test: cancel campaign
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_campaign(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/campaigns/{id}/cancel should transition to canceled."""
    campaign_id = uuid.uuid4()
    campaign = _make_campaign_obj(id=campaign_id, status="canceled")

    camp_result = MagicMock()
    camp_result.scalar_one_or_none.return_value = campaign
    db_session.execute = AsyncMock(return_value=camp_result)

    with patch(
        "app.routers.campaigns.svc_cancel",
        new_callable=AsyncMock,
        return_value=campaign,
    ):
        resp = await authenticated_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel"
        )

    assert resp.status_code == 200
    assert resp.json()["campaign"]["status"] == "canceled"


# ---------------------------------------------------------------------------
# Test: get campaign stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_campaign_stats(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/campaigns/{id}/stats should return delivery statistics."""
    campaign_id = uuid.uuid4()
    campaign = _make_campaign_obj(id=campaign_id, status="completed")

    camp_result = MagicMock()
    camp_result.scalar_one_or_none.return_value = campaign
    db_session.execute = AsyncMock(return_value=camp_result)

    stats = {
        "total_recipients": 3,
        "sent": 3,
        "delivered": 2,
        "failed": 1,
        "opted_out": 0,
        "delivery_rate": 0.67,
        "response_rate": 0.0,
        "cost": 0.015,
    }

    with patch(
        "app.routers.campaigns.svc_stats",
        new_callable=AsyncMock,
        return_value=stats,
    ):
        resp = await authenticated_client.get(
            f"/api/v1/campaigns/{campaign_id}/stats"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_recipients"] == 3
    assert data["delivered"] == 2
    assert data["failed"] == 1


# ---------------------------------------------------------------------------
# Test: list campaigns filter by status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_campaigns_filter_by_status(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/campaigns/?status=draft should return only draft campaigns."""
    draft_campaign = _make_campaign_obj(name="Draft Campaign", status="draft")

    # count query returns 1
    count_result = MagicMock()
    count_result.scalar.return_value = 1

    # data query returns one campaign
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [draft_campaign]

    db_session.execute = AsyncMock(side_effect=[count_result, data_result])

    resp = await authenticated_client.get("/api/v1/campaigns/?status=draft")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for c in data["campaigns"]:
        assert c["status"] == "draft"
