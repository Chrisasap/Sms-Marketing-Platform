"""Platform admin panel router.

Provides superadmin-only endpoints for tenant management, impersonation,
global platform stats, worker status, and system health checks.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_superadmin
from app.models.user import User
from app.models.tenant import Tenant
from app.models.campaign_message import CampaignMessage
from app.models.billing_event import BillingEvent
from app.models.contact import Contact
from app.models.phone_number import PhoneNumber
from app.models.dlc_application import DLCApplication
from app.models.brand import Brand10DLC
from app.models.campaign_10dlc import Campaign10DLC
from app.models.audit_log import AuditLog
from app.models.ai_review_result import AIReviewResult
from app.models.ai_review_prompt import AIReviewPrompt
from app.models.message import Message
from app.schemas.compliance import DLCApplicationResponse, DLCReviewAction
from app.services.auth import create_access_token
from app.services.bandwidth import bandwidth_client, BandwidthError

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /tenants -- List all tenants (superadmin only)
# ---------------------------------------------------------------------------

@router.get("/tenants")
async def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    plan_tier: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """List all tenants on the platform with filtering and search."""
    base_filter = [Tenant.deleted_at.is_(None)]

    if status_filter:
        base_filter.append(Tenant.status == status_filter)
    if plan_tier:
        base_filter.append(Tenant.plan_tier == plan_tier)
    if search:
        base_filter.append(
            or_(
                Tenant.name.ilike(f"%{search}%"),
                Tenant.slug.ilike(f"%{search}%"),
            )
        )

    count_q = select(func.count(Tenant.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    data_q = (
        select(Tenant)
        .where(*base_filter)
        .order_by(Tenant.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    tenants = result.scalars().all()

    # Batch-fetch counts for all tenants in the page to avoid N+1 queries
    tenant_ids = [t.id for t in tenants]

    user_counts: dict = {}
    contact_counts: dict = {}
    number_counts: dict = {}

    if tenant_ids:
        # User counts per tenant
        user_count_q = (
            select(User.tenant_id, func.count(User.id))
            .where(User.tenant_id.in_(tenant_ids))
            .group_by(User.tenant_id)
        )
        user_count_result = await db.execute(user_count_q)
        user_counts = {row[0]: row[1] for row in user_count_result.all()}

        # Contact counts per tenant
        contact_count_q = (
            select(Contact.tenant_id, func.count(Contact.id))
            .where(Contact.tenant_id.in_(tenant_ids))
            .group_by(Contact.tenant_id)
        )
        contact_count_result = await db.execute(contact_count_q)
        contact_counts = {row[0]: row[1] for row in contact_count_result.all()}

        # Active phone number counts per tenant
        number_count_q = (
            select(PhoneNumber.tenant_id, func.count(PhoneNumber.id))
            .where(
                PhoneNumber.tenant_id.in_(tenant_ids),
                PhoneNumber.status == "active",
            )
            .group_by(PhoneNumber.tenant_id)
        )
        number_count_result = await db.execute(number_count_q)
        number_counts = {row[0]: row[1] for row in number_count_result.all()}

    items = []
    for t in tenants:
        items.append({
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "plan_tier": t.plan_tier,
            "status": t.status,
            "credit_balance": float(t.credit_balance),
            "user_count": user_counts.get(t.id, 0),
            "contact_count": contact_counts.get(t.id, 0),
            "phone_number_count": number_counts.get(t.id, 0),
            "stripe_customer_id": t.stripe_customer_id,
            "created_at": t.created_at.isoformat(),
        })

    return {
        "tenants": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# GET /tenants/{id} -- Tenant detail
# ---------------------------------------------------------------------------

@router.get("/tenants/{tenant_id}")
async def get_tenant_detail(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Get detailed information about a specific tenant."""
    result = await db.execute(
        select(Tenant)
        .options(
            selectinload(Tenant.users),
            selectinload(Tenant.phone_numbers),
        )
        .where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Users and phone numbers are eager-loaded via selectinload
    users = tenant.users
    numbers = tenant.phone_numbers

    # Contact stats
    contact_count_q = select(func.count(Contact.id)).where(
        Contact.tenant_id == tenant.id
    )
    contact_result = await db.execute(contact_count_q)
    contact_count = contact_result.scalar() or 0

    # Message stats (last 30 days)
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    msg_count_q = select(func.count(CampaignMessage.id)).where(
        CampaignMessage.tenant_id == tenant.id,
        CampaignMessage.sent_at >= period_start,
    )
    msg_result = await db.execute(msg_count_q)
    messages_30d = msg_result.scalar() or 0

    # Revenue (billing events last 30 days)
    revenue_q = select(
        func.coalesce(func.sum(BillingEvent.total_cost), 0)
    ).where(
        BillingEvent.tenant_id == tenant.id,
        BillingEvent.created_at >= period_start,
    )
    revenue_result = await db.execute(revenue_q)
    revenue_30d = float(revenue_result.scalar() or 0)

    return {
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "plan_tier": tenant.plan_tier,
            "status": tenant.status,
            "credit_balance": float(tenant.credit_balance),
            "stripe_customer_id": tenant.stripe_customer_id,
            "stripe_subscription_id": tenant.stripe_subscription_id,
            "bandwidth_site_id": tenant.bandwidth_site_id,
            "bandwidth_location_id": tenant.bandwidth_location_id,
            "bandwidth_application_id": tenant.bandwidth_application_id,
            "settings": tenant.settings or {},
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat(),
        },
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role,
                "is_active": u.is_active,
                "mfa_enabled": u.mfa_enabled,
                "last_login_at": (
                    u.last_login_at.isoformat() if u.last_login_at else None
                ),
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "phone_numbers": [
            {
                "id": str(pn.id),
                "number": pn.number,
                "number_type": pn.number_type,
                "status": pn.status,
                "monthly_cost": float(pn.monthly_cost),
            }
            for pn in numbers
        ],
        "stats": {
            "contact_count": contact_count,
            "messages_30d": messages_30d,
            "revenue_30d": revenue_30d,
        },
    }


# ---------------------------------------------------------------------------
# PUT /tenants/{id} -- Update tenant (suspend, change plan, etc.)
# ---------------------------------------------------------------------------

@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Update a tenant's status, plan tier, credit balance, or settings.

    Body fields (all optional):
    - ``status``: "active", "suspended", "canceled"
    - ``plan_tier``: "free_trial", "starter", "growth", "enterprise"
    - ``credit_balance``: Decimal amount
    - ``settings``: dict
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if "status" in body:
        valid_statuses = {"active", "suspended", "canceled"}
        if body["status"] not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of: {', '.join(sorted(valid_statuses))}",
            )
        tenant.status = body["status"]

        # If suspending, deactivate all users
        if body["status"] == "suspended":
            users_q = select(User).where(User.tenant_id == tenant.id)
            users_result = await db.execute(users_q)
            for u in users_result.scalars().all():
                if not u.is_superadmin:
                    u.is_active = False

    if "plan_tier" in body:
        valid_tiers = {"free_trial", "starter", "growth", "enterprise"}
        if body["plan_tier"] not in valid_tiers:
            raise HTTPException(
                status_code=400,
                detail=f"Plan tier must be one of: {', '.join(sorted(valid_tiers))}",
            )
        tenant.plan_tier = body["plan_tier"]

    if "credit_balance" in body:
        from decimal import Decimal

        tenant.credit_balance = Decimal(str(body["credit_balance"]))

    if "settings" in body:
        tenant.settings = body["settings"]

    if "name" in body:
        tenant.name = body["name"]

    await db.commit()
    await db.refresh(tenant)

    return {
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "plan_tier": tenant.plan_tier,
            "status": tenant.status,
            "credit_balance": float(tenant.credit_balance),
            "settings": tenant.settings or {},
            "updated_at": tenant.updated_at.isoformat(),
        },
        "message": "Tenant updated",
    }


# ---------------------------------------------------------------------------
# POST /tenants/{id}/impersonate -- Get impersonation token
# ---------------------------------------------------------------------------

@router.post("/tenants/{tenant_id}/impersonate")
async def impersonate_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Generate an access token to impersonate a tenant's owner.

    Returns a short-lived JWT that grants access as the tenant's owner
    user, allowing the superadmin to debug or assist from within the
    tenant's context.
    """
    # Find tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Find the tenant owner (or first admin)
    owner_q = (
        select(User)
        .where(
            User.tenant_id == tenant_id,
            User.is_active == True,
        )
        .order_by(
            # Prefer owner, then admin, then anyone
            func.array_position(
                ["owner", "admin", "sender"],
                User.role,
            ).asc().nullslast()
        )
        .limit(1)
    )
    # Fallback: simpler query if array_position is unavailable
    try:
        owner_result = await db.execute(owner_q)
        target_user = owner_result.scalar_one_or_none()
    except Exception:
        # Simpler fallback
        owner_q_simple = (
            select(User)
            .where(
                User.tenant_id == tenant_id,
                User.is_active == True,
                User.role == "owner",
            )
            .limit(1)
        )
        owner_result = await db.execute(owner_q_simple)
        target_user = owner_result.scalar_one_or_none()

        if not target_user:
            admin_q = (
                select(User)
                .where(
                    User.tenant_id == tenant_id,
                    User.is_active == True,
                )
                .limit(1)
            )
            admin_result = await db.execute(admin_q)
            target_user = admin_result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="No active user found in this tenant",
        )

    # Generate a short-lived impersonation token
    token = create_access_token(
        str(target_user.id),
        str(tenant_id),
        target_user.role,
    )

    logger.warning(
        "Superadmin %s impersonating tenant %s (user %s)",
        user.email,
        tenant.slug,
        target_user.email,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
        },
        "impersonated_user": {
            "id": str(target_user.id),
            "email": target_user.email,
            "role": target_user.role,
        },
    }


# ---------------------------------------------------------------------------
# GET /stats -- Global platform stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Global platform-wide statistics for the admin dashboard."""
    # Tenant counts
    total_tenants_q = select(func.count(Tenant.id)).where(
        Tenant.deleted_at.is_(None)
    )
    total_result = await db.execute(total_tenants_q)
    total_tenants = total_result.scalar() or 0

    active_tenants_q = select(func.count(Tenant.id)).where(
        Tenant.deleted_at.is_(None),
        Tenant.status == "active",
    )
    active_result = await db.execute(active_tenants_q)
    active_tenants = active_result.scalar() or 0

    # Totals by plan
    plan_breakdown_q = (
        select(Tenant.plan_tier, func.count(Tenant.id))
        .where(Tenant.deleted_at.is_(None))
        .group_by(Tenant.plan_tier)
    )
    plan_result = await db.execute(plan_breakdown_q)
    plan_breakdown = {row[0]: row[1] for row in plan_result.all()}

    # Today's messages
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    messages_today_q = select(func.count(CampaignMessage.id)).where(
        CampaignMessage.sent_at >= today_start,
    )
    today_result = await db.execute(messages_today_q)
    messages_today = today_result.scalar() or 0

    # This month's messages
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    messages_month_q = select(func.count(CampaignMessage.id)).where(
        CampaignMessage.sent_at >= month_start,
    )
    month_result = await db.execute(messages_month_q)
    messages_month = month_result.scalar() or 0

    # Revenue this month
    revenue_month_q = select(
        func.coalesce(func.sum(BillingEvent.total_cost), 0)
    ).where(BillingEvent.created_at >= month_start)
    revenue_result = await db.execute(revenue_month_q)
    revenue_month = float(revenue_result.scalar() or 0)

    # Total users
    total_users_q = select(func.count(User.id))
    users_result = await db.execute(total_users_q)
    total_users = users_result.scalar() or 0

    # Total phone numbers
    total_numbers_q = select(func.count(PhoneNumber.id)).where(
        PhoneNumber.status == "active"
    )
    numbers_result = await db.execute(total_numbers_q)
    total_numbers = numbers_result.scalar() or 0

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "plan_breakdown": plan_breakdown,
        "total_users": total_users,
        "total_phone_numbers": total_numbers,
        "messages_today": messages_today,
        "messages_this_month": messages_month,
        "revenue_this_month": revenue_month,
    }


# ---------------------------------------------------------------------------
# GET /workers -- Celery worker status
# ---------------------------------------------------------------------------

@router.get("/workers")
async def get_worker_status(
    user: User = Depends(require_superadmin()),
):
    """Check Celery worker status and queue depths.

    Attempts to connect to the Celery broker and inspect active workers.
    Returns a degraded response if the broker is unreachable.
    """
    try:
        from app.config import get_settings

        settings = get_settings()
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        redis_info = await r.info("server")
        redis_ping = await r.ping()

        # Check Celery queue lengths
        celery_default = await r.llen("celery")
        campaign_queue = await r.llen("campaign_queue")
        drip_queue = await r.llen("drip_queue")

        await r.aclose()

        return {
            "redis": {
                "connected": redis_ping,
                "version": redis_info.get("redis_version", "unknown"),
            },
            "queues": {
                "celery_default": celery_default,
                "campaign_queue": campaign_queue,
                "drip_queue": drip_queue,
            },
            "status": "healthy",
        }

    except Exception as e:
        logger.warning("Worker status check failed: %s", e)
        return {
            "redis": {"connected": False, "error": str(e)},
            "queues": {},
            "status": "degraded",
        }


# ---------------------------------------------------------------------------
# GET /health -- System health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def system_health_check(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Comprehensive system health check covering database, Redis, and
    Bandwidth API connectivity.
    """
    health = {
        "database": {"status": "unknown"},
        "redis": {"status": "unknown"},
        "bandwidth": {"status": "unknown"},
        "overall": "unknown",
    }

    # Database
    try:
        result = await db.execute(select(func.now()))
        db_time = result.scalar()
        health["database"] = {
            "status": "healthy",
            "server_time": str(db_time),
        }
    except Exception as e:
        health["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Redis
    try:
        from app.config import get_settings

        settings = get_settings()
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        pong = await r.ping()
        redis_info = await r.info("memory")
        await r.aclose()
        health["redis"] = {
            "status": "healthy" if pong else "unhealthy",
            "used_memory_human": redis_info.get("used_memory_human", "unknown"),
        }
    except Exception as e:
        health["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Bandwidth API
    try:
        from app.services.bandwidth import bandwidth_client

        # A lightweight check -- just list sites
        sites = await bandwidth_client.list_sites()
        health["bandwidth"] = {
            "status": "healthy",
            "site_count": len(sites) if isinstance(sites, list) else 0,
        }
    except Exception as e:
        health["bandwidth"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Overall
    statuses = [
        health["database"]["status"],
        health["redis"]["status"],
        health["bandwidth"]["status"],
    ]
    if all(s == "healthy" for s in statuses):
        health["overall"] = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        health["overall"] = "degraded"
    else:
        health["overall"] = "unknown"

    return health


# ---------------------------------------------------------------------------
# GET /analytics/overview -- Real-time KPI snapshot
# ---------------------------------------------------------------------------

@router.get("/analytics/overview")
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Real-time platform KPI snapshot for the admin dashboard."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Tenant counts
    total_tenants = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.deleted_at.is_(None))
    )).scalar() or 0

    active_tenants_24h = (await db.execute(
        select(func.count(func.distinct(User.tenant_id))).where(User.last_login_at >= now - timedelta(hours=24))
    )).scalar() or 0

    new_tenants_7d = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.deleted_at.is_(None), Tenant.created_at >= week_ago)
    )).scalar() or 0

    new_tenants_30d = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.deleted_at.is_(None), Tenant.created_at >= month_ago)
    )).scalar() or 0

    # User counts
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users_24h = (await db.execute(
        select(func.count(User.id)).where(User.last_login_at >= now - timedelta(hours=24))
    )).scalar() or 0

    # Messages
    messages_24h = (await db.execute(
        select(func.count(CampaignMessage.id)).where(CampaignMessage.sent_at >= now - timedelta(hours=24))
    )).scalar() or 0

    messages_7d = (await db.execute(
        select(func.count(CampaignMessage.id)).where(CampaignMessage.sent_at >= week_ago)
    )).scalar() or 0

    messages_30d = (await db.execute(
        select(func.count(CampaignMessage.id)).where(CampaignMessage.sent_at >= month_ago)
    )).scalar() or 0

    # Revenue (MRR approximation from this month's billing)
    mrr = float((await db.execute(
        select(func.coalesce(func.sum(BillingEvent.total_cost), 0)).where(BillingEvent.created_at >= month_start)
    )).scalar() or 0)

    # DLC Queue
    dlc_pending = (await db.execute(
        select(func.count(DLCApplication.id)).where(DLCApplication.status == "pending_review")
    )).scalar() or 0

    # System health summary
    health_status = "healthy"
    try:
        await db.execute(select(func.now()))
    except Exception:
        health_status = "degraded"

    return {
        "total_tenants": total_tenants,
        "active_tenants_24h": active_tenants_24h,
        "new_tenants_7d": new_tenants_7d,
        "new_tenants_30d": new_tenants_30d,
        "total_users": total_users,
        "active_users_24h": active_users_24h,
        "messages_24h": messages_24h,
        "messages_7d": messages_7d,
        "messages_30d": messages_30d,
        "mrr": mrr,
        "dlc_queue_pending": dlc_pending,
        "system_health": health_status,
    }


# ---------------------------------------------------------------------------
# GET /analytics/messages -- Message volume time series
# ---------------------------------------------------------------------------

@router.get("/analytics/messages")
async def analytics_messages(
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Message volume time series for charts."""
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    start = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", CampaignMessage.sent_at).label("day"),
            func.count(CampaignMessage.id).label("count"),
        )
        .where(CampaignMessage.sent_at >= start)
        .group_by("day")
        .order_by("day")
    )
    rows = result.all()

    return {
        "period": period,
        "data": [{"date": row[0].isoformat() if row[0] else None, "count": row[1]} for row in rows],
    }


# ---------------------------------------------------------------------------
# GET /analytics/revenue -- Revenue time series
# ---------------------------------------------------------------------------

@router.get("/analytics/revenue")
async def analytics_revenue(
    period: str = Query("12m", regex="^(3m|6m|12m)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Monthly revenue time series."""
    months = {"3m": 3, "6m": 6, "12m": 12}[period]
    start = datetime.now(timezone.utc) - timedelta(days=months * 30)

    result = await db.execute(
        select(
            func.date_trunc("month", BillingEvent.created_at).label("month"),
            func.coalesce(func.sum(BillingEvent.total_cost), 0).label("revenue"),
        )
        .where(BillingEvent.created_at >= start)
        .group_by("month")
        .order_by("month")
    )
    rows = result.all()

    return {
        "period": period,
        "data": [{"month": row[0].isoformat() if row[0] else None, "revenue": float(row[1])} for row in rows],
    }


# ---------------------------------------------------------------------------
# GET /analytics/tenants/growth -- Tenant signup trend
# ---------------------------------------------------------------------------

@router.get("/analytics/tenants/growth")
async def analytics_tenant_growth(
    period: str = Query("90d", regex="^(30d|90d|365d)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Tenant signup trend over time."""
    days = {"30d": 30, "90d": 90, "365d": 365}[period]
    start = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", Tenant.created_at).label("day"),
            func.count(Tenant.id).label("count"),
        )
        .where(Tenant.created_at >= start, Tenant.deleted_at.is_(None))
        .group_by("day")
        .order_by("day")
    )
    rows = result.all()

    return {
        "period": period,
        "data": [{"date": row[0].isoformat() if row[0] else None, "count": row[1]} for row in rows],
    }


# ---------------------------------------------------------------------------
# GET /analytics/compliance -- DLC approval analytics
# ---------------------------------------------------------------------------

@router.get("/analytics/compliance")
async def analytics_compliance(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """10DLC compliance analytics: approval rates, AI metrics."""
    total = (await db.execute(select(func.count(DLCApplication.id)))).scalar() or 0
    approved = (await db.execute(
        select(func.count(DLCApplication.id)).where(DLCApplication.status.in_(["approved", "submitted", "registered"]))
    )).scalar() or 0
    rejected = (await db.execute(
        select(func.count(DLCApplication.id)).where(DLCApplication.status == "rejected")
    )).scalar() or 0
    pending = (await db.execute(
        select(func.count(DLCApplication.id)).where(DLCApplication.status == "pending_review")
    )).scalar() or 0

    approval_rate = (approved / total * 100) if total > 0 else 0

    # AI review metrics
    total_ai_reviews = (await db.execute(
        select(func.count(AIReviewResult.id)).where(AIReviewResult.verdict != "ERROR")
    )).scalar() or 0
    avg_ai_score = float((await db.execute(
        select(func.coalesce(func.avg(AIReviewResult.score), 0)).where(AIReviewResult.verdict != "ERROR")
    )).scalar() or 0)

    return {
        "total_submissions": total,
        "total_approved": approved,
        "total_rejected": rejected,
        "total_pending": pending,
        "approval_rate": round(approval_rate, 1),
        "ai_metrics": {
            "total_reviews": total_ai_reviews,
            "avg_score": round(avg_ai_score, 1),
        },
    }


# ---------------------------------------------------------------------------
# GET /activity-feed -- Recent platform events
# ---------------------------------------------------------------------------

@router.get("/activity-feed")
async def activity_feed(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Recent platform activity for the admin dashboard feed."""
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    # Enrich with user emails
    user_ids = list({l.user_id for l in logs if l.user_id})
    user_emails = {}
    if user_ids:
        user_q = select(User.id, User.email).where(User.id.in_(user_ids))
        user_result = await db.execute(user_q)
        user_emails = {row[0]: row[1] for row in user_result.all()}

    return {
        "events": [
            {
                "id": str(l.id),
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "user_email": user_emails.get(l.user_id, "system"),
                "details": l.details,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
    }


# ---------------------------------------------------------------------------
# AI Review Prompt Management (must be before {application_id} routes)
# ---------------------------------------------------------------------------

@router.get("/dlc-queue/ai-prompts")
async def list_ai_prompts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """List all AI review prompts."""
    result = await db.execute(
        select(AIReviewPrompt).order_by(AIReviewPrompt.prompt_type, AIReviewPrompt.version.desc())
    )
    prompts = result.scalars().all()

    return {
        "prompts": [
            {
                "id": str(p.id),
                "name": p.name,
                "prompt_type": p.prompt_type,
                "system_prompt": p.system_prompt,
                "model": p.model,
                "temperature": p.temperature,
                "is_active": p.is_active,
                "version": p.version,
                "created_at": p.created_at.isoformat(),
            }
            for p in prompts
        ],
    }


@router.put("/dlc-queue/ai-prompts/{prompt_id}")
async def update_ai_prompt(
    prompt_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Update an AI review prompt (creates a new version)."""
    result = await db.execute(
        select(AIReviewPrompt).where(AIReviewPrompt.id == prompt_id)
    )
    old_prompt = result.scalar_one_or_none()
    if not old_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Deactivate old prompt
    old_prompt.is_active = False

    # Create new version
    new_prompt = AIReviewPrompt(
        name=body.get("name", old_prompt.name),
        prompt_type=old_prompt.prompt_type,
        system_prompt=body.get("system_prompt", old_prompt.system_prompt),
        model=body.get("model", old_prompt.model),
        temperature=body.get("temperature", old_prompt.temperature),
        is_active=True,
        version=old_prompt.version + 1,
        created_by=user.id,
    )
    db.add(new_prompt)

    audit = AuditLog(
        tenant_id=None,
        user_id=user.id,
        action="ai_prompt_updated",
        resource_type="ai_review_prompt",
        resource_id=str(old_prompt.id),
        details={"old_version": old_prompt.version, "new_version": new_prompt.version},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_prompt)

    return {
        "message": "Prompt updated (new version created)",
        "prompt": {
            "id": str(new_prompt.id),
            "name": new_prompt.name,
            "prompt_type": new_prompt.prompt_type,
            "model": new_prompt.model,
            "temperature": new_prompt.temperature,
            "version": new_prompt.version,
            "is_active": new_prompt.is_active,
        },
    }


# ---------------------------------------------------------------------------
# DLC Review Queue (superadmin only)
# ---------------------------------------------------------------------------

@router.get("/dlc-queue")
async def list_dlc_applications(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    app_type: str | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """List all DLC applications pending review (superadmin only)."""
    base = []
    if status_filter:
        base.append(DLCApplication.status == status_filter)
    else:
        # Default: show pending_review
        base.append(DLCApplication.status == "pending_review")
    if app_type:
        base.append(DLCApplication.application_type == app_type)

    count_result = await db.execute(
        select(func.count(DLCApplication.id)).where(*base)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(DLCApplication)
        .where(*base)
        .order_by(DLCApplication.submitted_at.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    apps = result.scalars().all()

    # Enrich with tenant names
    tenant_ids = list({a.tenant_id for a in apps})
    tenant_names = {}
    if tenant_ids:
        tenant_q = select(Tenant.id, Tenant.name).where(Tenant.id.in_(tenant_ids))
        tenant_result = await db.execute(tenant_q)
        tenant_names = {row[0]: row[1] for row in tenant_result.all()}

    # Batch-fetch latest AI review score + verdict for all applications in this page
    app_ids = [a.id for a in apps]
    ai_reviews: dict[uuid.UUID, dict] = {}
    if app_ids:
        # Subquery: latest review per application (max created_at)
        latest_subq = (
            select(
                AIReviewResult.dlc_application_id,
                func.max(AIReviewResult.created_at).label("max_created"),
            )
            .where(AIReviewResult.dlc_application_id.in_(app_ids))
            .group_by(AIReviewResult.dlc_application_id)
            .subquery()
        )
        review_q = (
            select(
                AIReviewResult.dlc_application_id,
                AIReviewResult.score,
                AIReviewResult.verdict,
            )
            .join(
                latest_subq,
                (AIReviewResult.dlc_application_id == latest_subq.c.dlc_application_id)
                & (AIReviewResult.created_at == latest_subq.c.max_created),
            )
        )
        review_result = await db.execute(review_q)
        for row in review_result.all():
            ai_reviews[row[0]] = {"ai_score": row[1], "ai_verdict": row[2]}

    items = []
    for a in apps:
        data = DLCApplicationResponse.model_validate(a).model_dump(mode="json")
        data["tenant_name"] = tenant_names.get(a.tenant_id, "Unknown")
        review_data = ai_reviews.get(a.id, {})
        data["ai_score"] = review_data.get("ai_score")
        data["ai_verdict"] = review_data.get("ai_verdict")
        items.append(data)

    return {
        "applications": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/dlc-queue/{application_id}")
async def get_dlc_application_detail(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Get full details of a DLC application for review."""
    result = await db.execute(
        select(DLCApplication).where(DLCApplication.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get tenant info
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == app.tenant_id))
    tenant = tenant_result.scalar_one_or_none()

    # Get brand info if applicable
    brand_data = None
    if app.brand_id:
        brand_result = await db.execute(select(Brand10DLC).where(Brand10DLC.id == app.brand_id))
        brand = brand_result.scalar_one_or_none()
        if brand:
            brand_data = {
                "id": str(brand.id),
                "legal_name": brand.legal_name,
                "entity_type": brand.entity_type,
                "ein": brand.ein,
                "registration_status": brand.registration_status,
                "bandwidth_brand_id": brand.bandwidth_brand_id,
            }

    # Get campaign info if applicable
    campaign_data = None
    if app.campaign_id:
        camp_result = await db.execute(select(Campaign10DLC).where(Campaign10DLC.id == app.campaign_id))
        camp = camp_result.scalar_one_or_none()
        if camp:
            campaign_data = {
                "id": str(camp.id),
                "use_case": camp.use_case,
                "description": camp.description,
                "status": camp.status,
                "bandwidth_campaign_id": camp.bandwidth_campaign_id,
            }

    return {
        "application": DLCApplicationResponse.model_validate(app).model_dump(mode="json"),
        "tenant": {
            "id": str(tenant.id) if tenant else None,
            "name": tenant.name if tenant else "Unknown",
            "plan_tier": tenant.plan_tier if tenant else None,
        },
        "brand": brand_data,
        "campaign": campaign_data,
    }


# ---------------------------------------------------------------------------
# AI-Powered DLC Review Endpoints
# ---------------------------------------------------------------------------

@router.post("/dlc-queue/{application_id}/ai-review")
async def trigger_ai_review(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Trigger AI review of a DLC application. Returns 202 if queued."""
    result = await db.execute(
        select(DLCApplication).where(DLCApplication.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check for recent review (< 1 hour old)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    existing = await db.execute(
        select(AIReviewResult)
        .where(
            AIReviewResult.dlc_application_id == application_id,
            AIReviewResult.created_at >= one_hour_ago,
            AIReviewResult.verdict != "ERROR",
        )
        .order_by(AIReviewResult.created_at.desc())
        .limit(1)
    )
    cached = existing.scalar_one_or_none()
    if cached:
        return {
            "status": "cached",
            "review": {
                "id": str(cached.id),
                "score": cached.score,
                "verdict": cached.verdict,
                "issues": cached.issues,
                "enhanced_fields": cached.enhanced_fields,
                "compliance_flags": cached.compliance_flags,
                "summary": cached.summary,
                "model_used": cached.model_used,
                "tokens_used": cached.tokens_used,
                "latency_ms": cached.latency_ms,
                "created_at": cached.created_at.isoformat(),
            },
        }

    # Enqueue AI review task
    from app.tasks.ai_dlc_review import run_ai_dlc_review
    task = run_ai_dlc_review.delay(str(application_id))

    return {"status": "queued", "task_id": task.id}


@router.get("/dlc-queue/{application_id}/ai-review")
async def get_ai_review(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Get the latest AI review result for an application."""
    result = await db.execute(
        select(AIReviewResult)
        .where(AIReviewResult.dlc_application_id == application_id)
        .order_by(AIReviewResult.created_at.desc())
        .limit(1)
    )
    review = result.scalar_one_or_none()
    if not review:
        return {"review": None}

    return {
        "review": {
            "id": str(review.id),
            "score": review.score,
            "verdict": review.verdict,
            "issues": review.issues,
            "enhanced_fields": review.enhanced_fields,
            "compliance_flags": review.compliance_flags,
            "summary": review.summary,
            "model_used": review.model_used,
            "tokens_used": review.tokens_used,
            "latency_ms": review.latency_ms,
            "error": review.error,
            "created_at": review.created_at.isoformat(),
        },
    }


@router.post("/dlc-queue/{application_id}/ai-enhance")
async def apply_ai_enhancements(
    application_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Apply AI-suggested enhancements to a DLC application.

    Body: {"accept_fields": ["description", "sample_messages"]} or {"accept_fields": "all"}
    """
    result = await db.execute(
        select(DLCApplication).where(DLCApplication.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get latest AI review
    review_result = await db.execute(
        select(AIReviewResult)
        .where(AIReviewResult.dlc_application_id == application_id, AIReviewResult.verdict != "ERROR")
        .order_by(AIReviewResult.created_at.desc())
        .limit(1)
    )
    review = review_result.scalar_one_or_none()
    if not review or not review.enhanced_fields:
        raise HTTPException(status_code=400, detail="No AI enhancements available")

    accept = body.get("accept_fields", [])
    enhanced = review.enhanced_fields

    updated_form = dict(app.form_data)  # copy
    fields_applied = []

    if accept == "all":
        for field, value in enhanced.items():
            updated_form[field] = value
            fields_applied.append(field)
    elif isinstance(accept, list):
        for field in accept:
            if field in enhanced:
                updated_form[field] = enhanced[field]
                fields_applied.append(field)

    app.form_data = updated_form

    # Audit log
    audit = AuditLog(
        tenant_id=app.tenant_id,
        user_id=user.id,
        action="dlc_ai_enhancement_applied",
        resource_type="dlc_application",
        resource_id=str(app.id),
        details={"fields_applied": fields_applied, "review_id": str(review.id)},
    )
    db.add(audit)
    await db.commit()

    return {
        "message": f"Applied AI enhancements to {len(fields_applied)} fields",
        "fields_applied": fields_applied,
        "updated_form_data": updated_form,
    }


@router.post("/dlc-queue/{application_id}/review")
async def review_dlc_application(
    application_id: uuid.UUID,
    body: DLCReviewAction,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Approve or reject a DLC application.

    On approve: submits to Bandwidth API, updates statuses.
    On reject: sets rejection reason, tenant can resubmit.
    """
    result = await db.execute(
        select(DLCApplication).where(DLCApplication.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail=f"Application is '{app.status}', not 'pending_review'",
        )

    now = datetime.now(timezone.utc)

    if body.action == "reject":
        app.status = "rejected"
        app.reviewed_by = user.id
        app.reviewed_at = now
        app.admin_notes = body.admin_notes
        app.rejection_reason = body.rejection_reason or "Rejected by admin"

        # Update the underlying brand/campaign status
        if app.brand_id:
            brand_result = await db.execute(select(Brand10DLC).where(Brand10DLC.id == app.brand_id))
            brand = brand_result.scalar_one_or_none()
            if brand:
                brand.registration_status = "rejected"
        if app.campaign_id:
            camp_result = await db.execute(select(Campaign10DLC).where(Campaign10DLC.id == app.campaign_id))
            camp = camp_result.scalar_one_or_none()
            if camp:
                camp.status = "rejected"

        audit = AuditLog(
            tenant_id=app.tenant_id,
            user_id=user.id,
            action="dlc_application_rejected",
            resource_type="dlc_application",
            resource_id=str(app.id),
            details={"reason": app.rejection_reason},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(app)

        return {
            "message": "Application rejected",
            "application": DLCApplicationResponse.model_validate(app).model_dump(mode="json"),
        }

    # ---- APPROVE: submit to Bandwidth ----
    app.status = "approved"
    app.reviewed_by = user.id
    app.reviewed_at = now
    app.admin_notes = body.admin_notes

    if app.application_type == "brand":
        brand_result = await db.execute(select(Brand10DLC).where(Brand10DLC.id == app.brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand:
            raise HTTPException(status_code=404, detail="Brand record not found")

        # Build Bandwidth payload with correct field names
        brand_payload = {
            "CompanyName": brand.legal_name,
            "DisplayName": brand.dba_name or brand.legal_name,
            "EntityType": brand.entity_type,
            "Ein": brand.ein,
            "Phone": brand.phone,
            "Email": brand.email,
            "Street": brand.street,
            "City": brand.city,
            "State": brand.state,
            "PostalCode": brand.zip_code,
            "Country": brand.country,
            "Vertical": brand.vertical,
            "IsMain": brand.is_main,
        }
        if brand.brand_relationship:
            brand_payload["BrandRelationship"] = brand.brand_relationship
        if brand.website:
            brand_payload["Website"] = brand.website
        if brand.stock_symbol:
            brand_payload["StockSymbol"] = brand.stock_symbol
        if brand.stock_exchange:
            brand_payload["StockExchange"] = brand.stock_exchange
        if brand.business_contact_email:
            brand_payload["BusinessContactEmail"] = brand.business_contact_email
        if brand.alt_business_id and brand.alt_business_id_type:
            brand_payload["AltBusinessId"] = brand.alt_business_id
            brand_payload["AltBusinessIdType"] = brand.alt_business_id_type

        try:
            bw_result = await bandwidth_client.register_brand(brand_payload)
            bw_brand_id = bw_result.get("brandId") or bw_result.get("id", "")

            brand.bandwidth_brand_id = bw_brand_id
            brand.registration_status = "submitted"
            brand.identity_status = bw_result.get("identityStatus", "PENDING")
            app.status = "submitted"
            app.bandwidth_response = bw_result

        except BandwidthError as e:
            app.status = "submission_failed"
            app.admin_notes = (app.admin_notes or "") + f"\nBandwidth error: {e.message}"
            brand.registration_status = "submission_failed"

    elif app.application_type == "campaign":
        camp_result = await db.execute(select(Campaign10DLC).where(Campaign10DLC.id == app.campaign_id))
        campaign = camp_result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign record not found")

        brand_result = await db.execute(select(Brand10DLC).where(Brand10DLC.id == app.brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand or not brand.bandwidth_brand_id:
            raise HTTPException(
                status_code=400,
                detail="Brand must be registered with Bandwidth before campaign can be submitted",
            )

        # Build Bandwidth payload with correct field names
        camp_payload = {
            "BrandId": brand.bandwidth_brand_id,
            "Usecase": campaign.use_case,
            "Description": campaign.description,
            "MessageFlow": campaign.message_flow,
            "HelpMessage": campaign.help_message,
            "HelpKeywords": campaign.help_keywords or "HELP",
            "OptoutMessage": campaign.optout_message,
            "OptoutKeywords": campaign.optout_keywords or "STOP",
            "SubscriberOptin": campaign.subscriber_optin,
            "SubscriberOptout": campaign.subscriber_optout,
            "SubscriberHelp": campaign.subscriber_help,
            "NumberPool": campaign.number_pool,
            "DirectLending": campaign.direct_lending,
            "EmbeddedLink": campaign.embedded_links,
            "EmbeddedPhone": campaign.embedded_phone,
            "AffiliateMarketing": campaign.affiliate_marketing,
            "AgeGated": campaign.age_gated,
            "AutoRenewal": campaign.auto_renewal,
        }

        # Sample messages as Sample1, Sample2, etc.
        for i, sample in enumerate(campaign.sample_messages[:5], 1):
            camp_payload[f"Sample{i}"] = sample

        if campaign.optin_message:
            camp_payload["OptinMessage"] = campaign.optin_message
        if campaign.optin_keywords:
            camp_payload["OptinKeywords"] = campaign.optin_keywords
        if campaign.sub_usecases:
            camp_payload["SubUsecases"] = ",".join(campaign.sub_usecases)
        if campaign.privacy_policy_link:
            camp_payload["PrivacyPolicyLink"] = campaign.privacy_policy_link
        if campaign.terms_and_conditions_link:
            camp_payload["TermsAndConditionsLink"] = campaign.terms_and_conditions_link

        try:
            bw_result = await bandwidth_client.register_campaign(camp_payload)
            bw_campaign_id = bw_result.get("campaignId") or bw_result.get("id", "")

            campaign.bandwidth_campaign_id = bw_campaign_id
            campaign.status = "submitted"
            if bw_result.get("messagingVolume", {}).get("mps"):
                campaign.mps_limit = int(bw_result["messagingVolume"]["mps"])
            app.status = "submitted"
            app.bandwidth_response = bw_result

        except BandwidthError as e:
            app.status = "submission_failed"
            app.admin_notes = (app.admin_notes or "") + f"\nBandwidth error: {e.message}"
            campaign.status = "submission_failed"

    audit = AuditLog(
        tenant_id=app.tenant_id,
        user_id=user.id,
        action=f"dlc_application_{app.status}",
        resource_type="dlc_application",
        resource_id=str(app.id),
        details={"bandwidth_status": app.status},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(app)

    return {
        "message": f"Application {app.status}",
        "application": DLCApplicationResponse.model_validate(app).model_dump(mode="json"),
    }


# ---------------------------------------------------------------------------
# Admin User Management
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_all_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = None,
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """List all users across all tenants."""
    filters = []
    if search:
        filters.append(
            or_(
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
            )
        )
    if role:
        filters.append(User.role == role)

    total = (await db.execute(select(func.count(User.id)).where(*filters))).scalar() or 0 if filters else (await db.execute(select(func.count(User.id)))).scalar() or 0

    q = select(User).order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    if filters:
        q = q.where(*filters)
    result = await db.execute(q)
    users_list = result.scalars().all()

    # Get tenant names
    tenant_ids = list({u.tenant_id for u in users_list if u.tenant_id})
    tenant_names = {}
    if tenant_ids:
        tn_result = await db.execute(select(Tenant.id, Tenant.name).where(Tenant.id.in_(tenant_ids)))
        tenant_names = {row[0]: row[1] for row in tn_result.all()}

    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_superadmin": u.is_superadmin,
                "tenant_id": str(u.tenant_id) if u.tenant_id else None,
                "tenant_name": tenant_names.get(u.tenant_id, "\u2014"),
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users_list
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.put("/users/{user_id}")
async def update_user_admin(
    user_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin()),
):
    """Update a user's role, active status, or superadmin flag."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}
    if "role" in body:
        target.role = body["role"]
        changes["role"] = body["role"]
    if "is_active" in body:
        target.is_active = body["is_active"]
        changes["is_active"] = body["is_active"]
    if "is_superadmin" in body:
        # Prevent self-demotion
        if target.id == admin.id and not body["is_superadmin"]:
            raise HTTPException(status_code=400, detail="Cannot revoke your own superadmin access")
        target.is_superadmin = body["is_superadmin"]
        changes["is_superadmin"] = body["is_superadmin"]

    audit = AuditLog(
        tenant_id=target.tenant_id,
        user_id=admin.id,
        action="user_updated_by_admin",
        resource_type="user",
        resource_id=str(target.id),
        details=changes,
    )
    db.add(audit)
    await db.commit()

    return {"message": "User updated", "changes": changes}


# ---------------------------------------------------------------------------
# Audit Log Viewer
# ---------------------------------------------------------------------------

@router.get("/audit-log")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: str | None = None,
    resource_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin()),
):
    """Browse the audit log."""
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    count_q = select(func.count(AuditLog.id))
    if filters:
        count_q = count_q.where(*filters)
    total = (await db.execute(count_q)).scalar() or 0

    q = select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    if filters:
        q = q.where(*filters)
    result = await db.execute(q)
    logs = result.scalars().all()

    user_ids = list({l.user_id for l in logs if l.user_id})
    user_emails = {}
    if user_ids:
        ue_result = await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))
        user_emails = {row[0]: row[1] for row in ue_result.all()}

    return {
        "logs": [
            {
                "id": str(l.id),
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "user_email": user_emails.get(l.user_id, "system"),
                "details": l.details,
                "ip_address": l.ip_address,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
