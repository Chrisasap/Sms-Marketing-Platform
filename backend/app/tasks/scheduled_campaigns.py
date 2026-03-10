"""Celery tasks for scheduled campaign processing."""
from app.celery_app import celery_app
from datetime import datetime, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.scheduled_campaigns.check_scheduled")
def check_scheduled():
    """Check for campaigns that are due to launch. Runs every 30s via Beat."""
    from sqlalchemy import select
    from app.database import get_sync_session
    from app.models.campaign import Campaign

    with get_sync_session() as db:
        now = datetime.now(timezone.utc)
        due_campaigns = db.execute(
            select(Campaign).where(
                Campaign.status == "scheduled",
                Campaign.scheduled_at <= now,
            )
        ).scalars().all()

        for campaign in due_campaigns:
            logger.info(f"Launching scheduled campaign {campaign.id}: {campaign.name}")
            # Use the full launch_campaign flow to create CampaignMessage records
            # before dispatching to the send queue
            try:
                _launch_scheduled_campaign(campaign.id)
            except Exception as e:
                logger.error(f"Failed to launch scheduled campaign {campaign.id}: {e}")
                db.rollback()


def _launch_scheduled_campaign(campaign_id):
    """Run the async launch_campaign service in a sync context."""
    from app.services.campaign_service import launch_campaign
    from app.database import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as db:
            campaign = await launch_campaign(db, campaign_id)
            return campaign

    loop = asyncio.new_event_loop()
    try:
        campaign = loop.run_until_complete(_run())
    finally:
        loop.close()

    # Dispatch to the send queue after CampaignMessage records are created
    from app.tasks.send_messages import send_campaign_messages
    send_campaign_messages.delay(str(campaign_id))
