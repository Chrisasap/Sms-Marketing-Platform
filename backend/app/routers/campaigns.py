"""Campaign management routes -- CRUD, launch, pause, resume, cancel, stats."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.campaign import Campaign
from app.models.campaign_message import CampaignMessage
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
)
from app.services.campaign_service import (
    cancel_campaign as svc_cancel,
    create_campaign as svc_create,
    get_campaign_stats as svc_stats,
    launch_campaign as svc_launch,
    pause_campaign as svc_pause,
    resume_campaign as svc_resume,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_campaign_or_404(
    db: AsyncSession, campaign_id: uuid.UUID, tenant_id: uuid.UUID
) -> Campaign:
    result = await db.execute(
        select(Campaign).where(
            and_(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
            )
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    return campaign


# ---------------------------------------------------------------------------
# GET / -- list campaigns
# ---------------------------------------------------------------------------

@router.get("/")
async def list_campaigns(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all campaigns with optional status filtering and pagination."""
    base = select(Campaign).where(Campaign.tenant_id == user.tenant_id)
    count_q = select(func.count(Campaign.id)).where(
        Campaign.tenant_id == user.tenant_id
    )

    if status_filter:
        base = base.where(Campaign.status == status_filter)
        count_q = count_q.where(Campaign.status == status_filter)

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    campaigns_result = await db.execute(
        base.order_by(Campaign.created_at.desc()).offset(offset).limit(per_page)
    )
    campaigns = campaigns_result.scalars().all()

    return {
        "campaigns": [CampaignResponse.model_validate(c) for c in campaigns],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST / -- create campaign
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new campaign in draft status (does not send)."""
    try:
        campaign = await svc_create(db, user.tenant_id, user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    return {"campaign": CampaignResponse.model_validate(campaign)}


# ---------------------------------------------------------------------------
# GET /{id} -- campaign detail with stats
# ---------------------------------------------------------------------------

@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get campaign details including delivery statistics."""
    campaign = await _get_campaign_or_404(db, campaign_id, user.tenant_id)
    try:
        stats = await svc_stats(db, campaign_id, tenant_id=user.tenant_id)
    except ValueError:
        stats = None
    return {
        "campaign": CampaignResponse.model_validate(campaign),
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# PUT /{id} -- update draft campaign
# ---------------------------------------------------------------------------

@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a campaign that is still in draft status."""
    campaign = await _get_campaign_or_404(db, campaign_id, user.tenant_id)

    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit campaign in '{campaign.status}' status",
        )

    if data.name is not None:
        campaign.name = data.name
    if data.message_template is not None:
        campaign.message_template = data.message_template
    if data.media_urls is not None:
        campaign.media_urls = data.media_urls
    if data.scheduled_at is not None:
        campaign.scheduled_at = data.scheduled_at
    if data.status is not None:
        # Only allow transitioning to scheduled from draft
        if data.status == "scheduled" and campaign.status == "draft":
            campaign.status = "scheduled"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot set status to '{data.status}' from '{campaign.status}'",
            )

    await db.commit()
    await db.refresh(campaign)
    return {"campaign": CampaignResponse.model_validate(campaign)}


# ---------------------------------------------------------------------------
# POST /{id}/launch -- start sending
# ---------------------------------------------------------------------------

@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Launch a campaign -- resolve recipients and start sending."""
    # Verify tenant ownership
    await _get_campaign_or_404(db, campaign_id, user.tenant_id)

    try:
        campaign = await svc_launch(db, campaign_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Dispatch to Celery for actual sending
    from app.tasks.send_messages import send_campaign_messages

    send_campaign_messages.delay(str(campaign_id))

    return {
        "message": "Campaign launched",
        "campaign": CampaignResponse.model_validate(campaign),
    }


# ---------------------------------------------------------------------------
# POST /{id}/pause
# ---------------------------------------------------------------------------

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pause a running campaign."""
    await _get_campaign_or_404(db, campaign_id, user.tenant_id)
    try:
        campaign = await svc_pause(db, campaign_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return {
        "message": "Campaign paused",
        "campaign": CampaignResponse.model_validate(campaign),
    }


# ---------------------------------------------------------------------------
# POST /{id}/resume
# ---------------------------------------------------------------------------

@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resume a paused campaign."""
    await _get_campaign_or_404(db, campaign_id, user.tenant_id)
    try:
        campaign = await svc_resume(db, campaign_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Re-dispatch to Celery to continue sending remaining queued messages
    from app.tasks.send_messages import send_campaign_messages

    send_campaign_messages.delay(str(campaign_id))

    return {
        "message": "Campaign resumed",
        "campaign": CampaignResponse.model_validate(campaign),
    }


# ---------------------------------------------------------------------------
# POST /{id}/cancel
# ---------------------------------------------------------------------------

@router.post("/{campaign_id}/cancel")
async def cancel_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cancel a campaign (stops sending, marks queued messages as canceled)."""
    await _get_campaign_or_404(db, campaign_id, user.tenant_id)
    try:
        campaign = await svc_cancel(db, campaign_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return {
        "message": "Campaign canceled",
        "campaign": CampaignResponse.model_validate(campaign),
    }


# ---------------------------------------------------------------------------
# GET /{id}/messages -- paginated campaign messages
# ---------------------------------------------------------------------------

@router.get("/{campaign_id}/messages")
async def list_campaign_messages(
    campaign_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    msg_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Paginated list of individual campaign messages with delivery status."""
    await _get_campaign_or_404(db, campaign_id, user.tenant_id)

    base = select(CampaignMessage).where(
        CampaignMessage.campaign_id == campaign_id
    )
    count_q = select(func.count(CampaignMessage.id)).where(
        CampaignMessage.campaign_id == campaign_id
    )

    if msg_status:
        base = base.where(CampaignMessage.status == msg_status)
        count_q = count_q.where(CampaignMessage.status == msg_status)

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    msgs_result = await db.execute(
        base.order_by(CampaignMessage.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    messages = msgs_result.scalars().all()

    return {
        "messages": [
            {
                "id": str(m.id),
                "contact_id": str(m.contact_id),
                "from_number": m.from_number,
                "to_number": m.to_number,
                "message_body": m.message_body,
                "status": m.status,
                "error_code": m.error_code,
                "error_description": m.error_description,
                "segments": m.segments,
                "cost": float(m.cost),
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "delivered_at": m.delivered_at.isoformat() if m.delivered_at else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# GET /{id}/stats -- delivery statistics
# ---------------------------------------------------------------------------

@router.get("/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed delivery statistics for a campaign."""
    await _get_campaign_or_404(db, campaign_id, user.tenant_id)
    try:
        stats = await svc_stats(db, campaign_id, tenant_id=user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    return stats
