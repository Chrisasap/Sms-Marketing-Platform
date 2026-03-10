"""Inbox tests -- conversations, messages, replies, close, assign, internal notes.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conversation_obj(**overrides):
    """Create a MagicMock conversation object."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "contact_id": uuid.uuid4(),
        "phone_number_id": uuid.uuid4(),
        "contact_phone": "+14155551234",
        "status": "open",
        "assigned_to": None,
        "unread_count": 0,
        "tags": [],
        "last_message_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    # contact relationship
    if "contact" not in overrides:
        contact = MagicMock()
        contact.first_name = "Inbox"
        contact.last_name = "Contact"
        contact.phone_number = defaults["contact_phone"]
        contact.status = "active"
        obj.contact = contact
    # assigned_user relationship
    obj.assigned_user = None
    return obj


def _make_message_obj(index=0, direction="inbound", **overrides):
    """Create a MagicMock message object."""
    defaults = {
        "id": uuid.uuid4(),
        "conversation_id": uuid.uuid4(),
        "tenant_id": TEST_TENANT_ID,
        "direction": direction,
        "sender_type": "contact" if direction == "inbound" else "user",
        "sender_id": None,
        "body": f"Message {index}: {direction}",
        "media_urls": [],
        "bandwidth_message_id": None,
        "status": "delivered",
        "error_code": None,
        "segments": 1,
        "cost": Decimal("0.005"),
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# Test: list conversations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_conversations(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/inbox/ should list conversations."""
    conv = _make_conversation_obj()

    # count query
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    # data query
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [conv]

    # last message preview query
    last_msg_result = MagicMock()
    last_msg_result.scalar_one_or_none.return_value = "Hello there"

    db_session.execute = AsyncMock(
        side_effect=[count_result, data_result, last_msg_result]
    )

    resp = await authenticated_client.get("/api/v1/inbox/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "conversations" in data
    assert data["page"] == 1


# ---------------------------------------------------------------------------
# Test: get conversation messages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_conversation_messages(authenticated_client: AsyncClient, db_session):
    """GET /api/v1/inbox/{id}/messages should return paginated messages."""
    conv_id = uuid.uuid4()
    messages = [
        _make_message_obj(0, "inbound", conversation_id=conv_id),
        _make_message_obj(1, "outbound", conversation_id=conv_id),
        _make_message_obj(2, "inbound", conversation_id=conv_id),
    ]

    # verify conversation exists
    conv_check = MagicMock()
    conv_check.scalar_one_or_none.return_value = conv_id

    # count
    count_result = MagicMock()
    count_result.scalar.return_value = 3

    # messages
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = messages

    # conversation update (unread reset)
    conv_obj = _make_conversation_obj(id=conv_id, unread_count=2)
    conv_update_result = MagicMock()
    conv_update_result.scalar_one_or_none.return_value = conv_obj

    db_session.execute = AsyncMock(
        side_effect=[conv_check, count_result, data_result, conv_update_result]
    )

    resp = await authenticated_client.get(f"/api/v1/inbox/{conv_id}/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["messages"]) == 3
    assert "Message 0" in data["messages"][0]["body"]


# ---------------------------------------------------------------------------
# Test: reply to conversation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reply_to_conversation(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/inbox/{id}/reply should send a reply."""
    conv_id = uuid.uuid4()
    conv = _make_conversation_obj(id=conv_id)

    # verify conversation
    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    # contact check (not unsubscribed)
    contact = MagicMock()
    contact.status = "active"
    contact_result = MagicMock()
    contact_result.scalar_one_or_none.return_value = contact

    db_session.execute = AsyncMock(side_effect=[conv_result, contact_result])

    mock_reply_result = {
        "message_id": str(uuid.uuid4()),
        "status": "sent",
        "body": "Hello back!",
    }

    with patch(
        "app.routers.inbox.send_inbox_reply",
        new_callable=AsyncMock,
        return_value=mock_reply_result,
    ) as mock_send:
        resp = await authenticated_client.post(
            f"/api/v1/inbox/{conv_id}/reply",
            json={"body": "Hello back!", "media_urls": []},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "sent"
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# Test: close conversation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_close_conversation(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/inbox/{id}/close should close an open conversation."""
    conv_id = uuid.uuid4()
    conv = _make_conversation_obj(id=conv_id, status="open")

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    db_session.execute = AsyncMock(return_value=conv_result)

    resp = await authenticated_client.post(f"/api/v1/inbox/{conv_id}/close")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"
    assert "closed" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test: close already-closed conversation returns 400
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_close_already_closed_conversation(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/inbox/{id}/close on a closed conv should return 400."""
    conv_id = uuid.uuid4()
    conv = _make_conversation_obj(id=conv_id, status="closed")

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    db_session.execute = AsyncMock(return_value=conv_result)

    resp = await authenticated_client.post(f"/api/v1/inbox/{conv_id}/close")
    assert resp.status_code == 400
    assert "already closed" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test: assign conversation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assign_conversation(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/inbox/{id}/assign should assign a user."""
    conv_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    conv = _make_conversation_obj(id=conv_id)

    # conversation lookup
    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    # assignee validation
    assignee = MagicMock()
    assignee.id = user2_id
    assignee_result = MagicMock()
    assignee_result.scalar_one_or_none.return_value = assignee

    db_session.execute = AsyncMock(side_effect=[conv_result, assignee_result])

    resp = await authenticated_client.post(
        f"/api/v1/inbox/{conv_id}/assign",
        json={"user_id": str(user2_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned_to"] == str(user2_id)
    assert "assigned" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test: unassign conversation (null user_id)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unassign_conversation(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/inbox/{id}/assign with null should unassign."""
    conv_id = uuid.uuid4()
    conv = _make_conversation_obj(id=conv_id, assigned_to=uuid.uuid4())

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    db_session.execute = AsyncMock(return_value=conv_result)

    resp = await authenticated_client.post(
        f"/api/v1/inbox/{conv_id}/assign",
        json={"user_id": None},
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] is None


# ---------------------------------------------------------------------------
# Test: add internal note
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_internal_note(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/inbox/{id}/note should add an internal note."""
    conv_id = uuid.uuid4()
    conv = _make_conversation_obj(id=conv_id)

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    note_id = uuid.uuid4()
    note = MagicMock()
    note.id = note_id
    note.conversation_id = conv_id
    note.sender_type = "system"
    note.sender_id = TEST_USER_ID
    note.body = "This is an internal note for context."
    note.created_at = datetime.now(timezone.utc)

    db_session.execute = AsyncMock(return_value=conv_result)

    # Patch Message constructor
    with patch("app.routers.inbox.Message") as MockMessage:
        MockMessage.return_value = note
        db_session.refresh = AsyncMock()

        resp = await authenticated_client.post(
            f"/api/v1/inbox/{conv_id}/note",
            json={"body": "This is an internal note for context."},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["sender_type"] == "system"
    assert data["body"] == "This is an internal note for context."
    assert "note added" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test: add internal note -- empty body fails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_internal_note_empty_body(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/inbox/{id}/note with empty body should return 400."""
    conv_id = uuid.uuid4()
    conv = _make_conversation_obj(id=conv_id)

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    db_session.execute = AsyncMock(return_value=conv_result)

    resp = await authenticated_client.post(
        f"/api/v1/inbox/{conv_id}/note",
        json={"body": ""},
    )
    assert resp.status_code == 400
    assert "required" in resp.json()["detail"].lower()
