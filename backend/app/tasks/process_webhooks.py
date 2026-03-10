"""Celery tasks for async webhook processing."""
from app.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.process_webhooks.process_bandwidth_callback", bind=True, max_retries=3)
def process_bandwidth_callback(self, event_data: dict):
    """Process a single Bandwidth callback event asynchronously."""
    from app.database import get_sync_session

    event_type = event_data.get("type", "unknown")
    message_id = event_data.get("message", {}).get("id", "unknown")

    try:
        with get_sync_session() as db:
            from app.models.webhook_log import WebhookLog
            from app.models.campaign_message import CampaignMessage
            from app.models.campaign import Campaign
            from app.models.message import Message
            from sqlalchemy import select, update
            from datetime import datetime, timezone

            bw_msg_id = event_data.get("message", {}).get("id", "")

            if event_type == "message-delivered":
                # Update campaign message
                msg = db.execute(
                    select(CampaignMessage).where(CampaignMessage.bandwidth_message_id == bw_msg_id)
                ).scalar_one_or_none()
                if msg:
                    msg.status = "delivered"
                    msg.delivered_at = datetime.now(timezone.utc)
                    db.execute(
                        update(Campaign).where(Campaign.id == msg.campaign_id)
                        .values(delivered_count=Campaign.delivered_count + 1)
                    )

                # Update conversation message
                conv_msg = db.execute(
                    select(Message).where(Message.bandwidth_message_id == bw_msg_id)
                ).scalar_one_or_none()
                if conv_msg:
                    conv_msg.status = "delivered"

                db.commit()

            elif event_type == "message-failed":
                error_code = str(event_data.get("errorCode", ""))
                msg = db.execute(
                    select(CampaignMessage).where(CampaignMessage.bandwidth_message_id == bw_msg_id)
                ).scalar_one_or_none()
                if msg:
                    msg.status = "failed"
                    msg.error_code = error_code
                    msg.failed_at = datetime.now(timezone.utc)
                    db.execute(
                        update(Campaign).where(Campaign.id == msg.campaign_id)
                        .values(failed_count=Campaign.failed_count + 1)
                    )
                db.commit()

            logger.info(f"Processed webhook: {event_type} for message {bw_msg_id}")

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        self.retry(countdown=30)
