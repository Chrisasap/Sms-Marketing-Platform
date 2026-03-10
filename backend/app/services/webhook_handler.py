"""Process inbound Bandwidth webhook callbacks (delivery receipts + inbound messages)."""

import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.campaign_message import CampaignMessage
from app.models.campaign import Campaign
from app.models.conversation import Conversation
from app.models.message import Message as ConversationMessage
from app.models.contact import Contact
from app.models.phone_number import PhoneNumber
from app.models.opt_out_log import OptOutLog
from app.models.webhook_log import WebhookLog

logger = logging.getLogger(__name__)

OPT_OUT_KEYWORDS = {"stop", "unsubscribe", "cancel", "quit", "end"}
HELP_KEYWORDS = {"help", "info"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def process_webhook(db: AsyncSession, events: list[dict]) -> None:
    """Process a batch of Bandwidth webhook events.

    Bandwidth posts an array of callback objects.  Each is dispatched to the
    appropriate handler based on the ``type`` field.
    """
    for event in events:
        event_type = event.get("type", "")
        message_data = event.get("message", {})
        bw_message_id = message_data.get("id", "")

        # ---- Idempotency check: skip if we already processed this
        # bandwidth_message_id + event_type combination ----
        if bw_message_id:
            existing = await db.execute(
                select(WebhookLog).where(
                    WebhookLog.bandwidth_message_id == bw_message_id,
                    WebhookLog.event_type == event_type,
                    WebhookLog.processed == True,
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(
                    "Duplicate webhook skipped: %s for %s",
                    event_type,
                    bw_message_id,
                )
                continue

        # Persist every callback for debugging / audit
        log = WebhookLog(
            event_type=event_type,
            bandwidth_message_id=bw_message_id,
            payload=event,
            processed=False,
        )
        db.add(log)

        try:
            if event_type == "message-delivered":
                await _handle_delivered(db, bw_message_id, event)
            elif event_type == "message-failed":
                await _handle_failed(db, bw_message_id, event)
            elif event_type == "message-sending":
                await _handle_sending(db, bw_message_id, event)
            elif event_type == "message-received":
                await _handle_received(db, event)
            else:
                logger.debug("Unhandled webhook type: %s", event_type)

            log.processed = True
        except Exception as e:
            logger.error(
                "Error processing webhook %s for %s: %s",
                event_type,
                bw_message_id,
                e,
            )
            log.processing_error = str(e)

        await db.commit()


# ---------------------------------------------------------------------------
# Outbound delivery callbacks
# ---------------------------------------------------------------------------

async def _handle_delivered(
    db: AsyncSession, bw_message_id: str, event: dict
) -> None:
    """Handle delivery confirmation for an outbound message."""
    # Update campaign message if present
    result = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.bandwidth_message_id == bw_message_id
        )
    )
    msg = result.scalar_one_or_none()
    if msg:
        msg.status = "delivered"
        msg.delivered_at = datetime.now(timezone.utc)
        # Atomically bump campaign counter
        await db.execute(
            update(Campaign)
            .where(Campaign.id == msg.campaign_id)
            .values(delivered_count=Campaign.delivered_count + 1)
        )

    # Also update conversation messages (inbox replies)
    conv_result = await db.execute(
        select(ConversationMessage).where(
            ConversationMessage.bandwidth_message_id == bw_message_id
        )
    )
    conv_msg = conv_result.scalar_one_or_none()
    if conv_msg:
        conv_msg.status = "delivered"


async def _handle_failed(
    db: AsyncSession, bw_message_id: str, event: dict
) -> None:
    """Handle delivery failure for an outbound message."""
    error_code = str(event.get("errorCode", ""))
    description = event.get("description", "")

    # Campaign message
    result = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.bandwidth_message_id == bw_message_id
        )
    )
    msg = result.scalar_one_or_none()
    if msg:
        msg.status = "failed"
        msg.error_code = error_code
        msg.error_description = description
        msg.failed_at = datetime.now(timezone.utc)
        await db.execute(
            update(Campaign)
            .where(Campaign.id == msg.campaign_id)
            .values(failed_count=Campaign.failed_count + 1)
        )

    # Conversation message
    conv_result = await db.execute(
        select(ConversationMessage).where(
            ConversationMessage.bandwidth_message_id == bw_message_id
        )
    )
    conv_msg = conv_result.scalar_one_or_none()
    if conv_msg:
        conv_msg.status = "failed"
        conv_msg.error_code = error_code


async def _handle_sending(
    db: AsyncSession, bw_message_id: str, event: dict
) -> None:
    """Handle intermediate "sending" status (mostly MMS)."""
    result = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.bandwidth_message_id == bw_message_id
        )
    )
    msg = result.scalar_one_or_none()
    if msg:
        msg.status = "sending"


# ---------------------------------------------------------------------------
# Inbound message handling
# ---------------------------------------------------------------------------

async def _handle_received(db: AsyncSession, event: dict) -> None:
    """Handle an inbound message from a subscriber."""
    message_data = event.get("message", {})
    from_number = message_data.get("from", "")
    to_numbers = message_data.get("to", [])
    to_number = to_numbers[0] if to_numbers else ""
    text = message_data.get("text", "")
    media = message_data.get("media", [])
    bw_message_id = message_data.get("id", "")

    # Resolve the tenant that owns the receiving number
    result = await db.execute(
        select(PhoneNumber).where(
            PhoneNumber.number == to_number,
            PhoneNumber.status == "active",
        )
    )
    phone = result.scalar_one_or_none()
    if not phone:
        logger.warning("Received message for unknown number: %s", to_number)
        return

    tenant_id = phone.tenant_id

    # ---- Opt-out keyword detection ----
    text_lower = text.strip().lower()
    if text_lower in OPT_OUT_KEYWORDS:
        await _process_opt_out(
            db, tenant_id, from_number, text_lower, bw_message_id
        )
        return

    # ---- Find or auto-create contact ----
    contact_result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.phone_number == from_number,
        )
    )
    contact = contact_result.scalar_one_or_none()
    if not contact:
        contact = Contact(
            tenant_id=tenant_id,
            phone_number=from_number,
            status="active",
            opted_in_at=datetime.now(timezone.utc),
            opt_in_method="inbound_message",
        )
        db.add(contact)
        await db.flush()

    # ---- Find or create conversation ----
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.contact_id == contact.id,
            Conversation.phone_number_id == phone.id,
            Conversation.status != "archived",
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(
            tenant_id=tenant_id,
            contact_id=contact.id,
            phone_number_id=phone.id,
            contact_phone=from_number,
            status="open",
            unread_count=0,
            tags=[],
        )
        db.add(conversation)
        await db.flush()

    # ---- Create inbound message record ----
    msg = ConversationMessage(
        conversation_id=conversation.id,
        tenant_id=tenant_id,
        direction="inbound",
        sender_type="contact",
        sender_id=contact.id,
        body=text,
        media_urls=media if media else [],
        bandwidth_message_id=bw_message_id,
        status="delivered",
        segments=1,
    )
    db.add(msg)

    # ---- Update conversation state ----
    conversation.last_message_at = datetime.now(timezone.utc)
    conversation.unread_count += 1
    if conversation.status == "closed":
        conversation.status = "open"

    # ---- Update contact stats ----
    contact.last_messaged_at = datetime.now(timezone.utc)
    contact.message_count += 1


# ---------------------------------------------------------------------------
# Opt-out processing
# ---------------------------------------------------------------------------

async def _process_opt_out(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    phone_number: str,
    keyword: str,
    bw_message_id: str,
) -> None:
    """Mark a contact as unsubscribed and log the opt-out event."""
    result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.phone_number == phone_number,
        )
    )
    contact = result.scalar_one_or_none()

    if contact:
        contact.status = "unsubscribed"
        contact.opted_out_at = datetime.now(timezone.utc)

    # Always log the opt-out, even if the contact wasn't previously known
    opt_out = OptOutLog(
        tenant_id=tenant_id,
        contact_id=contact.id if contact else None,
        phone_number=phone_number,
        keyword_used=keyword,
        bandwidth_message_id=bw_message_id,
    )
    db.add(opt_out)

    logger.info(
        "Opt-out processed for %s in tenant %s (keyword=%s)",
        phone_number,
        tenant_id,
        keyword,
    )
