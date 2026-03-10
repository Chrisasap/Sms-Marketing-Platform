"""Stripe billing router.

Provides billing overview, Stripe Checkout/Portal session creation,
prepaid credit purchases, invoice history, billing events, and plan
details -- all tenant-scoped.
"""

import uuid
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.config import get_settings
from app.models.user import User
from app.models.tenant import Tenant
from app.models.billing_event import BillingEvent
from app.models.campaign_message import CampaignMessage
from app.models.phone_number import PhoneNumber
from app.schemas.billing import (
    PlanInfo,
    CreditPurchaseRequest,
    BillingOverview,
    BillingEventResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------

PLANS: dict[str, dict] = {
    "free_trial": {
        "tier": "free_trial",
        "name": "Free Trial",
        "price": Decimal("0"),
        "included_sms": 100,
        "included_mms": 10,
        "max_numbers": 1,
        "max_users": 1,
        "max_contacts": 500,
        "max_ai_agents": 0,
        "stripe_price_id": None,
    },
    "starter": {
        "tier": "starter",
        "name": "Starter",
        "price": Decimal("49"),
        "included_sms": 1000,
        "included_mms": 100,
        "max_numbers": 3,
        "max_users": 3,
        "max_contacts": 5000,
        "max_ai_agents": 1,
        "stripe_price_id": settings.stripe_price_starter,
    },
    "growth": {
        "tier": "growth",
        "name": "Growth",
        "price": Decimal("149"),
        "included_sms": 5000,
        "included_mms": 500,
        "max_numbers": 10,
        "max_users": 10,
        "max_contacts": 25000,
        "max_ai_agents": 3,
        "stripe_price_id": settings.stripe_price_growth,
    },
    "enterprise": {
        "tier": "enterprise",
        "name": "Enterprise",
        "price": Decimal("499"),
        "included_sms": 25000,
        "included_mms": 2500,
        "max_numbers": 50,
        "max_users": 50,
        "max_contacts": 100000,
        "max_ai_agents": 10,
        "stripe_price_id": settings.stripe_price_enterprise,
    },
}


def _get_stripe():
    """Lazily import and configure stripe."""
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


# ---------------------------------------------------------------------------
# GET / -- Billing overview
# ---------------------------------------------------------------------------

@router.get("/")
async def billing_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Billing overview: plan info, credit balance, current period usage,
    and next invoice date.
    """
    tenant_id = user.tenant_id

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan = PLANS.get(tenant.plan_tier, PLANS["free_trial"])

    # Current period SMS/MMS usage from billing events
    # Approximate current period as last 30 days
    from datetime import datetime, timezone, timedelta

    period_start = datetime.now(timezone.utc) - timedelta(days=30)

    sms_q = select(func.coalesce(func.sum(BillingEvent.quantity), 0)).where(
        BillingEvent.tenant_id == tenant_id,
        BillingEvent.event_type == "sms_sent",
        BillingEvent.created_at >= period_start,
    )
    sms_result = await db.execute(sms_q)
    current_sms = int(sms_result.scalar() or 0)

    mms_q = select(func.coalesce(func.sum(BillingEvent.quantity), 0)).where(
        BillingEvent.tenant_id == tenant_id,
        BillingEvent.event_type == "mms_sent",
        BillingEvent.created_at >= period_start,
    )
    mms_result = await db.execute(mms_q)
    current_mms = int(mms_result.scalar() or 0)

    # Overage cost
    overage_q = select(
        func.coalesce(func.sum(BillingEvent.total_cost), 0)
    ).where(
        BillingEvent.tenant_id == tenant_id,
        BillingEvent.created_at >= period_start,
    )
    overage_result = await db.execute(overage_q)
    overage_cost = float(overage_result.scalar() or 0)

    # Next invoice date from Stripe if subscription exists
    next_invoice_date = None
    if tenant.stripe_subscription_id:
        try:
            stripe = _get_stripe()
            sub = stripe.Subscription.retrieve(tenant.stripe_subscription_id)
            if sub.current_period_end:
                next_invoice_date = datetime.fromtimestamp(
                    sub.current_period_end, tz=timezone.utc
                ).isoformat()
        except Exception as e:
            logger.warning("Failed to fetch Stripe subscription: %s", e)

    return {
        "plan_tier": tenant.plan_tier,
        "plan_name": plan["name"],
        "plan_price": float(plan["price"]),
        "credit_balance": float(tenant.credit_balance),
        "current_period_sms": current_sms,
        "current_period_mms": current_mms,
        "included_sms": plan["included_sms"],
        "included_mms": plan["included_mms"],
        "overage_cost": overage_cost,
        "next_invoice_date": next_invoice_date,
        "stripe_customer_id": tenant.stripe_customer_id,
        "stripe_subscription_id": tenant.stripe_subscription_id,
    }


# ---------------------------------------------------------------------------
# POST /checkout -- Create Stripe Checkout session
# ---------------------------------------------------------------------------

@router.post("/checkout")
async def create_checkout_session(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Create a Stripe Checkout session for subscribing to a plan.

    Body: ``{"plan": "starter" | "growth" | "enterprise"}``
    Returns the Checkout session URL for redirect.
    """
    plan_tier = body.get("plan")
    if plan_tier not in PLANS or plan_tier == "free_trial":
        raise HTTPException(
            status_code=400,
            detail="Invalid plan. Choose: starter, growth, or enterprise",
        )

    plan = PLANS[plan_tier]
    if not plan["stripe_price_id"]:
        raise HTTPException(
            status_code=400,
            detail="Stripe price not configured for this plan",
        )

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    stripe = _get_stripe()

    # Ensure Stripe customer exists
    if not tenant.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=tenant.name,
            metadata={
                "tenant_id": str(tenant.id),
                "tenant_slug": tenant.slug,
            },
        )
        tenant.stripe_customer_id = customer.id
        await db.commit()

    # Create Checkout session
    try:
        session = stripe.checkout.Session.create(
            customer=tenant.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
            success_url=f"{settings.app_url}/billing?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app_url}/billing?canceled=true",
            metadata={
                "tenant_id": str(tenant.id),
                "plan_tier": plan_tier,
            },
        )
    except Exception as e:
        logger.exception("Stripe Checkout session creation failed")
        raise HTTPException(
            status_code=502, detail=f"Stripe error: {str(e)}"
        )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }


# ---------------------------------------------------------------------------
# POST /portal -- Create Stripe Billing Portal session
# ---------------------------------------------------------------------------

@router.post("/portal")
async def create_portal_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Create a Stripe Billing Portal session for self-service management
    (update payment, cancel, switch plans).

    Returns the Portal session URL for redirect.
    """
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No billing account found. Subscribe to a plan first.",
        )

    stripe = _get_stripe()

    try:
        session = stripe.billing_portal.Session.create(
            customer=tenant.stripe_customer_id,
            return_url=f"{settings.app_url}/billing",
        )
    except Exception as e:
        logger.exception("Stripe Portal session creation failed")
        raise HTTPException(
            status_code=502, detail=f"Stripe error: {str(e)}"
        )

    return {"portal_url": session.url}


# ---------------------------------------------------------------------------
# POST /credits/purchase -- Purchase prepaid credits
# ---------------------------------------------------------------------------

@router.post("/credits/purchase")
async def purchase_credits(
    body: CreditPurchaseRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Purchase prepaid messaging credits.

    Creates a one-time Stripe Payment Intent for the given dollar amount
    and adds credits to the tenant balance upon success.
    """
    if body.amount < Decimal("5"):
        raise HTTPException(
            status_code=400, detail="Minimum credit purchase is $5.00"
        )
    if body.amount > Decimal("10000"):
        raise HTTPException(
            status_code=400, detail="Maximum single purchase is $10,000.00"
        )

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    stripe = _get_stripe()

    # Ensure Stripe customer
    if not tenant.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=tenant.name,
            metadata={"tenant_id": str(tenant.id)},
        )
        tenant.stripe_customer_id = customer.id
        await db.flush()

    try:
        # Create a Checkout session for the one-time payment
        session = stripe.checkout.Session.create(
            customer=tenant.stripe_customer_id,
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(body.amount * 100),
                        "product_data": {
                            "name": f"BlastWave SMS Credits - ${body.amount}",
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=(
                f"{settings.app_url}/billing?credits=purchased"
                f"&session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{settings.app_url}/billing?credits=canceled",
            metadata={
                "tenant_id": str(tenant.id),
                "type": "credit_purchase",
                "amount": str(body.amount),
            },
        )
    except Exception as e:
        logger.exception("Stripe credit purchase failed")
        raise HTTPException(
            status_code=502, detail=f"Stripe error: {str(e)}"
        )

    # Note: Credits are added by the webhook handler upon payment success,
    # not here. This just initiates the payment flow.
    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "amount": float(body.amount),
    }


# ---------------------------------------------------------------------------
# GET /invoices -- Invoice history
# ---------------------------------------------------------------------------

@router.get("/invoices")
async def list_invoices(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List Stripe invoices for the tenant."""
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant or not tenant.stripe_customer_id:
        return {"invoices": []}

    stripe = _get_stripe()

    try:
        invoices = stripe.Invoice.list(
            customer=tenant.stripe_customer_id,
            limit=limit,
        )
    except Exception as e:
        logger.warning("Failed to fetch Stripe invoices: %s", e)
        return {"invoices": [], "error": "Could not fetch invoices"}

    return {
        "invoices": [
            {
                "id": inv.id,
                "number": inv.number,
                "status": inv.status,
                "amount_due": inv.amount_due / 100,
                "amount_paid": inv.amount_paid / 100,
                "currency": inv.currency,
                "period_start": inv.period_start,
                "period_end": inv.period_end,
                "hosted_invoice_url": inv.hosted_invoice_url,
                "invoice_pdf": inv.invoice_pdf,
                "created": inv.created,
            }
            for inv in invoices.data
        ]
    }


# ---------------------------------------------------------------------------
# GET /events -- Billing event history
# ---------------------------------------------------------------------------

@router.get("/events")
async def list_billing_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    event_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List billing events (sms_sent, mms_sent, credit_purchase, etc.)."""
    tenant_id = user.tenant_id

    base_filter = [BillingEvent.tenant_id == tenant_id]
    if event_type:
        base_filter.append(BillingEvent.event_type == event_type)

    count_q = select(func.count(BillingEvent.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    data_q = (
        select(BillingEvent)
        .where(*base_filter)
        .order_by(BillingEvent.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "quantity": e.quantity,
                "unit_cost": float(e.unit_cost),
                "total_cost": float(e.total_cost),
                "campaign_id": str(e.campaign_id) if e.campaign_id else None,
                "stripe_invoice_item_id": e.stripe_invoice_item_id,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# GET /plans -- Available plan details
# ---------------------------------------------------------------------------

@router.get("/plans")
async def list_plans(
    user: User = Depends(get_current_user),
):
    """List all available subscription plans with feature limits."""
    plans_list = []
    for tier, plan in PLANS.items():
        plans_list.append({
            "tier": plan["tier"],
            "name": plan["name"],
            "price": float(plan["price"]),
            "included_sms": plan["included_sms"],
            "included_mms": plan["included_mms"],
            "max_numbers": plan["max_numbers"],
            "max_users": plan["max_users"],
            "max_contacts": plan["max_contacts"],
            "max_ai_agents": plan["max_ai_agents"],
        })

    return {"plans": plans_list}
