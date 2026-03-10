"""Celery tasks for data cleanup and maintenance."""
from app.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.cleanup.cleanup_expired_messages")
def cleanup_expired_messages():
    """Clean up message content older than retention period. Runs hourly."""
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import Session
    from app.config import get_settings
    from app.models.campaign_message import CampaignMessage
    from app.models.message import Message
    from datetime import datetime, timezone, timedelta

    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    retention_days = 90
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    with Session(engine) as db:
        # Clear message bodies older than retention (keep metadata)
        result = db.execute(
            update(CampaignMessage)
            .where(CampaignMessage.created_at < cutoff, CampaignMessage.message_body != "[redacted]")
            .values(message_body="[redacted]")
        )
        campaign_cleaned = result.rowcount

        result2 = db.execute(
            update(Message)
            .where(Message.created_at < cutoff, Message.body != "[redacted]")
            .values(body="[redacted]")
        )
        inbox_cleaned = result2.rowcount

        db.commit()
        logger.info(f"Cleaned up {campaign_cleaned} campaign messages and {inbox_cleaned} inbox messages older than {retention_days} days")


@celery_app.task(name="app.tasks.cleanup.cleanup_webhook_logs")
def cleanup_webhook_logs():
    """Clean up old webhook logs. Keep 30 days."""
    from sqlalchemy import create_engine, delete
    from sqlalchemy.orm import Session
    from app.config import get_settings
    from app.models.webhook_log import WebhookLog
    from datetime import datetime, timezone, timedelta

    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    with Session(engine) as db:
        result = db.execute(
            delete(WebhookLog).where(WebhookLog.created_at < cutoff)
        )
        db.commit()
        logger.info(f"Cleaned up {result.rowcount} webhook logs older than 30 days")
