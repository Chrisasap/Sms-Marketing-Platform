"""Tests for app.services.webhook_handler -- webhook event processing."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.services.webhook_handler import (
    process_webhook,
    _handle_delivered,
    _handle_failed,
    _handle_received,
    _process_opt_out,
    OPT_OUT_KEYWORDS,
)
from tests.conftest import (
    make_test_contact,
    make_test_phone_number,
    make_test_tenant,
    TEST_TENANT_ID,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_delivered_event(bw_message_id: str = "bw-123") -> dict:
    return {
        "type": "message-delivered",
        "message": {
            "id": bw_message_id,
            "from": "+15559876543",
            "to": ["+15551234567"],
            "text": "Hello",
        },
    }


def _make_failed_event(
    bw_message_id: str = "bw-456",
    error_code: str = "4720",
    description: str = "Carrier rejected",
) -> dict:
    return {
        "type": "message-failed",
        "message": {
            "id": bw_message_id,
            "from": "+15559876543",
            "to": ["+15551234567"],
            "text": "Fail test",
        },
        "errorCode": error_code,
        "description": description,
    }


def _make_received_event(
    bw_message_id: str = "bw-in-789",
    from_number: str = "+15551234567",
    to_number: str = "+15559876543",
    text: str = "Hi there",
    media: list | None = None,
) -> dict:
    event = {
        "type": "message-received",
        "message": {
            "id": bw_message_id,
            "from": from_number,
            "to": [to_number],
            "text": text,
        },
    }
    if media:
        event["message"]["media"] = media
    return event


# ===========================================================================
# Delivery callbacks
# ===========================================================================


class TestHandleDelivered:
    """Tests for _handle_delivered."""

    @pytest.mark.asyncio
    async def test_handle_delivered_updates_campaign_message(self, db_session, override_settings):
        """A delivered callback should set status='delivered' on the campaign message."""
        bw_id = "bw-delivered-001"

        # Create a mock campaign message that will be "found"
        campaign_msg = MagicMock()
        campaign_msg.campaign_id = uuid.uuid4()
        campaign_msg.status = "sending"

        # _handle_delivered calls db.execute 3 times:
        # 1. select CampaignMessage -> found
        # 2. update Campaign counter (no scalar_one_or_none needed)
        # 3. select ConversationMessage -> not found
        select_campaign_msg = MagicMock()
        select_campaign_msg.scalar_one_or_none.return_value = campaign_msg
        update_result = MagicMock()  # update() result doesn't use scalar_one_or_none
        select_conv_msg = MagicMock()
        select_conv_msg.scalar_one_or_none.return_value = None

        db_session.execute = AsyncMock(
            side_effect=[select_campaign_msg, update_result, select_conv_msg]
        )

        await _handle_delivered(db_session, bw_id, _make_delivered_event(bw_id))

        assert campaign_msg.status == "delivered"
        assert campaign_msg.delivered_at is not None

    @pytest.mark.asyncio
    async def test_handle_delivered_no_matching_message(self, db_session, override_settings):
        """If no campaign or conversation message is found, nothing should crash."""
        bw_id = "bw-unknown-001"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await _handle_delivered(db_session, bw_id, _make_delivered_event(bw_id))


# ===========================================================================
# Failure callbacks
# ===========================================================================


class TestHandleFailed:
    """Tests for _handle_failed."""

    @pytest.mark.asyncio
    async def test_handle_failed_updates_status_and_error(self, db_session, override_settings):
        """A failure callback should set status='failed' with error details."""
        bw_id = "bw-fail-001"

        campaign_msg = MagicMock()
        campaign_msg.campaign_id = uuid.uuid4()
        campaign_msg.status = "sending"

        # _handle_failed calls db.execute 3 times:
        # 1. select CampaignMessage -> found
        # 2. update Campaign counter
        # 3. select ConversationMessage -> not found
        select_campaign_msg = MagicMock()
        select_campaign_msg.scalar_one_or_none.return_value = campaign_msg
        update_result = MagicMock()
        select_conv_msg = MagicMock()
        select_conv_msg.scalar_one_or_none.return_value = None

        db_session.execute = AsyncMock(
            side_effect=[select_campaign_msg, update_result, select_conv_msg]
        )

        event = _make_failed_event(bw_id, error_code="4720", description="Carrier rejected")
        await _handle_failed(db_session, bw_id, event)

        assert campaign_msg.status == "failed"
        assert campaign_msg.error_code == "4720"
        assert campaign_msg.error_description == "Carrier rejected"
        assert campaign_msg.failed_at is not None


# ===========================================================================
# Inbound message handling
# ===========================================================================


class TestHandleReceived:
    """Tests for _handle_received (inbound messages).

    Since _handle_received uses real SQLAlchemy select() statements with ORM
    models, we cannot patch the model classes directly.  Instead we mock
    db.execute to return the right objects, and let the service construct
    new model instances normally (they just get added to our mock session).
    """

    @pytest.mark.asyncio
    async def test_handle_received_creates_conversation(self, db_session, override_settings):
        """An inbound message for a known number with no existing conversation
        should create a new contact (if needed) and a new conversation."""
        phone = make_test_phone_number(number="+15559876543")

        # _handle_received calls db.execute 3 times:
        # 1. PhoneNumber lookup -> found
        # 2. Contact lookup -> not found (will create)
        # 3. Conversation lookup -> not found (will create)
        execute_results = [
            MagicMock(**{"scalar_one_or_none.return_value": phone}),
            MagicMock(**{"scalar_one_or_none.return_value": None}),
            MagicMock(**{"scalar_one_or_none.return_value": None}),
        ]
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            idx = min(call_count[0], len(execute_results) - 1)
            call_count[0] += 1
            return execute_results[idx]

        db_session.execute = AsyncMock(side_effect=mock_execute)

        # db.flush() normally populates column defaults.  Simulate that by
        # setting message_count=0 on any added Contact objects after flush.
        added_objects = db_session._added_objects

        async def mock_flush():
            for obj in added_objects:
                if hasattr(obj, "message_count") and obj.message_count is None:
                    obj.message_count = 0

        db_session.flush = AsyncMock(side_effect=mock_flush)

        event = _make_received_event(
            from_number="+15551234567",
            to_number="+15559876543",
            text="Hey, first message!",
        )

        await _handle_received(db_session, event)

        # Should have added: Contact, Conversation, Message
        assert db_session.add.call_count >= 3
        # At least 2 flush calls (contact + conversation)
        assert db_session.flush.await_count >= 2

    @pytest.mark.asyncio
    async def test_handle_received_existing_conversation(self, db_session, override_settings):
        """An inbound message with an existing conversation should reuse it and increment unread."""
        phone = make_test_phone_number(number="+15559876543")
        contact = make_test_contact(phone_number="+15551234567")

        existing_conv = MagicMock()
        existing_conv.id = uuid.uuid4()
        existing_conv.status = "open"
        existing_conv.unread_count = 2
        existing_conv.last_message_at = None

        execute_results = [
            MagicMock(**{"scalar_one_or_none.return_value": phone}),
            MagicMock(**{"scalar_one_or_none.return_value": contact}),
            MagicMock(**{"scalar_one_or_none.return_value": existing_conv}),
        ]
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            idx = min(call_count[0], len(execute_results) - 1)
            call_count[0] += 1
            return execute_results[idx]

        db_session.execute = AsyncMock(side_effect=mock_execute)

        event = _make_received_event(
            from_number="+15551234567",
            to_number="+15559876543",
            text="Another message",
        )

        await _handle_received(db_session, event)

        # Should increment unread and update message count
        assert existing_conv.unread_count == 3
        assert contact.message_count == 1

    @pytest.mark.asyncio
    async def test_handle_received_unknown_number(self, db_session, override_settings):
        """An inbound message for an unrecognized 'to' number should be silently ignored."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        event = _make_received_event(
            to_number="+15550000000",  # not in our system
            text="Hey",
        )
        # Should not raise, just return
        await _handle_received(db_session, event)
        # No contact or conversation should be created
        db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_received_reopens_closed_conversation(self, db_session, override_settings):
        """An inbound message on a closed conversation should reopen it."""
        phone = make_test_phone_number(number="+15559876543")
        contact = make_test_contact(phone_number="+15551234567")

        closed_conv = MagicMock()
        closed_conv.id = uuid.uuid4()
        closed_conv.status = "closed"
        closed_conv.unread_count = 0
        closed_conv.last_message_at = None

        execute_results = [
            MagicMock(**{"scalar_one_or_none.return_value": phone}),
            MagicMock(**{"scalar_one_or_none.return_value": contact}),
            MagicMock(**{"scalar_one_or_none.return_value": closed_conv}),
        ]
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            idx = min(call_count[0], len(execute_results) - 1)
            call_count[0] += 1
            return execute_results[idx]

        db_session.execute = AsyncMock(side_effect=mock_execute)

        event = _make_received_event(
            from_number="+15551234567",
            to_number="+15559876543",
            text="I'm back!",
        )

        await _handle_received(db_session, event)

        assert closed_conv.status == "open"


# ===========================================================================
# Opt-out handling
# ===========================================================================


class TestOptOut:
    """Tests for opt-out keyword processing."""

    @pytest.mark.asyncio
    async def test_handle_opt_out_stop_keyword(self, db_session, override_settings):
        """The keyword 'STOP' should mark the contact as unsubscribed."""
        phone = make_test_phone_number(number="+15559876543")
        contact = make_test_contact(phone_number="+15551234567", status="active")

        # _handle_received calls:
        # 1. PhoneNumber lookup -> found
        # Then detects opt-out keyword and calls _process_opt_out which calls:
        # 2. Contact lookup -> found
        execute_results = [
            MagicMock(**{"scalar_one_or_none.return_value": phone}),
            MagicMock(**{"scalar_one_or_none.return_value": contact}),
        ]
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            idx = min(call_count[0], len(execute_results) - 1)
            call_count[0] += 1
            return execute_results[idx]

        db_session.execute = AsyncMock(side_effect=mock_execute)

        event = _make_received_event(
            from_number="+15551234567",
            to_number="+15559876543",
            text="STOP",
        )

        await _handle_received(db_session, event)

        assert contact.status == "unsubscribed"
        assert contact.opted_out_at is not None

    @pytest.mark.asyncio
    async def test_handle_opt_out_unsubscribe_keyword(self, db_session, override_settings):
        """The keyword 'unsubscribe' should also trigger opt-out."""
        phone = make_test_phone_number(number="+15559876543")
        contact = make_test_contact(phone_number="+15551234567", status="active")

        execute_results = [
            MagicMock(**{"scalar_one_or_none.return_value": phone}),
            MagicMock(**{"scalar_one_or_none.return_value": contact}),
        ]
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            idx = min(call_count[0], len(execute_results) - 1)
            call_count[0] += 1
            return execute_results[idx]

        db_session.execute = AsyncMock(side_effect=mock_execute)

        event = _make_received_event(
            from_number="+15551234567",
            to_number="+15559876543",
            text="unsubscribe",
        )

        await _handle_received(db_session, event)

        assert contact.status == "unsubscribed"

    @pytest.mark.asyncio
    async def test_all_opt_out_keywords_recognized(self, override_settings):
        """All defined opt-out keywords should be in the set."""
        expected = {"stop", "unsubscribe", "cancel", "quit", "end"}
        assert OPT_OUT_KEYWORDS == expected


# ===========================================================================
# Full process_webhook (integration-style)
# ===========================================================================


class TestProcessWebhook:
    """Tests for the top-level process_webhook dispatcher."""

    @pytest.mark.asyncio
    async def test_idempotent_webhook_processing(self, db_session, override_settings):
        """process_webhook should log every event and commit even if the handler is a no-op."""
        event = _make_delivered_event("bw-idem-001")

        # All lookups return None (no matching messages, no duplicate webhook)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        await process_webhook(db_session, [event])

        # A WebhookLog should have been added via db.add()
        assert db_session.add.call_count >= 1
        # The added log should be marked as processed
        added_log = db_session.add.call_args_list[0][0][0]
        assert added_log.processed is True
        # Commit should have been called
        db_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_process_webhook_handles_multiple_events(self, db_session, override_settings):
        """Multiple events in one batch should each get their own WebhookLog entry."""
        events = [
            _make_delivered_event("bw-batch-1"),
            _make_failed_event("bw-batch-2"),
        ]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        await process_webhook(db_session, events)

        # Should have added a WebhookLog for each event (plus other db.add calls are ok)
        added_objects = [c[0][0] for c in db_session.add.call_args_list]
        webhook_logs = [o for o in added_objects if hasattr(o, 'event_type') and hasattr(o, 'bandwidth_message_id')]
        assert len(webhook_logs) >= 2

    @pytest.mark.asyncio
    async def test_process_webhook_catches_handler_errors(self, db_session, override_settings):
        """If a handler raises, the error should be logged but not propagate."""
        event = _make_delivered_event("bw-err-001")

        # First call is idempotency check (returns None = not duplicate),
        # subsequent calls raise to simulate handler failure
        idempotency_result = MagicMock()
        idempotency_result.scalar_one_or_none.return_value = None

        call_count = [0]
        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return idempotency_result  # idempotency check passes
            raise RuntimeError("DB down")  # handler calls fail

        db_session.execute = AsyncMock(side_effect=mock_execute)

        # Should not raise
        await process_webhook(db_session, [event])

        # The WebhookLog should have been added with error captured
        added_log = db_session.add.call_args_list[0][0][0]
        assert added_log.processing_error is not None
        assert "DB down" in added_log.processing_error
