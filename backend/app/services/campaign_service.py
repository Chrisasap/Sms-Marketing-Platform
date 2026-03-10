"""Campaign orchestration service -- create, launch, pause, resume, cancel, stats."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_message import CampaignMessage
from app.models.contact import Contact
from app.models.contact_list import ContactList
from app.models.contact_list_member import ContactListMember
from app.models.phone_number import PhoneNumber
from app.schemas.campaign import CampaignCreate, CampaignStats

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def create_campaign(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: CampaignCreate,
) -> Campaign:
    """Create a new campaign in *draft* status.

    Validates that all referenced target/exclude lists exist for the tenant
    and computes an estimated ``total_recipients`` count.
    """
    # Validate target lists
    if data.target_list_ids:
        result = await db.execute(
            select(func.count(ContactList.id)).where(
                and_(
                    ContactList.tenant_id == tenant_id,
                    ContactList.id.in_(data.target_list_ids),
                )
            )
        )
        found = result.scalar() or 0
        if found != len(data.target_list_ids):
            raise ValueError("One or more target lists not found")

    # Validate exclude lists
    if data.exclude_list_ids:
        result = await db.execute(
            select(func.count(ContactList.id)).where(
                and_(
                    ContactList.tenant_id == tenant_id,
                    ContactList.id.in_(data.exclude_list_ids),
                )
            )
        )
        found = result.scalar() or 0
        if found != len(data.exclude_list_ids):
            raise ValueError("One or more exclude lists not found")

    # Calculate estimated total recipients
    total_recipients = await _count_recipients(
        db, tenant_id, data.target_list_ids, data.exclude_list_ids
    )

    # Parse send window times
    send_window_start = None
    send_window_end = None
    if data.send_window_start:
        parts = data.send_window_start.split(":")
        send_window_start = datetime.strptime(data.send_window_start, "%H:%M").time()
    if data.send_window_end:
        send_window_end = datetime.strptime(data.send_window_end, "%H:%M").time()

    campaign = Campaign(
        tenant_id=tenant_id,
        name=data.name,
        campaign_type=data.campaign_type,
        status="draft",
        from_number_id=data.from_number_id,
        number_pool_ids=data.number_pool_ids or None,
        message_template=data.message_template,
        media_urls=data.media_urls or None,
        target_list_ids=data.target_list_ids or None,
        exclude_list_ids=data.exclude_list_ids or None,
        segment_filter=data.segment_filter,
        scheduled_at=data.scheduled_at,
        send_window_start=send_window_start,
        send_window_end=send_window_end,
        send_window_timezone=data.send_window_timezone,
        throttle_mps=data.throttle_mps,
        total_recipients=total_recipients,
        ab_variants=data.ab_variants,
        created_by=user_id,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

async def launch_campaign(db: AsyncSession, campaign_id: uuid.UUID, tenant_id: uuid.UUID = None) -> Campaign:
    """Transition a campaign to *sending* status and create
    ``CampaignMessage`` records for every resolved recipient.

    Returns the updated campaign.  The actual dispatch to the Celery
    send queue is handled by the caller (the router).
    """
    query = select(Campaign).where(Campaign.id == campaign_id)
    if tenant_id:
        query = query.where(Campaign.tenant_id == tenant_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found")
    if campaign.status not in ("draft", "scheduled"):
        raise ValueError(f"Cannot launch campaign in '{campaign.status}' status")

    # Resolve recipients
    recipient_ids = await _resolve_recipients(
        db,
        campaign.tenant_id,
        campaign.target_list_ids or [],
        campaign.exclude_list_ids or [],
    )

    if not recipient_ids:
        raise ValueError("No eligible recipients found")

    campaign.status = "sending"
    campaign.total_recipients = len(recipient_ids)

    # Resolve from number
    from_number_str = ""
    if campaign.from_number_id:
        pn_result = await db.execute(
            select(PhoneNumber).where(PhoneNumber.id == campaign.from_number_id)
        )
        pn = pn_result.scalar_one_or_none()
        if pn:
            from_number_str = pn.number

    # If no from number, try to pick one from the pool or tenant's first number
    if not from_number_str:
        if campaign.number_pool_ids:
            pn_result = await db.execute(
                select(PhoneNumber).where(
                    PhoneNumber.id == campaign.number_pool_ids[0]
                )
            )
            pn = pn_result.scalar_one_or_none()
            if pn:
                from_number_str = pn.number
        if not from_number_str:
            pn_result = await db.execute(
                select(PhoneNumber).where(
                    and_(
                        PhoneNumber.tenant_id == campaign.tenant_id,
                        PhoneNumber.status == "active",
                    )
                ).limit(1)
            )
            pn = pn_result.scalar_one_or_none()
            if pn:
                from_number_str = pn.number

    if not from_number_str:
        raise ValueError("No sending phone number available")

    # Load contacts for template rendering info
    contacts_result = await db.execute(
        select(Contact).where(Contact.id.in_(recipient_ids))
    )
    contacts_map = {c.id: c for c in contacts_result.scalars().all()}

    # Bulk-create CampaignMessage records
    batch_size = 500
    messages_to_insert: list[dict[str, Any]] = []
    pool_numbers: list[str] = []

    if campaign.number_pool_ids:
        pool_result = await db.execute(
            select(PhoneNumber.number).where(
                PhoneNumber.id.in_(campaign.number_pool_ids)
            )
        )
        pool_numbers = [r[0] for r in pool_result]

    for idx, contact_id in enumerate(recipient_ids):
        contact = contacts_map.get(contact_id)
        if not contact:
            continue

        # Round-robin from number when a pool is available
        sending_number = from_number_str
        if pool_numbers:
            sending_number = pool_numbers[idx % len(pool_numbers)]

        messages_to_insert.append(
            {
                "id": uuid.uuid4(),
                "campaign_id": campaign.id,
                "contact_id": contact_id,
                "tenant_id": campaign.tenant_id,
                "from_number": sending_number,
                "to_number": contact.phone_number,
                "message_body": campaign.message_template,  # rendered at send time
                "media_urls": campaign.media_urls,
                "status": "queued",
                "segments": 1,
                "cost": 0,
            }
        )

    for i in range(0, len(messages_to_insert), batch_size):
        batch = messages_to_insert[i : i + batch_size]
        await db.execute(pg_insert(CampaignMessage).values(batch))

    await db.commit()
    await db.refresh(campaign)
    return campaign


# ---------------------------------------------------------------------------
# Pause / Resume / Cancel
# ---------------------------------------------------------------------------

async def pause_campaign(db: AsyncSession, campaign_id: uuid.UUID, tenant_id: uuid.UUID = None) -> Campaign:
    query = select(Campaign).where(Campaign.id == campaign_id)
    if tenant_id:
        query = query.where(Campaign.tenant_id == tenant_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found")
    if campaign.status != "sending":
        raise ValueError(f"Cannot pause campaign in '{campaign.status}' status")
    campaign.status = "paused"
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def resume_campaign(db: AsyncSession, campaign_id: uuid.UUID, tenant_id: uuid.UUID = None) -> Campaign:
    query = select(Campaign).where(Campaign.id == campaign_id)
    if tenant_id:
        query = query.where(Campaign.tenant_id == tenant_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found")
    if campaign.status != "paused":
        raise ValueError(f"Cannot resume campaign in '{campaign.status}' status")
    campaign.status = "sending"
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def cancel_campaign(db: AsyncSession, campaign_id: uuid.UUID, tenant_id: uuid.UUID = None) -> Campaign:
    query = select(Campaign).where(Campaign.id == campaign_id)
    if tenant_id:
        query = query.where(Campaign.tenant_id == tenant_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found")
    if campaign.status not in ("sending", "paused", "scheduled", "draft"):
        raise ValueError(f"Cannot cancel campaign in '{campaign.status}' status")

    campaign.status = "canceled"

    # Mark any remaining queued messages as canceled
    await db.execute(
        update(CampaignMessage)
        .where(
            and_(
                CampaignMessage.campaign_id == campaign_id,
                CampaignMessage.status == "queued",
            )
        )
        .values(status="canceled")
    )

    await db.commit()
    await db.refresh(campaign)
    return campaign


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

async def get_campaign_stats(
    db: AsyncSession, campaign_id: uuid.UUID, tenant_id: uuid.UUID = None
) -> CampaignStats:
    """Aggregate delivery statistics from ``campaign_messages``."""
    query = select(Campaign).where(Campaign.id == campaign_id)
    if tenant_id:
        query = query.where(Campaign.tenant_id == tenant_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found")

    # Count by status -- include tenant_id filter for safety
    msg_filter = [CampaignMessage.campaign_id == campaign_id]
    if tenant_id:
        msg_filter.append(CampaignMessage.tenant_id == tenant_id)

    status_counts = await db.execute(
        select(
            CampaignMessage.status,
            func.count(CampaignMessage.id),
        )
        .where(*msg_filter)
        .group_by(CampaignMessage.status)
    )
    counts: dict[str, int] = {}
    for status_val, cnt in status_counts:
        counts[status_val] = cnt

    sent = counts.get("sent", 0) + counts.get("sending", 0)
    delivered = counts.get("delivered", 0)
    failed = counts.get("failed", 0)
    total = campaign.total_recipients or sum(counts.values())

    # Cost
    cost_result = await db.execute(
        select(func.sum(CampaignMessage.cost)).where(*msg_filter)
    )
    total_cost = float(cost_result.scalar() or 0)

    delivery_rate = (delivered / sent * 100) if sent > 0 else 0.0
    # Response rate would require counting inbound replies -- approximate with 0
    response_rate = 0.0

    return CampaignStats(
        total_recipients=total,
        sent=sent,
        delivered=delivered,
        failed=failed,
        opted_out=campaign.opted_out_count,
        delivery_rate=round(delivery_rate, 2),
        response_rate=response_rate,
        cost=round(total_cost, 4),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _count_recipients(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_list_ids: list[uuid.UUID],
    exclude_list_ids: list[uuid.UUID],
) -> int:
    """Estimate the number of unique, opted-in contacts across the target
    lists minus the exclude lists."""
    if not target_list_ids:
        return 0

    # Contacts in target lists
    target_q = (
        select(ContactListMember.contact_id)
        .join(Contact, Contact.id == ContactListMember.contact_id)
        .where(
            and_(
                ContactListMember.list_id.in_(target_list_ids),
                Contact.tenant_id == tenant_id,
                Contact.status == "active",
            )
        )
    )

    if exclude_list_ids:
        exclude_q = select(ContactListMember.contact_id).where(
            ContactListMember.list_id.in_(exclude_list_ids)
        )
        target_q = target_q.where(
            ContactListMember.contact_id.not_in(exclude_q)
        )

    count_q = select(func.count(func.distinct(target_q.c.contact_id))).select_from(
        target_q.subquery()
    )
    result = await db.execute(count_q)
    return result.scalar() or 0


async def _resolve_recipients(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_list_ids: list[uuid.UUID],
    exclude_list_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Return the list of unique, opted-in contact IDs after applying
    exclusions."""
    if not target_list_ids:
        return []

    target_q = (
        select(func.distinct(ContactListMember.contact_id))
        .join(Contact, Contact.id == ContactListMember.contact_id)
        .where(
            and_(
                ContactListMember.list_id.in_(target_list_ids),
                Contact.tenant_id == tenant_id,
                Contact.status == "active",
            )
        )
    )

    if exclude_list_ids:
        exclude_q = select(ContactListMember.contact_id).where(
            ContactListMember.list_id.in_(exclude_list_ids)
        )
        target_q = target_q.where(
            ContactListMember.contact_id.not_in(exclude_q)
        )

    result = await db.execute(target_q)
    return [row[0] for row in result]
