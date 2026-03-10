"""Template tests -- CRUD, category filtering, preview with merge tags.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_template_obj(**overrides):
    """Create a MagicMock template that passes Pydantic model_validate."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "name": "Test Template",
        "category": "custom",
        "body": "Hello {{first_name}}!",
        "media_urls": [],
        "is_shared": True,
        "created_by": TEST_USER_ID,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_contact_obj(**overrides):
    """Create a MagicMock contact for preview tests."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "phone_number": "+14155550001",
        "email": "preview@test.com",
        "first_name": "PreviewFirst",
        "last_name": "PreviewLast",
        "custom_fields": {"promo_code": "SAVE20"},
        "status": "active",
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# Test: create template
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_template(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/templates/ should create a new template."""
    template = _make_template_obj(
        name="New Template",
        category="custom",
        is_shared=True,
    )

    with patch("app.routers.templates.Template") as MockTemplate:
        MockTemplate.return_value = template
        db_session.refresh = AsyncMock()

        resp = await authenticated_client.post(
            "/api/v1/templates/",
            json={
                "name": "New Template",
                "category": "custom",
                "body": "Hello {{first_name}}!",
                "is_shared": True,
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["template"]["name"] == "New Template"
    assert data["template"]["category"] == "custom"
    assert data["template"]["is_shared"] is True


# ---------------------------------------------------------------------------
# Test: list templates by category
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_templates_by_category(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/templates/?category=marketing should filter by category."""
    marketing_template = _make_template_obj(
        name="Promo Blast",
        category="marketing",
    )
    onboarding_template = _make_template_obj(
        name="Welcome",
        category="onboarding",
    )

    # Marketing query
    count1 = MagicMock()
    count1.scalar.return_value = 1
    data1 = MagicMock()
    data1.scalars.return_value.all.return_value = [marketing_template]

    # Onboarding query
    count2 = MagicMock()
    count2.scalar.return_value = 1
    data2 = MagicMock()
    data2.scalars.return_value.all.return_value = [onboarding_template]

    db_session.execute = AsyncMock(side_effect=[count1, data1, count2, data2])

    resp = await authenticated_client.get("/api/v1/templates/?category=marketing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for t in data["templates"]:
        assert t["category"] == "marketing"

    resp2 = await authenticated_client.get("/api/v1/templates/?category=onboarding")
    assert resp2.status_code == 200
    data2_resp = resp2.json()
    assert data2_resp["total"] >= 1
    for t in data2_resp["templates"]:
        assert t["category"] == "onboarding"


# ---------------------------------------------------------------------------
# Test: update template
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_template(authenticated_client: AsyncClient, db_session):
    """PUT /api/v1/templates/{id} should update fields."""
    template_id = uuid.uuid4()
    template = _make_template_obj(
        id=template_id,
        name="Welcome Message",
        body="Hi {{first_name}}, welcome!",
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = template
    db_session.execute = AsyncMock(return_value=result_mock)

    async def mock_refresh(obj):
        obj.name = "Updated Welcome"
        obj.body = "Welcome, {{first_name}}! We are glad to have you."

    db_session.refresh = AsyncMock(side_effect=mock_refresh)

    resp = await authenticated_client.put(
        f"/api/v1/templates/{template_id}",
        json={
            "name": "Updated Welcome",
            "body": "Welcome, {{first_name}}! We are glad to have you.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template"]["name"] == "Updated Welcome"
    assert "glad to have you" in data["template"]["body"]


# ---------------------------------------------------------------------------
# Test: delete template
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_template(authenticated_client: AsyncClient, db_session):
    """DELETE /api/v1/templates/{id} should delete the template."""
    template_id = uuid.uuid4()
    template = _make_template_obj(id=template_id)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = template
    db_session.execute = AsyncMock(return_value=result_mock)
    db_session.delete = AsyncMock()

    resp = await authenticated_client.delete(f"/api/v1/templates/{template_id}")
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()


# ---------------------------------------------------------------------------
# Test: preview template with merge tags (sample data)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_template_with_merge_tags(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/templates/{id}/preview without contact_id uses sample data."""
    template_id = uuid.uuid4()
    template = _make_template_obj(
        id=template_id,
        body="Hi {{first_name}}, welcome to our service!",
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = template
    db_session.execute = AsyncMock(return_value=result_mock)

    resp = await authenticated_client.post(f"/api/v1/templates/{template_id}/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert "{{first_name}}" not in data["rendered"]
    # Sample default first_name is "Jane"
    assert "Jane" in data["rendered"]
    assert data["original"] == template.body
    assert len(data["unresolved_tags"]) == 0


# ---------------------------------------------------------------------------
# Test: preview template with real contact data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_template_with_real_contact(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/templates/{id}/preview with contact_id uses real data."""
    template_id = uuid.uuid4()
    contact_id = uuid.uuid4()

    template = _make_template_obj(
        id=template_id,
        body="Hey {{first_name}}, check out our sale! Use code {{promo_code}} for 20% off.",
    )
    contact = _make_contact_obj(id=contact_id)

    # First execute returns template, second returns contact
    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = template

    contact_result = MagicMock()
    contact_result.scalar_one_or_none.return_value = contact

    db_session.execute = AsyncMock(side_effect=[template_result, contact_result])

    resp = await authenticated_client.post(
        f"/api/v1/templates/{template_id}/preview",
        json={"contact_id": str(contact_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "PreviewFirst" in data["rendered"]
    assert "SAVE20" in data["rendered"]
    assert len(data["unresolved_tags"]) == 0


# ---------------------------------------------------------------------------
# Test: preview template with unresolved merge tags
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_template_unresolved_tags(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/templates/{id}/preview with unknown tags shows them."""
    template_id = uuid.uuid4()
    template = _make_template_obj(
        id=template_id,
        body="{{first_name}}, your appointment is tomorrow at {{time}}.",
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = template
    db_session.execute = AsyncMock(return_value=result_mock)

    resp = await authenticated_client.post(f"/api/v1/templates/{template_id}/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert "time" in data["unresolved_tags"]
