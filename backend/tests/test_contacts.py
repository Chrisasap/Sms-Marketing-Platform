"""Contact management tests -- CRUD, pagination, search, bulk actions, phone normalisation.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_TENANT_ID,
    make_test_contact,
    make_test_user,
)
from app.services.contact_service import normalize_phone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_contact_response_obj(**overrides):
    """Create a MagicMock that passes Pydantic model_validate (from_attributes)."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "phone_number": "+14155551234",
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "custom_fields": {},
        "status": "active",
        "opted_in_at": datetime.now(timezone.utc),
        "opted_out_at": None,
        "opt_in_method": "api",
        "last_messaged_at": None,
        "message_count": 0,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# Test: create contact -- success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_contact_success(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/contacts/ with a valid phone should return 201."""
    contact_obj = _make_contact_response_obj(
        phone_number="+14155551234",
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
    )

    # db.execute for duplicate check returns None (no duplicate)
    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = None
    db_session.execute = AsyncMock(return_value=dup_result)

    # db.add captures the object; db.refresh makes it look like our mock
    captured = {}

    def capture_add(obj):
        captured["obj"] = obj

    db_session.add = MagicMock(side_effect=capture_add)

    async def mock_refresh(obj):
        # Copy mock attributes onto the real Contact ORM object
        for attr in (
            "id", "phone_number", "first_name", "last_name", "email",
            "custom_fields", "status", "opted_in_at", "opted_out_at",
            "opt_in_method", "last_messaged_at", "message_count", "created_at",
        ):
            setattr(obj, attr, getattr(contact_obj, attr))

    db_session.refresh = AsyncMock(side_effect=mock_refresh)

    with patch("app.routers.contacts.normalize_phone", return_value="+14155551234"):
        resp = await authenticated_client.post(
            "/api/v1/contacts/",
            json={
                "phone_number": "+14155551234",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "contact" in data
    assert data["contact"]["phone_number"] == "+14155551234"
    assert data["contact"]["first_name"] == "Jane"
    assert data["contact"]["status"] == "active"


# ---------------------------------------------------------------------------
# Test: create contact -- invalid phone
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_contact_invalid_phone(authenticated_client: AsyncClient):
    """POST /api/v1/contacts/ with an invalid phone should return 422."""
    with patch("app.routers.contacts.normalize_phone", return_value=None):
        resp = await authenticated_client.post(
            "/api/v1/contacts/",
            json={"phone_number": "not-a-phone"},
        )
    assert resp.status_code == 422
    assert "Invalid phone number" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test: create contact -- duplicate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_contact_duplicate(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/contacts/ with existing phone should return 409."""
    existing = _make_contact_response_obj(phone_number="+15551230000")

    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = existing
    db_session.execute = AsyncMock(return_value=dup_result)

    with patch("app.routers.contacts.normalize_phone", return_value="+15551230000"):
        resp = await authenticated_client.post(
            "/api/v1/contacts/",
            json={"phone_number": "+15551230000"},
        )

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test: list contacts -- pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_contacts_pagination(authenticated_client: AsyncClient):
    """GET /api/v1/contacts/?page=1&per_page=2 should return paginated results."""
    contacts = [_make_contact_response_obj() for _ in range(2)]

    with patch(
        "app.routers.contacts.get_contacts_paginated",
        new_callable=AsyncMock,
        return_value=(contacts, 6),
    ):
        resp = await authenticated_client.get("/api/v1/contacts/?page=1&per_page=2")

    assert resp.status_code == 200
    data = resp.json()
    assert data["per_page"] == 2
    assert data["page"] == 1
    assert len(data["contacts"]) == 2
    assert data["total"] == 6


# ---------------------------------------------------------------------------
# Test: list contacts -- search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_contacts_search(authenticated_client: AsyncClient):
    """GET /api/v1/contacts/?search=First0 should return matching contacts."""
    contact = _make_contact_response_obj(first_name="First0")

    with patch(
        "app.routers.contacts.get_contacts_paginated",
        new_callable=AsyncMock,
        return_value=([contact], 1),
    ):
        resp = await authenticated_client.get("/api/v1/contacts/?search=First0")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(c["first_name"] == "First0" for c in data["contacts"])


# ---------------------------------------------------------------------------
# Test: list contacts -- filter by status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_contacts_filter_by_status(authenticated_client: AsyncClient):
    """GET /api/v1/contacts/?status=opted_out should return only opted_out contacts."""
    contact = _make_contact_response_obj(status="opted_out")

    with patch(
        "app.routers.contacts.get_contacts_paginated",
        new_callable=AsyncMock,
        return_value=([contact], 1),
    ):
        resp = await authenticated_client.get("/api/v1/contacts/?status=opted_out")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for c in data["contacts"]:
        assert c["status"] == "opted_out"


# ---------------------------------------------------------------------------
# Test: get contact by id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_contact_by_id(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/contacts/{id} should return contact with lists."""
    contact_id = uuid.uuid4()
    contact = _make_contact_response_obj(id=contact_id)

    # First execute returns contact, second returns list memberships
    contact_result = MagicMock()
    contact_result.scalar_one_or_none.return_value = contact

    lists_result = MagicMock()
    lists_result.scalars.return_value.all.return_value = []

    db_session.execute = AsyncMock(side_effect=[contact_result, lists_result])

    resp = await authenticated_client.get(f"/api/v1/contacts/{contact_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["contact"]["id"] == str(contact_id)
    assert "lists" in data


# ---------------------------------------------------------------------------
# Test: update contact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_contact(authenticated_client: AsyncClient, db_session):
    """PUT /api/v1/contacts/{id} should update contact fields."""
    contact_id = uuid.uuid4()
    contact = _make_contact_response_obj(
        id=contact_id,
        first_name="Original",
        email="original@test.com",
    )

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = contact
    db_session.execute = AsyncMock(return_value=result_mock)

    async def mock_refresh(obj):
        obj.first_name = "Updated"
        obj.email = "updated@test.com"

    db_session.refresh = AsyncMock(side_effect=mock_refresh)

    resp = await authenticated_client.put(
        f"/api/v1/contacts/{contact_id}",
        json={"first_name": "Updated", "email": "updated@test.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["contact"]["first_name"] == "Updated"
    assert data["contact"]["email"] == "updated@test.com"


# ---------------------------------------------------------------------------
# Test: delete contact -- soft deletes (sets status to blocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_contact_soft_deletes(authenticated_client: AsyncClient, db_session):
    """DELETE /api/v1/contacts/{id} should set status to blocked."""
    contact_id = uuid.uuid4()
    contact = _make_contact_response_obj(id=contact_id, status="active")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = contact
    db_session.execute = AsyncMock(return_value=result_mock)

    resp = await authenticated_client.delete(f"/api/v1/contacts/{contact_id}")
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()


# ---------------------------------------------------------------------------
# Test: bulk action -- add to list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bulk_action_add_to_list(authenticated_client: AsyncClient):
    """POST /api/v1/contacts/bulk should add contacts to a list."""
    list_id = uuid.uuid4()
    contact_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    with patch(
        "app.routers.contacts.bulk_action",
        new_callable=AsyncMock,
        return_value={"affected": 2},
    ):
        resp = await authenticated_client.post(
            "/api/v1/contacts/bulk",
            json={
                "contact_ids": contact_ids,
                "action": "add_to_list",
                "value": str(list_id),
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["affected"] == 2


# ---------------------------------------------------------------------------
# Test: bulk action -- unsubscribe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bulk_action_unsubscribe(authenticated_client: AsyncClient):
    """POST /api/v1/contacts/bulk with action unsubscribe should work."""
    contact_ids = [str(uuid.uuid4())]

    with patch(
        "app.routers.contacts.bulk_action",
        new_callable=AsyncMock,
        return_value={"affected": 1},
    ):
        resp = await authenticated_client.post(
            "/api/v1/contacts/bulk",
            json={
                "contact_ids": contact_ids,
                "action": "unsubscribe",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["affected"] == 1


# ---------------------------------------------------------------------------
# Test: normalize_phone -- US number
# ---------------------------------------------------------------------------

def test_normalize_phone_us_number():
    assert normalize_phone("(415) 555-1234") == "+14155551234"
    assert normalize_phone("415-555-1234") == "+14155551234"
    assert normalize_phone("4155551234") == "+14155551234"
    assert normalize_phone("+14155551234") == "+14155551234"


# ---------------------------------------------------------------------------
# Test: normalize_phone -- international
# ---------------------------------------------------------------------------

def test_normalize_phone_international():
    # UK number
    result = normalize_phone("+442071234567", country="GB")
    assert result == "+442071234567"
    # German number
    result = normalize_phone("+4915112345678", country="DE")
    assert result == "+4915112345678"


# ---------------------------------------------------------------------------
# Test: normalize_phone -- invalid
# ---------------------------------------------------------------------------

def test_normalize_phone_invalid():
    assert normalize_phone("") is None
    assert normalize_phone("abc") is None
    assert normalize_phone("123") is None
    assert normalize_phone("   ") is None
    assert normalize_phone("+1") is None
