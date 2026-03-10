"""Contact list management tests -- CRUD, add/remove members, pagination.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_TENANT_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_list_obj(**overrides):
    """Create a MagicMock contact list that passes Pydantic model_validate."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "name": "Test List",
        "description": "Test description",
        "tag_color": "#3b82f6",
        "contact_count": 0,
        "is_smart": False,
        "smart_filter": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_contact_obj(**overrides):
    """Create a MagicMock contact for list membership tests."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "phone_number": "+15551234567",
        "email": "test@test.com",
        "first_name": "Test",
        "last_name": "Contact",
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
# Test: create list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_list(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/lists/ should create a new contact list."""
    new_list = _make_list_obj(
        name="VIP Customers",
        description="High-value contacts",
        tag_color="#00ff00",
        contact_count=0,
    )

    with patch("app.routers.lists.ContactList") as MockList:
        MockList.return_value = new_list
        db_session.refresh = AsyncMock()

        resp = await authenticated_client.post(
            "/api/v1/lists/",
            json={
                "name": "VIP Customers",
                "description": "High-value contacts",
                "tag_color": "#00ff00",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["list"]["name"] == "VIP Customers"
    assert data["list"]["tag_color"] == "#00ff00"
    assert data["list"]["contact_count"] == 0


# ---------------------------------------------------------------------------
# Test: list all lists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_all_lists(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/lists/ should return all lists."""
    existing = _make_list_obj(name="Existing List")

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [existing]

    db_session.execute = AsyncMock(side_effect=[count_result, data_result])

    resp = await authenticated_client.get("/api/v1/lists/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["lists"]) >= 1
    list_names = [l["name"] for l in data["lists"]]
    assert "Existing List" in list_names


# ---------------------------------------------------------------------------
# Test: add contacts to list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_contacts_to_list(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/lists/{id}/contacts should add contacts."""
    list_id = uuid.uuid4()
    clist = _make_list_obj(id=list_id, contact_count=0)

    contact_ids = [uuid.uuid4() for _ in range(3)]

    # Calls: 1) _get_list_or_404, 2) validate contacts, 3-5) check existing membership each
    list_result = MagicMock()
    list_result.scalar_one_or_none.return_value = clist

    valid_result = MagicMock()
    valid_result.__iter__ = lambda self: iter([(cid,) for cid in contact_ids])

    no_member = MagicMock()
    no_member.scalar_one_or_none.return_value = None

    db_session.execute = AsyncMock(
        side_effect=[list_result, valid_result, no_member, no_member, no_member]
    )

    resp = await authenticated_client.post(
        f"/api/v1/lists/{list_id}/contacts",
        json={"contact_ids": [str(cid) for cid in contact_ids]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["added"] == 3


# ---------------------------------------------------------------------------
# Test: remove contacts from list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_remove_contacts_from_list(authenticated_client: AsyncClient, db_session):
    """DELETE /api/v1/lists/{id}/contacts should remove contacts."""
    list_id = uuid.uuid4()
    clist = _make_list_obj(id=list_id, contact_count=2)

    # _get_list_or_404 result
    list_result = MagicMock()
    list_result.scalar_one_or_none.return_value = clist

    # delete result
    delete_result = MagicMock()
    delete_result.rowcount = 1

    # count result after removal
    count_result = MagicMock()
    count_result.scalar.return_value = 1

    db_session.execute = AsyncMock(side_effect=[list_result, delete_result, count_result])

    remove_ids = [str(uuid.uuid4())]

    resp = await authenticated_client.request(
        "DELETE",
        f"/api/v1/lists/{list_id}/contacts",
        json={"contact_ids": remove_ids},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["removed"] == 1


# ---------------------------------------------------------------------------
# Test: delete list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_list(authenticated_client: AsyncClient, db_session):
    """DELETE /api/v1/lists/{id} should delete the list."""
    list_id = uuid.uuid4()
    clist = _make_list_obj(id=list_id)

    list_result = MagicMock()
    list_result.scalar_one_or_none.return_value = clist

    # delete members execute, then db.delete is called separately
    delete_result = MagicMock()
    db_session.execute = AsyncMock(side_effect=[list_result, delete_result])
    db_session.delete = AsyncMock()

    resp = await authenticated_client.delete(f"/api/v1/lists/{list_id}")
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()


# ---------------------------------------------------------------------------
# Test: get list contacts paginated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_list_contacts_paginated(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/lists/{id}/contacts?page=1&per_page=1 should paginate."""
    list_id = uuid.uuid4()
    clist = _make_list_obj(id=list_id, contact_count=2)
    contact = _make_contact_obj()

    # _get_list_or_404
    list_result = MagicMock()
    list_result.scalar_one_or_none.return_value = clist

    # count
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    # data
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [contact]

    db_session.execute = AsyncMock(side_effect=[list_result, count_result, data_result])

    resp = await authenticated_client.get(
        f"/api/v1/lists/{list_id}/contacts?page=1&per_page=1"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["per_page"] == 1
    assert len(data["contacts"]) <= 1
    assert data["total"] == 2
