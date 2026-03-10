"""Webhook receivers for Bandwidth messaging callbacks and Stripe billing events."""

import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Bandwidth messaging callbacks
# ---------------------------------------------------------------------------

@router.post("/bandwidth")
async def bandwidth_webhook(
    request: Request,
):
    """Receive Bandwidth messaging webhooks (delivery receipts + inbound).

    Bandwidth posts a JSON array of callback objects.  We enqueue each event
    for async processing via Celery -- no direct processing in the router to
    avoid duplicate processing paths.
    """
    try:
        body = await request.json()
        # Bandwidth sends callbacks as a JSON array, but some edge-cases
        # (e.g. manual testing) may send a single object.
        events = body if isinstance(body, list) else [body]

        from app.tasks.process_webhooks import process_bandwidth_callback
        for event in events:
            process_bandwidth_callback.delay(event)

        return {"status": "ok"}
    except Exception as e:
        logger.error("Webhook processing error: %s", e, exc_info=True)
        # Return 200 to prevent Bandwidth from endlessly retrying.
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Stripe billing webhooks
# ---------------------------------------------------------------------------

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive Stripe webhooks for subscription lifecycle events.

    Verifies the webhook signature using the configured endpoint secret,
    then dispatches to the appropriate handler.
    """
    import stripe
    from app.config import get_settings
    from sqlalchemy import select, update
    from app.models.tenant import Tenant

    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data_object = event["data"]["object"]
    logger.info("Stripe webhook received: %s", event_type)

    # Complete Stripe subscription status mapping
    status_map = {
        "active": "active",
        "trialing": "active",
        "past_due": "past_due",
        "unpaid": "suspended",
        "canceled": "canceled",
        "incomplete": "incomplete",
        "incomplete_expired": "canceled",
        "paused": "suspended",
    }

    if event_type == "customer.subscription.updated":
        stripe_customer_id = data_object.get("customer")
        new_status = data_object.get("status")
        # Map Stripe plan to internal tier
        items = data_object.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        plan_tier = _stripe_price_to_tier(price_id, settings)
        mapped_status = status_map.get(new_status, "past_due")
        if stripe_customer_id:
            await db.execute(
                update(Tenant)
                .where(Tenant.stripe_customer_id == stripe_customer_id)
                .values(
                    plan_tier=plan_tier or Tenant.plan_tier,
                    stripe_subscription_id=data_object.get("id"),
                    status=mapped_status,
                )
            )
            await db.commit()

    elif event_type == "customer.subscription.deleted":
        stripe_customer_id = data_object.get("customer")
        if stripe_customer_id:
            await db.execute(
                update(Tenant)
                .where(Tenant.stripe_customer_id == stripe_customer_id)
                .values(
                    plan_tier="free_trial",
                    stripe_subscription_id=None,
                    status="canceled",
                )
            )
            await db.commit()

    elif event_type == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("metadata", {}).get("type") == "credit_purchase":
            tenant_id = session["metadata"]["tenant_id"]
            credit_amount = int(session["metadata"]["amount"])
            await db.execute(
                update(Tenant)
                .where(Tenant.id == tenant_id)
                .values(credit_balance=Tenant.credit_balance + credit_amount)
            )
            await db.commit()
            logger.info(
                "Added %d credits to tenant %s via checkout.session.completed",
                credit_amount,
                tenant_id,
            )

    elif event_type == "invoice.payment_failed":
        stripe_customer_id = data_object.get("customer")
        if stripe_customer_id:
            await db.execute(
                update(Tenant)
                .where(Tenant.stripe_customer_id == stripe_customer_id)
                .values(status="past_due")
            )
            await db.commit()

    elif event_type == "invoice.paid":
        stripe_customer_id = data_object.get("customer")
        if stripe_customer_id:
            await db.execute(
                update(Tenant)
                .where(Tenant.stripe_customer_id == stripe_customer_id)
                .values(status="active")
            )
            await db.commit()

    return {"status": "ok"}


def _stripe_price_to_tier(price_id: str | None, settings) -> str | None:
    """Map a Stripe price ID to the internal plan tier name."""
    if not price_id:
        return None
    mapping = {
        settings.stripe_price_starter: "starter",
        settings.stripe_price_growth: "growth",
        settings.stripe_price_enterprise: "enterprise",
    }
    return mapping.get(price_id)
