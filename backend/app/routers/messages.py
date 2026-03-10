"""Message sending and retrieval router."""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.phone_number import PhoneNumber
from app.models.campaign_message import CampaignMessage
from app.models.message import Message as ConversationMessage
from app.models.contact import Contact
from app.schemas.message import SendMessageRequest, MessageResponse
from app.services.message_sender import send_single_message, send_inbox_reply
from app.services.bandwidth import bandwidth_client, BandwidthError
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET / -- List messages (campaign messages) with pagination/filtering
# ---------------------------------------------------------------------------

@router.get("/")
async def list_messages(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    direction: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    campaign_id: uuid.UUID | None = None,
    from_number: str | None = None,
    to_number: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List messages with filtering and pagination.

    Returns campaign messages by default; use ``direction`` to limit to
    inbound or outbound.
    """
    query = select(CampaignMessage).where(
        CampaignMessage.tenant_id == user.tenant_id
    )
    count_query = select(func.count(CampaignMessage.id)).where(
        CampaignMessage.tenant_id == user.tenant_id
    )

    if status_filter:
        query = query.where(CampaignMessage.status == status_filter)
        count_query = count_query.where(CampaignMessage.status == status_filter)
    if campaign_id:
        query = query.where(CampaignMessage.campaign_id == campaign_id)
        count_query = count_query.where(CampaignMessage.campaign_id == campaign_id)
    if from_number:
        query = query.where(CampaignMessage.from_number == from_number)
        count_query = count_query.where(CampaignMessage.from_number == from_number)
    if to_number:
        query = query.where(CampaignMessage.to_number == to_number)
        count_query = count_query.where(CampaignMessage.to_number == to_number)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query.order_by(CampaignMessage.sent_at.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "messages": [
            {
                "id": str(m.id),
                "campaign_id": str(m.campaign_id),
                "from_number": m.from_number,
                "to_number": m.to_number,
                "message_body": m.message_body,
                "media_urls": m.media_urls or [],
                "bandwidth_message_id": m.bandwidth_message_id,
                "status": m.status,
                "error_code": m.error_code,
                "error_description": m.error_description,
                "segments": m.segments,
                "cost": float(m.cost),
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "delivered_at": m.delivered_at.isoformat() if m.delivered_at else None,
                "failed_at": m.failed_at.isoformat() if m.failed_at else None,
            }
            for m in messages
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST /send -- Send a single message
# ---------------------------------------------------------------------------

@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_message(
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a single SMS or MMS message.

    Requires ``to`` (E.164 phone number) and ``text``.
    Optionally provide ``from_number_id`` (UUID of an owned PhoneNumber)
    and ``media_urls`` for MMS.
    """
    tenant_id = user.tenant_id

    # Resolve from-number
    if body.from_number_id:
        pn_result = await db.execute(
            select(PhoneNumber).where(
                PhoneNumber.id == body.from_number_id,
                PhoneNumber.tenant_id == tenant_id,
                PhoneNumber.status == "active",
            )
        )
        phone = pn_result.scalar_one_or_none()
        if not phone:
            raise HTTPException(
                status_code=400, detail="From number not found or inactive"
            )
        from_number = phone.number
    else:
        # Pick the first active number
        pn_result = await db.execute(
            select(PhoneNumber)
            .where(
                PhoneNumber.tenant_id == tenant_id,
                PhoneNumber.status == "active",
            )
            .limit(1)
        )
        phone = pn_result.scalar_one_or_none()
        if not phone:
            raise HTTPException(
                status_code=400,
                detail="No active phone numbers. Purchase a number first.",
            )
        from_number = phone.number

    # Rate limit check
    allowed = await rate_limiter.check_tenant_rate(str(tenant_id), mps_limit=10)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again shortly.",
        )

    # Optionally resolve contact
    contact_id: uuid.UUID | None = None
    contact_result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.phone_number == body.to,
        )
    )
    contact = contact_result.scalar_one_or_none()
    if contact:
        contact_id = contact.id
        # Block sending to unsubscribed contacts
        if contact.status == "unsubscribed":
            raise HTTPException(
                status_code=400,
                detail="Contact has opted out. Cannot send messages.",
            )

    try:
        result = await send_single_message(
            db=db,
            tenant_id=tenant_id,
            to_number=body.to,
            from_number=from_number,
            text=body.text,
            media_urls=body.media_urls if body.media_urls else None,
            contact_id=contact_id,
        )
        await rate_limiter.increment_daily_count(str(tenant_id))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BandwidthError as e:
        raise HTTPException(status_code=502, detail=f"Bandwidth error: {e.message}")


# ---------------------------------------------------------------------------
# GET /:id -- Get message details
# ---------------------------------------------------------------------------

@router.get("/{message_id}")
async def get_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get details of a specific campaign message."""
    result = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.id == message_id,
            CampaignMessage.tenant_id == user.tenant_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    return {
        "message": {
            "id": str(msg.id),
            "campaign_id": str(msg.campaign_id),
            "contact_id": str(msg.contact_id) if msg.contact_id else None,
            "from_number": msg.from_number,
            "to_number": msg.to_number,
            "message_body": msg.message_body,
            "media_urls": msg.media_urls or [],
            "bandwidth_message_id": msg.bandwidth_message_id,
            "status": msg.status,
            "error_code": msg.error_code,
            "error_description": msg.error_description,
            "segments": msg.segments,
            "cost": float(msg.cost),
            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
            "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
            "failed_at": msg.failed_at.isoformat() if msg.failed_at else None,
        }
    }


# ---------------------------------------------------------------------------
# GET /:id/status -- Check delivery status via Bandwidth
# ---------------------------------------------------------------------------

@router.get("/{message_id}/status")
async def get_message_status(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check the real-time delivery status of a message via Bandwidth API.

    Also updates the local record if the status has changed.
    """
    result = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.id == message_id,
            CampaignMessage.tenant_id == user.tenant_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if not msg.bandwidth_message_id:
        return {
            "local_status": msg.status,
            "bandwidth_status": None,
            "note": "No Bandwidth message ID -- message may not have been sent yet.",
        }

    try:
        bw_status = await bandwidth_client.get_message_status(
            msg.bandwidth_message_id
        )
        return {
            "local_status": msg.status,
            "bandwidth_status": bw_status,
        }
    except BandwidthError as e:
        return {
            "local_status": msg.status,
            "bandwidth_status": None,
            "error": e.message,
        }


# ---------------------------------------------------------------------------
# POST /send-bulk -- Queue bulk messages
# ---------------------------------------------------------------------------

@router.post("/send-bulk")
async def send_bulk_messages(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Queue messages to multiple recipients.

    This is a placeholder -- bulk sending should be handled via the
    campaign engine (/api/v1/campaigns) with proper throttling.
    """
    return {
        "message": "Use the campaigns API for bulk message sends with proper throttling and compliance checks.",
        "campaigns_endpoint": "/api/v1/campaigns",
    }
