from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "blastwave",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.send_messages",
        "app.tasks.process_webhooks",
        "app.tasks.import_contacts",
        "app.tasks.ai_agent",
        "app.tasks.drip_sequences",
        "app.tasks.scheduled_campaigns",
        "app.tasks.billing",
        "app.tasks.cleanup",
        "app.tasks.ai_dlc_review",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "process-drip-steps": {
            "task": "app.tasks.drip_sequences.process_due_steps",
            "schedule": 60.0,  # every minute
        },
        "process-scheduled-campaigns": {
            "task": "app.tasks.scheduled_campaigns.check_scheduled",
            "schedule": 30.0,  # every 30 seconds
        },
        "cleanup-old-messages": {
            "task": "app.tasks.cleanup.cleanup_expired_messages",
            "schedule": 3600.0,  # every hour
        },
        "sync-billing-usage": {
            "task": "app.tasks.billing.sync_usage_to_stripe",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)
