"""Message sending service with rate limiting, segment calculation, and credit tracking."""

import uuid
import math
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.campaign_message import CampaignMessage
from app.models.contact import Contact
from app.models.phone_number import PhoneNumber
from app.models.tenant import Tenant
from app.models.billing_event import BillingEvent
from app.models.conversation import Conversation
from app.models.message import Message as ConversationMessage
from app.services.bandwidth import (
    bandwidth_client,
    BandwidthError,
    BandwidthRateLimitError,
)

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when a tenant does not have enough credits to send a message."""
    pass

# ---------------------------------------------------------------------------
# SMS segment calculation (GSM-7 vs UCS-2)
# ---------------------------------------------------------------------------

GSM7_MAX = 160
GSM7_MULTI_MAX = 153
UCS2_MAX = 70
UCS2_MULTI_MAX = 67

GSM7_CHARS = set(
    "@\u00a3$\u00a5\u00e8\u00e9\u00f9\u00ec\u00f2\u00c7\n\u00d8\u00f8\r\u00c5\u00e5"
    "\u0394_\u03a6\u0393\u039b\u03a9\u03a0\u03a8\u03a3\u0398\u039e "
    "\u00c6\u00e6\u00df\u00c9 !\"#\u00a4%&'()*+,-./0123456789:;<=>?"
    "\u00a1ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c4\u00d6\u00d1\u00dc\u00a7"
    "\u00bfabcdefghijklmnopqrstuvwxyz\u00e4\u00f6\u00f1\u00fc\u00e0"
)

# Extended GSM-7 characters that count as 2 code points in a segment
GSM7_EXTENDED = set("|^{}[]~\\€")


def calculate_segments(text: str) -> int:
    """Calculate the number of SMS segments for a message body.

    Uses GSM-7 encoding limits when all characters fit, otherwise UCS-2.
    """
    if not text:
        return 0

    is_gsm7 = all(c in GSM7_CHARS or c in GSM7_EXTENDED for c in text)

    if is_gsm7:
        # Extended chars occupy 2 character slots
        length = sum(2 if c in GSM7_EXTENDED else 1 for c in text)
        if length <= GSM7_MAX:
            return 1
        return math.ceil(length / GSM7_MULTI_MAX)
    else:
        length = len(text)
        if length <= UCS2_MAX:
            return 1
        return math.ceil(length / UCS2_MULTI_MAX)


# ---------------------------------------------------------------------------
# Merge-tag template rendering
# ---------------------------------------------------------------------------

def render_template(template: str, contact: Contact) -> str:
    """Render merge tags like ``{{first_name}}`` in a message template."""
    result = template
    result = result.replace("{{first_name}}", contact.first_name or "")
    result = result.replace("{{last_name}}", contact.last_name or "")
    result = result.replace("{{phone}}", contact.phone_number or "")
    result = result.replace("{{email}}", contact.email or "")
    # Support arbitrary custom fields stored in the contact's JSONB column
    if contact.custom_fields:
        for key, value in contact.custom_fields.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
    return result.strip()


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

# Per-segment carrier costs (platform marks up on top of these)
SMS_SEGMENT_COST = Decimal("0.005")
MMS_MESSAGE_COST = Decimal("0.015")


def calculate_cost(segments: int, is_mms: bool) -> Decimal:
    """Return the carrier cost for a message."""
    if is_mms:
        return MMS_MESSAGE_COST
    return SMS_SEGMENT_COST * segments


# ---------------------------------------------------------------------------
# Send a single message (outbound)
# ---------------------------------------------------------------------------

async def send_single_message(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    to_number: str,
    from_number: str,
    text: str,
    media_urls: list[str] | None = None,
    campaign_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    application_id: str | None = None,
) -> dict:
    """Send a single SMS/MMS, deducting credits and recording the event.

    Returns a dict with ``success``, ``message_id``, ``segments``, ``cost``.
    """
    segments = calculate_segments(text)
    is_mms = bool(media_urls)
    cost = calculate_cost(segments, is_mms)

    # ---- Tenant credit check ----
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise ValueError("Tenant not found")

    if tenant.credit_balance < cost and tenant.plan_tier == "free_trial":
        raise InsufficientCreditsError("Insufficient credits")

    # ---- Create a campaign message record when this send belongs to a campaign ----
    msg_record: CampaignMessage | None = None
    if campaign_id:
        msg_record = CampaignMessage(
            campaign_id=campaign_id,
            contact_id=contact_id,
            tenant_id=tenant_id,
            from_number=from_number,
            to_number=to_number,
            message_body=text,
            media_urls=media_urls or [],
            status="sending",
            segments=segments,
            cost=cost,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(msg_record)
        await db.flush()

    # ---- Call Bandwidth ----
    try:
        bw_response = await bandwidth_client.send_message(
            to=to_number,
            from_number=from_number,
            text=text,
            media_urls=media_urls,
            tag=str(campaign_id) if campaign_id else None,
            application_id=application_id,
        )

        bw_message_id = bw_response.get("id")

        if msg_record:
            msg_record.bandwidth_message_id = bw_message_id
            msg_record.status = "sending"

        # Deduct credits atomically
        deduct_result = await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id, Tenant.credit_balance >= cost)
            .values(credit_balance=Tenant.credit_balance - cost)
        )
        if deduct_result.rowcount == 0:
            # Could not deduct -- balance was insufficient (race condition guard)
            if tenant.plan_tier == "free_trial":
                raise InsufficientCreditsError("Insufficient credits")

        # Record billing event
        billing_event = BillingEvent(
            tenant_id=tenant_id,
            event_type="mms_sent" if is_mms else "sms_sent",
            quantity=segments,
            unit_cost=SMS_SEGMENT_COST if not is_mms else MMS_MESSAGE_COST,
            total_cost=cost,
            campaign_id=campaign_id,
        )
        db.add(billing_event)
        await db.commit()

        return {
            "success": True,
            "message_id": bw_message_id,
            "segments": segments,
            "cost": float(cost),
        }

    except BandwidthRateLimitError:
        if msg_record:
            msg_record.status = "queued"
            await db.commit()
        raise
    except BandwidthError as e:
        if msg_record:
            msg_record.status = "failed"
            msg_record.error_code = str(e.status_code)
            msg_record.error_description = e.message
            msg_record.failed_at = datetime.now(timezone.utc)
            await db.commit()
        raise


# ---------------------------------------------------------------------------
# Send an ad-hoc (non-campaign) reply from the inbox
# ---------------------------------------------------------------------------

async def send_inbox_reply(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    text: str,
    media_urls: list[str] | None = None,
) -> dict:
    """Send a reply within an existing inbox conversation.

    Creates the ``Message`` record, calls Bandwidth, and deducts credits.
    """
    # Load conversation with related phone number
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise ValueError("Conversation not found")

    # Resolve from-number
    pn_result = await db.execute(
        select(PhoneNumber).where(PhoneNumber.id == conversation.phone_number_id)
    )
    phone = pn_result.scalar_one_or_none()
    if not phone:
        raise ValueError("Phone number not found")

    segments = calculate_segments(text)
    is_mms = bool(media_urls)
    cost = calculate_cost(segments, is_mms)

    # Credit check
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise ValueError("Tenant not found")
    if tenant.credit_balance < cost and tenant.plan_tier == "free_trial":
        raise InsufficientCreditsError("Insufficient credits")

    # Create message record
    msg = ConversationMessage(
        conversation_id=conversation.id,
        tenant_id=tenant_id,
        direction="outbound",
        sender_type="user",
        sender_id=user_id,
        body=text,
        media_urls=media_urls or [],
        status="sending",
        segments=segments,
        cost=cost,
    )
    db.add(msg)
    await db.flush()

    try:
        bw_response = await bandwidth_client.send_message(
            to=conversation.contact_phone,
            from_number=phone.number,
            text=text,
            media_urls=media_urls,
        )

        bw_message_id = bw_response.get("id")
        msg.bandwidth_message_id = bw_message_id
        msg.status = "sending"

        # Deduct credits atomically
        deduct_result = await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id, Tenant.credit_balance >= cost)
            .values(credit_balance=Tenant.credit_balance - cost)
        )
        if deduct_result.rowcount == 0:
            if tenant.plan_tier == "free_trial":
                raise InsufficientCreditsError("Insufficient credits")

        # Billing
        billing_event = BillingEvent(
            tenant_id=tenant_id,
            event_type="mms_sent" if is_mms else "sms_sent",
            quantity=segments,
            unit_cost=SMS_SEGMENT_COST if not is_mms else MMS_MESSAGE_COST,
            total_cost=cost,
        )
        db.add(billing_event)

        # Update conversation timestamp
        conversation.last_message_at = datetime.now(timezone.utc)

        await db.commit()

        return {
            "success": True,
            "message_id": bw_message_id,
            "segments": segments,
            "cost": float(cost),
            "conversation_id": str(conversation.id),
        }

    except BandwidthError as e:
        msg.status = "failed"
        msg.error_code = str(e.status_code)
        await db.commit()
        raise
