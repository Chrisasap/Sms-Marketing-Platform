"""Analytics and reporting router.

Provides real-time dashboard stats, campaign performance, message volume
trends, per-number utilization, contact growth, and CSV export -- all
tenant-scoped.
"""

import uuid
import csv
import io
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, cast, Date

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.campaign import Campaign
from app.models.campaign_message import CampaignMessage
from app.models.message import Message
from app.models.contact import Contact
from app.models.phone_number import PhoneNumber
from app.models.billing_event import BillingEvent
from app.schemas.analytics import (
    DashboardStats,
    CampaignAnalytics,
    VolumeDataPoint,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_period(period: str) -> datetime:
    """Convert a period string like '24h', '7d', '30d', '90d' to a start datetime."""
    now = datetime.now(timezone.utc)
    mapping = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    delta = mapping.get(period, timedelta(days=7))
    return now - delta


# ---------------------------------------------------------------------------
# GET /dashboard -- Real-time dashboard stats
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Real-time dashboard metrics: messages today, delivery rate,
    active contacts, and spend.
    """
    tenant_id = user.tenant_id
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Campaign messages today
    msg_stats_q = select(
        func.count(CampaignMessage.id).label("total"),
        func.count(
            case((CampaignMessage.status == "delivered", CampaignMessage.id))
        ).label("delivered"),
        func.count(
            case((CampaignMessage.status == "failed", CampaignMessage.id))
        ).label("failed"),
    ).where(
        CampaignMessage.tenant_id == tenant_id,
        CampaignMessage.sent_at >= today_start,
    )
    msg_result = await db.execute(msg_stats_q)
    msg_row = msg_result.one()
    sent_today = msg_row.total or 0
    delivered_today = msg_row.delivered or 0
    failed_today = msg_row.failed or 0

    # Inbox messages (responses) today
    inbox_today_q = select(func.count(Message.id)).where(
        Message.tenant_id == tenant_id,
        Message.direction == "inbound",
        Message.created_at >= today_start,
    )
    inbox_result = await db.execute(inbox_today_q)
    responses_today = inbox_result.scalar() or 0

    # Active contacts
    active_contacts_q = select(func.count(Contact.id)).where(
        Contact.tenant_id == tenant_id,
        Contact.status == "active",
    )
    active_result = await db.execute(active_contacts_q)
    active_contacts = active_result.scalar() or 0

    # Active phone numbers
    active_numbers_q = select(func.count(PhoneNumber.id)).where(
        PhoneNumber.tenant_id == tenant_id,
        PhoneNumber.status == "active",
    )
    numbers_result = await db.execute(active_numbers_q)
    active_numbers = numbers_result.scalar() or 0

    # Spend today
    spend_q = select(func.coalesce(func.sum(BillingEvent.total_cost), 0)).where(
        BillingEvent.tenant_id == tenant_id,
        BillingEvent.created_at >= today_start,
    )
    spend_result = await db.execute(spend_q)
    spend_today = float(spend_result.scalar() or 0)

    delivery_rate = (
        round(delivered_today / sent_today * 100, 2) if sent_today > 0 else 0.0
    )

    return {
        "messages_sent_today": sent_today,
        "messages_delivered_today": delivered_today,
        "messages_failed_today": failed_today,
        "responses_today": responses_today,
        "delivery_rate": delivery_rate,
        "active_contacts": active_contacts,
        "active_numbers": active_numbers,
        "spend_today": spend_today,
    }


# ---------------------------------------------------------------------------
# GET /campaigns -- Campaign performance list
# ---------------------------------------------------------------------------

@router.get("/campaigns")
async def list_campaign_analytics(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Campaign performance overview with delivery and response rates."""
    tenant_id = user.tenant_id

    # Count total campaigns
    count_q = select(func.count(Campaign.id)).where(
        Campaign.tenant_id == tenant_id,
        Campaign.status.in_(["completed", "sending", "paused"]),
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Fetch campaigns
    data_q = (
        select(Campaign)
        .where(
            Campaign.tenant_id == tenant_id,
            Campaign.status.in_(["completed", "sending", "paused"]),
        )
        .order_by(Campaign.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    campaigns = result.scalars().all()

    # Batch-fetch costs per campaign to avoid N+1 queries
    campaign_ids = [c.id for c in campaigns]
    cost_map: dict = {}
    if campaign_ids:
        cost_q = (
            select(
                CampaignMessage.campaign_id,
                func.coalesce(func.sum(CampaignMessage.cost), 0).label("total_cost"),
            )
            .where(CampaignMessage.campaign_id.in_(campaign_ids))
            .group_by(CampaignMessage.campaign_id)
        )
        cost_result = await db.execute(cost_q)
        cost_map = {row[0]: float(row[1]) for row in cost_result.all()}

    items = []
    for c in campaigns:
        sent = c.sent_count or 0
        delivered = c.delivered_count or 0
        failed = c.failed_count or 0
        opted_out = c.opted_out_count or 0

        delivery_rate = round(delivered / sent * 100, 2) if sent > 0 else 0.0
        cost = cost_map.get(c.id, 0.0)

        items.append({
            "campaign_id": str(c.id),
            "name": c.name,
            "status": c.status,
            "sent": sent,
            "delivered": delivered,
            "failed": failed,
            "opted_out": opted_out,
            "total_recipients": c.total_recipients or 0,
            "delivery_rate": delivery_rate,
            "response_rate": 0.0,  # Requires deeper join; placeholder
            "cost": cost,
            "created_at": c.created_at.isoformat(),
        })

    return {
        "campaigns": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# GET /campaigns/{id} -- Detailed campaign analytics
# ---------------------------------------------------------------------------

@router.get("/campaigns/{campaign_id}")
async def get_campaign_analytics(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Detailed analytics for a specific campaign, including per-day
    delivery timeline.
    """
    tenant_id = user.tenant_id

    campaign_result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    sent = campaign.sent_count or 0
    delivered = campaign.delivered_count or 0
    failed = campaign.failed_count or 0
    opted_out = campaign.opted_out_count or 0

    delivery_rate = round(delivered / sent * 100, 2) if sent > 0 else 0.0
    opt_out_rate = round(opted_out / sent * 100, 2) if sent > 0 else 0.0

    # Cost breakdown
    cost_q = select(
        func.coalesce(func.sum(CampaignMessage.cost), 0),
        func.coalesce(func.sum(CampaignMessage.segments), 0),
    ).where(CampaignMessage.campaign_id == campaign_id)
    cost_result = await db.execute(cost_q)
    cost_row = cost_result.one()
    total_cost = float(cost_row[0] or 0)
    total_segments = int(cost_row[1] or 0)

    # Per-day delivery timeline
    timeline_q = (
        select(
            cast(CampaignMessage.sent_at, Date).label("send_date"),
            func.count(CampaignMessage.id).label("sent"),
            func.count(
                case((CampaignMessage.status == "delivered", CampaignMessage.id))
            ).label("delivered"),
            func.count(
                case((CampaignMessage.status == "failed", CampaignMessage.id))
            ).label("failed"),
        )
        .where(
            CampaignMessage.campaign_id == campaign_id,
            CampaignMessage.sent_at.isnot(None),
        )
        .group_by(cast(CampaignMessage.sent_at, Date))
        .order_by(cast(CampaignMessage.sent_at, Date))
    )
    timeline_result = await db.execute(timeline_q)
    timeline = [
        {
            "date": row.send_date.isoformat() if row.send_date else None,
            "sent": row.sent,
            "delivered": row.delivered,
            "failed": row.failed,
        }
        for row in timeline_result.all()
    ]

    # Status breakdown
    status_q = (
        select(
            CampaignMessage.status,
            func.count(CampaignMessage.id),
        )
        .where(CampaignMessage.campaign_id == campaign_id)
        .group_by(CampaignMessage.status)
    )
    status_result = await db.execute(status_q)
    status_breakdown = {row[0]: row[1] for row in status_result.all()}

    return {
        "campaign_id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status,
        "total_recipients": campaign.total_recipients or 0,
        "sent": sent,
        "delivered": delivered,
        "failed": failed,
        "opted_out": opted_out,
        "delivery_rate": delivery_rate,
        "opt_out_rate": opt_out_rate,
        "total_segments": total_segments,
        "total_cost": total_cost,
        "status_breakdown": status_breakdown,
        "timeline": timeline,
        "created_at": campaign.created_at.isoformat(),
        "scheduled_at": (
            campaign.scheduled_at.isoformat() if campaign.scheduled_at else None
        ),
    }


# ---------------------------------------------------------------------------
# GET /volume -- Message volume over time
# ---------------------------------------------------------------------------

@router.get("/volume")
async def get_message_volume(
    start_date: date | None = None,
    end_date: date | None = None,
    period: str = Query("7d", pattern="^(24h|7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Message volume grouped by day over a date range.

    Uses ``start_date`` / ``end_date`` if provided, otherwise falls back
    to the ``period`` shortcut (7d, 30d, etc.).
    """
    tenant_id = user.tenant_id

    if start_date and end_date:
        range_start = datetime.combine(start_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        range_end = datetime.combine(end_date, datetime.max.time()).replace(
            tzinfo=timezone.utc
        )
    else:
        range_start = _parse_period(period)
        range_end = datetime.now(timezone.utc)

    # Campaign messages by day
    volume_q = (
        select(
            cast(CampaignMessage.sent_at, Date).label("send_date"),
            func.count(CampaignMessage.id).label("sent"),
            func.count(
                case((CampaignMessage.status == "delivered", CampaignMessage.id))
            ).label("delivered"),
            func.count(
                case((CampaignMessage.status == "failed", CampaignMessage.id))
            ).label("failed"),
        )
        .where(
            CampaignMessage.tenant_id == tenant_id,
            CampaignMessage.sent_at >= range_start,
            CampaignMessage.sent_at <= range_end,
        )
        .group_by(cast(CampaignMessage.sent_at, Date))
        .order_by(cast(CampaignMessage.sent_at, Date))
    )
    result = await db.execute(volume_q)
    rows = result.all()

    data_points = [
        {
            "date": row.send_date.isoformat() if row.send_date else None,
            "sent": row.sent,
            "delivered": row.delivered,
            "failed": row.failed,
        }
        for row in rows
    ]

    return {
        "volume": data_points,
        "start_date": range_start.date().isoformat(),
        "end_date": range_end.date().isoformat(),
        "total_sent": sum(d["sent"] for d in data_points),
        "total_delivered": sum(d["delivered"] for d in data_points),
        "total_failed": sum(d["failed"] for d in data_points),
    }


# ---------------------------------------------------------------------------
# GET /numbers -- Per-number utilization stats
# ---------------------------------------------------------------------------

@router.get("/numbers")
async def get_number_analytics(
    period: str = Query("7d", pattern="^(24h|7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Per-phone-number messaging utilization stats."""
    tenant_id = user.tenant_id
    range_start = _parse_period(period)

    # Get all active numbers for tenant
    numbers_q = select(PhoneNumber).where(
        PhoneNumber.tenant_id == tenant_id,
        PhoneNumber.status == "active",
    )
    numbers_result = await db.execute(numbers_q)
    numbers = numbers_result.scalars().all()

    # Batch aggregation queries to avoid N+1

    # Outbound counts grouped by from_number
    number_strings = [pn.number for pn in numbers]
    outbound_counts: dict[str, int] = {}
    delivered_counts: dict[str, int] = {}
    if number_strings:
        outbound_q = (
            select(
                CampaignMessage.from_number,
                func.count(CampaignMessage.id).label("total"),
                func.count(
                    case((CampaignMessage.status == "delivered", CampaignMessage.id))
                ).label("delivered"),
            )
            .where(
                CampaignMessage.tenant_id == tenant_id,
                CampaignMessage.from_number.in_(number_strings),
                CampaignMessage.sent_at >= range_start,
            )
            .group_by(CampaignMessage.from_number)
        )
        outbound_result = await db.execute(outbound_q)
        for row in outbound_result.all():
            outbound_counts[row[0]] = row.total
            delivered_counts[row[0]] = row.delivered

    # Inbound counts grouped by phone_number_id
    from app.models.conversation import Conversation
    number_ids = [pn.id for pn in numbers]
    inbound_counts: dict[uuid.UUID, int] = {}
    if number_ids:
        inbound_q = (
            select(
                Conversation.phone_number_id,
                func.count(Message.id).label("inbound"),
            )
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.tenant_id == tenant_id,
                Message.direction == "inbound",
                Conversation.phone_number_id.in_(number_ids),
                Message.created_at >= range_start,
            )
            .group_by(Conversation.phone_number_id)
        )
        inbound_result = await db.execute(inbound_q)
        for row in inbound_result.all():
            inbound_counts[row[0]] = row.inbound

    items = []
    for pn in numbers:
        outbound_count = outbound_counts.get(pn.number, 0)
        delivered_count = delivered_counts.get(pn.number, 0)
        inbound_count = inbound_counts.get(pn.id, 0)

        delivery_rate = (
            round(delivered_count / outbound_count * 100, 2)
            if outbound_count > 0 else 0.0
        )

        items.append({
            "phone_number_id": str(pn.id),
            "number": pn.number,
            "number_type": pn.number_type,
            "outbound_count": outbound_count,
            "inbound_count": inbound_count,
            "delivered_count": delivered_count,
            "delivery_rate": delivery_rate,
            "monthly_cost": float(pn.monthly_cost),
        })

    return {"numbers": items, "period": period}


# ---------------------------------------------------------------------------
# GET /contacts -- Contact growth over time
# ---------------------------------------------------------------------------

@router.get("/contacts")
async def get_contact_growth(
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Contact growth (new contacts per day) over time."""
    tenant_id = user.tenant_id
    range_start = _parse_period(period)

    growth_q = (
        select(
            cast(Contact.created_at, Date).label("created_date"),
            func.count(Contact.id).label("new_contacts"),
        )
        .where(
            Contact.tenant_id == tenant_id,
            Contact.created_at >= range_start,
        )
        .group_by(cast(Contact.created_at, Date))
        .order_by(cast(Contact.created_at, Date))
    )
    result = await db.execute(growth_q)
    rows = result.all()

    # Total contact counts
    total_q = select(func.count(Contact.id)).where(
        Contact.tenant_id == tenant_id
    )
    total_result = await db.execute(total_q)
    total_contacts = total_result.scalar() or 0

    active_q = select(func.count(Contact.id)).where(
        Contact.tenant_id == tenant_id,
        Contact.status == "active",
    )
    active_result = await db.execute(active_q)
    active_contacts = active_result.scalar() or 0

    opted_out_q = select(func.count(Contact.id)).where(
        Contact.tenant_id == tenant_id,
        Contact.status == "unsubscribed",
    )
    opted_out_result = await db.execute(opted_out_q)
    opted_out_contacts = opted_out_result.scalar() or 0

    return {
        "growth": [
            {
                "date": row.created_date.isoformat(),
                "new_contacts": row.new_contacts,
            }
            for row in rows
        ],
        "total_contacts": total_contacts,
        "active_contacts": active_contacts,
        "opted_out_contacts": opted_out_contacts,
        "period": period,
    }


# ---------------------------------------------------------------------------
# GET /export -- Export report as CSV
# ---------------------------------------------------------------------------

@router.get("/export")
async def export_report(
    report_type: str = Query(..., pattern="^(messages|campaigns|contacts)$"),
    period: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Export analytics data as a CSV file.

    Supported report types: ``messages``, ``campaigns``, ``contacts``.
    """
    tenant_id = user.tenant_id
    range_start = (
        _parse_period(period) if period != "all"
        else datetime(2000, 1, 1, tzinfo=timezone.utc)
    )

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "messages":
        writer.writerow([
            "message_id", "campaign_id", "from_number", "to_number",
            "status", "segments", "cost", "sent_at", "delivered_at",
        ])
        query = (
            select(CampaignMessage)
            .where(
                CampaignMessage.tenant_id == tenant_id,
                CampaignMessage.sent_at >= range_start,
            )
            .order_by(CampaignMessage.sent_at.desc())
            .limit(50000)
        )
        result = await db.execute(query)
        for m in result.scalars().all():
            writer.writerow([
                str(m.id),
                str(m.campaign_id),
                m.from_number,
                m.to_number,
                m.status,
                m.segments,
                float(m.cost),
                m.sent_at.isoformat() if m.sent_at else "",
                m.delivered_at.isoformat() if m.delivered_at else "",
            ])

    elif report_type == "campaigns":
        writer.writerow([
            "campaign_id", "name", "status", "total_recipients",
            "sent", "delivered", "failed", "opted_out",
            "delivery_rate", "created_at",
        ])
        query = (
            select(Campaign)
            .where(
                Campaign.tenant_id == tenant_id,
                Campaign.created_at >= range_start,
            )
            .order_by(Campaign.created_at.desc())
        )
        result = await db.execute(query)
        for c in result.scalars().all():
            sent = c.sent_count or 0
            delivered = c.delivered_count or 0
            dr = round(delivered / sent * 100, 2) if sent > 0 else 0.0
            writer.writerow([
                str(c.id),
                c.name,
                c.status,
                c.total_recipients,
                sent,
                delivered,
                c.failed_count or 0,
                c.opted_out_count or 0,
                dr,
                c.created_at.isoformat(),
            ])

    elif report_type == "contacts":
        writer.writerow([
            "contact_id", "phone_number", "first_name", "last_name",
            "email", "status", "message_count", "created_at",
        ])
        query = (
            select(Contact)
            .where(
                Contact.tenant_id == tenant_id,
                Contact.created_at >= range_start,
            )
            .order_by(Contact.created_at.desc())
            .limit(100000)
        )
        result = await db.execute(query)
        for c in result.scalars().all():
            writer.writerow([
                str(c.id),
                c.phone_number,
                c.first_name or "",
                c.last_name or "",
                c.email or "",
                c.status,
                c.message_count,
                c.created_at.isoformat(),
            ])

    output.seek(0)
    filename = f"blastwave_{report_type}_{date.today().isoformat()}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
