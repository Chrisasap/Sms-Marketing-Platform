"""Tests for app.services.message_sender -- segment calculation, template rendering, sending."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.message_sender import (
    calculate_segments,
    calculate_cost,
    render_template,
    send_single_message,
    InsufficientCreditsError,
    SMS_SEGMENT_COST,
    MMS_MESSAGE_COST,
)
from tests.conftest import (
    make_test_tenant,
    make_test_contact,
    TEST_TENANT_ID,
)


# ===========================================================================
# Segment calculation
# ===========================================================================


class TestCalculateSegments:
    """Tests for the SMS segment counting logic."""

    def test_calculate_segments_short_sms(self):
        """A short GSM-7 message (<=160 chars) should be 1 segment."""
        text = "Hello, this is a test message."
        assert len(text) <= 160
        assert calculate_segments(text) == 1

    def test_calculate_segments_exactly_160(self):
        """Exactly 160 GSM-7 characters should be 1 segment."""
        text = "A" * 160
        assert calculate_segments(text) == 1

    def test_calculate_segments_long_sms(self):
        """A GSM-7 message longer than 160 chars requires multiple segments."""
        # 161 chars -> 2 segments (each multipart segment holds 153 chars)
        text = "A" * 161
        assert calculate_segments(text) == 2

        # 306 chars -> ceil(306/153) = 2 segments
        text = "B" * 306
        assert calculate_segments(text) == 2

        # 307 chars -> ceil(307/153) = 3 segments
        text = "C" * 307
        assert calculate_segments(text) == 3

    def test_calculate_segments_unicode(self):
        """Unicode (UCS-2) messages have different segment limits."""
        # Single emoji is UCS-2; <= 70 chars -> 1 segment
        text = "Hello " + "\U0001f600"  # smiley face
        assert calculate_segments(text) == 1

        # 71 UCS-2 characters -> 2 segments (each holds 67)
        text = "\U0001f600" * 71
        assert calculate_segments(text) == 2

    def test_calculate_segments_empty(self):
        """An empty message should return 0 segments."""
        assert calculate_segments("") == 0

    def test_calculate_segments_gsm7_extended_chars(self):
        """Extended GSM-7 chars (|, ^, {, etc.) count as 2 code-points."""
        # 80 pipe characters = 160 code-points -> 1 segment
        text = "|" * 80
        assert calculate_segments(text) == 1

        # 81 pipe characters = 162 code-points -> 2 segments
        text = "|" * 81
        assert calculate_segments(text) == 2

    def test_calculate_segments_mixed_gsm7_extended(self):
        """Mix of regular and extended GSM-7 chars."""
        # 150 regular + 5 extended = 150 + 10 = 160 -> 1 segment
        text = "A" * 150 + "|" * 5
        assert calculate_segments(text) == 1

        # 150 regular + 6 extended = 150 + 12 = 162 -> 2 segments
        text = "A" * 150 + "|" * 6
        assert calculate_segments(text) == 2


# ===========================================================================
# Cost calculation
# ===========================================================================


class TestCalculateCost:
    """Tests for calculate_cost."""

    def test_sms_cost_single_segment(self):
        """1 SMS segment should cost SMS_SEGMENT_COST."""
        assert calculate_cost(1, is_mms=False) == SMS_SEGMENT_COST

    def test_sms_cost_multiple_segments(self):
        """Multiple segments should multiply the per-segment cost."""
        assert calculate_cost(3, is_mms=False) == SMS_SEGMENT_COST * 3

    def test_mms_cost_flat(self):
        """MMS cost is flat regardless of segment count."""
        assert calculate_cost(1, is_mms=True) == MMS_MESSAGE_COST
        assert calculate_cost(5, is_mms=True) == MMS_MESSAGE_COST


# ===========================================================================
# Template rendering
# ===========================================================================


class TestRenderTemplate:
    """Tests for merge-tag template rendering."""

    def test_render_template_basic(self):
        """Standard merge tags should be replaced with contact fields."""
        contact = make_test_contact(
            first_name="Jane",
            last_name="Doe",
            phone_number="+15551234567",
            email="jane@example.com",
        )
        template = "Hi {{first_name}} {{last_name}}, your number is {{phone}}."
        result = render_template(template, contact)
        assert result == "Hi Jane Doe, your number is +15551234567."

    def test_render_template_missing_fields(self):
        """Missing contact fields should be replaced with empty strings."""
        contact = make_test_contact(first_name=None, last_name=None, email=None)
        template = "Hello {{first_name}}, email: {{email}}"
        result = render_template(template, contact)
        assert result == "Hello , email:"

    def test_render_template_custom_fields(self):
        """Custom fields from the contact's JSONB column should be interpolated."""
        contact = make_test_contact(
            first_name="Alice",
            custom_fields={"company": "Acme Corp", "order_id": "12345"},
        )
        template = "Hi {{first_name}}, your order {{order_id}} at {{company}} shipped!"
        result = render_template(template, contact)
        assert result == "Hi Alice, your order 12345 at Acme Corp shipped!"

    def test_render_template_no_merge_tags(self):
        """A template without merge tags should be returned unchanged (stripped)."""
        contact = make_test_contact()
        template = "  Plain message with no tags.  "
        result = render_template(template, contact)
        assert result == "Plain message with no tags."

    def test_render_template_email_tag(self):
        """The {{email}} tag should render correctly."""
        contact = make_test_contact(email="user@test.com")
        template = "Reply to {{email}}"
        result = render_template(template, contact)
        assert result == "Reply to user@test.com"


# ===========================================================================
# send_single_message
# ===========================================================================


class TestSendSingleMessage:
    """Tests for the send_single_message function (mocked Bandwidth + DB)."""

    @pytest.mark.asyncio
    async def test_send_single_message_success(self, db_session, override_settings):
        """Successful send should return message_id, segments, and cost."""
        tenant = make_test_tenant(credit_balance=Decimal("10.0000"))

        # Mock db.execute to return the tenant on lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = tenant
        db_session.execute = AsyncMock(return_value=mock_result)

        bw_response = {"id": "bw-msg-001"}
        with patch(
            "app.services.message_sender.bandwidth_client"
        ) as mock_bw:
            mock_bw.send_message = AsyncMock(return_value=bw_response)

            result = await send_single_message(
                db=db_session,
                tenant_id=tenant.id,
                to_number="+15551234567",
                from_number="+15559876543",
                text="Hello from BlastWave!",
            )

        assert result["success"] is True
        assert result["message_id"] == "bw-msg-001"
        assert result["segments"] == 1
        assert result["cost"] == float(SMS_SEGMENT_COST)
        db_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_send_message_insufficient_credits(self, db_session, override_settings):
        """A free-trial tenant with 0 credits should get a ValueError."""
        tenant = make_test_tenant(
            credit_balance=Decimal("0.0000"),
            plan_tier="free_trial",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = tenant
        db_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(InsufficientCreditsError, match="Insufficient credits"):
            await send_single_message(
                db=db_session,
                tenant_id=tenant.id,
                to_number="+15551234567",
                from_number="+15559876543",
                text="This should fail",
            )

    @pytest.mark.asyncio
    async def test_send_message_tenant_not_found(self, db_session, override_settings):
        """A missing tenant should raise ValueError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Tenant not found"):
            await send_single_message(
                db=db_session,
                tenant_id=uuid.uuid4(),
                to_number="+15551234567",
                from_number="+15559876543",
                text="No tenant",
            )

    @pytest.mark.asyncio
    async def test_send_mms_cost_calculation(self, db_session, override_settings):
        """Sending with media_urls should use MMS pricing."""
        tenant = make_test_tenant(credit_balance=Decimal("10.0000"))

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = tenant
        db_session.execute = AsyncMock(return_value=mock_result)

        bw_response = {"id": "bw-mms-001"}
        with patch(
            "app.services.message_sender.bandwidth_client"
        ) as mock_bw:
            mock_bw.send_message = AsyncMock(return_value=bw_response)

            result = await send_single_message(
                db=db_session,
                tenant_id=tenant.id,
                to_number="+15551234567",
                from_number="+15559876543",
                text="Picture!",
                media_urls=["https://example.com/photo.jpg"],
            )

        assert result["success"] is True
        assert result["cost"] == float(MMS_MESSAGE_COST)

    @pytest.mark.asyncio
    async def test_send_paid_tier_allows_zero_credits(self, db_session, override_settings):
        """A paid-tier tenant with 0 credits should still be able to send."""
        tenant = make_test_tenant(
            credit_balance=Decimal("0.0000"),
            plan_tier="starter",  # not free_trial
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = tenant
        db_session.execute = AsyncMock(return_value=mock_result)

        bw_response = {"id": "bw-paid-001"}
        with patch(
            "app.services.message_sender.bandwidth_client"
        ) as mock_bw:
            mock_bw.send_message = AsyncMock(return_value=bw_response)

            result = await send_single_message(
                db=db_session,
                tenant_id=tenant.id,
                to_number="+15551234567",
                from_number="+15559876543",
                text="Paid tier send",
            )

        assert result["success"] is True
