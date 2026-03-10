"""Celery tasks for billing synchronization."""
from app.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.billing.sync_usage_to_stripe")
def sync_usage_to_stripe():
    """Sync message usage to Stripe for metered billing. Runs every 5 min."""
    from sqlalchemy import select, func
    from app.database import get_sync_session
    from app.config import get_settings
    from app.models.tenant import Tenant
    from app.models.billing_event import BillingEvent
    from datetime import datetime, timezone, timedelta
    import stripe

    settings = get_settings()
    if not settings.stripe_secret_key:
        return

    stripe.api_key = settings.stripe_secret_key

    with get_sync_session() as db:
        # Find billing events that haven't been synced yet (synced_at IS NULL)
        events = db.execute(
            select(BillingEvent).where(
                BillingEvent.synced_at == None,
                BillingEvent.event_type.in_(["sms_sent", "mms_sent"]),
            )
        ).scalars().all()

        # Group by tenant
        tenant_usage = {}
        for event in events:
            tid = str(event.tenant_id)
            if tid not in tenant_usage:
                tenant_usage[tid] = {"sms": 0, "mms": 0, "events": []}
            if event.event_type == "sms_sent":
                tenant_usage[tid]["sms"] += event.quantity
            else:
                tenant_usage[tid]["mms"] += event.quantity
            tenant_usage[tid]["events"].append(event)

        for tid, usage in tenant_usage.items():
            tenant = db.get(Tenant, tid)
            if not tenant or not tenant.stripe_subscription_item_id:
                continue

            try:
                # Report usage to Stripe using the subscription ITEM id (not subscription id)
                if usage["sms"] > 0:
                    stripe.SubscriptionItem.create_usage_record(
                        tenant.stripe_subscription_item_id,
                        quantity=usage["sms"],
                        timestamp=int(datetime.now(timezone.utc).timestamp()),
                        action="increment",
                    )

                if usage["mms"] > 0:
                    stripe.SubscriptionItem.create_usage_record(
                        tenant.stripe_subscription_item_id,
                        quantity=usage["mms"],
                        timestamp=int(datetime.now(timezone.utc).timestamp()),
                        action="increment",
                    )

                # Mark events as synced to prevent double-reporting
                now = datetime.now(timezone.utc)
                for event in usage["events"]:
                    event.synced_at = now
                db.commit()

                logger.info(f"Synced {usage['sms']} SMS, {usage['mms']} MMS for tenant {tid}")
            except Exception as e:
                logger.error(f"Stripe sync error for tenant {tid}: {e}")
                db.rollback()
