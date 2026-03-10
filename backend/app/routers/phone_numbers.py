"""Phone number management -- search, order, list, release, configure."""

import uuid
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.phone_number import PhoneNumber
from app.models.tenant import Tenant
from app.models.campaign_message import CampaignMessage
from app.models.user import User
from app.schemas.phone_number import (
    NumberSearchRequest,
    AvailableNumber,
    NumberOrderRequest,
    NumberResponse,
)
from app.services.bandwidth import bandwidth_client, BandwidthError

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic helpers for request/response bodies not in schemas yet
# ---------------------------------------------------------------------------

class NumberConfigUpdate(BaseModel):
    label: str | None = None
    campaign_id: uuid.UUID | None = None
    capabilities: list[str] | None = None


class NumberStatsResponse(BaseModel):
    sent: int
    delivered: int
    failed: int


# ---------------------------------------------------------------------------
# GET / -- List tenant phone numbers
# ---------------------------------------------------------------------------

@router.get("/")
async def list_phone_numbers(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    number_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all phone numbers owned by the tenant, with pagination."""
    query = select(PhoneNumber).where(
        PhoneNumber.tenant_id == user.tenant_id
    )
    count_query = select(func.count(PhoneNumber.id)).where(
        PhoneNumber.tenant_id == user.tenant_id
    )

    if number_type:
        query = query.where(PhoneNumber.number_type == number_type)
        count_query = count_query.where(PhoneNumber.number_type == number_type)
    if status_filter:
        query = query.where(PhoneNumber.status == status_filter)
        count_query = count_query.where(PhoneNumber.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query.order_by(PhoneNumber.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    numbers = result.scalars().all()

    return {
        "numbers": [
            NumberResponse.model_validate(n) for n in numbers
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST /search -- Search available numbers via Bandwidth
# ---------------------------------------------------------------------------

@router.post("/search")
async def search_available_numbers(
    body: NumberSearchRequest,
    user: User = Depends(get_current_user),
):
    """Search for available phone numbers to purchase from Bandwidth."""
    try:
        raw = await bandwidth_client.search_available_numbers(
            area_code=body.area_code,
            state=body.state,
            city=body.city,
            quantity=body.quantity,
            number_type=body.number_type,
        )
    except BandwidthError as e:
        raise HTTPException(status_code=502, detail=f"Bandwidth error: {e.message}")

    # Normalise Bandwidth response into our schema
    available: list[dict] = []
    for item in raw:
        if isinstance(item, str):
            available.append({
                "number": item,
                "city": None,
                "state": None,
                "rate_center": None,
                "monthly_cost": Decimal("1.00"),
            })
        elif isinstance(item, dict):
            available.append({
                "number": item.get("telephoneNumber", item.get("fullNumber", "")),
                "city": item.get("city"),
                "state": item.get("state"),
                "rate_center": item.get("rateCenter"),
                "monthly_cost": Decimal("1.00"),
            })

    return {"available_numbers": available}


# ---------------------------------------------------------------------------
# POST /order -- Order (purchase) phone numbers
# ---------------------------------------------------------------------------

@router.post("/order", status_code=status.HTTP_201_CREATED)
async def order_numbers(
    body: NumberOrderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Order phone numbers from Bandwidth and associate them with the tenant."""
    # Resolve tenant's Bandwidth site
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    site_id = tenant.bandwidth_site_id
    if not site_id:
        raise HTTPException(
            status_code=400,
            detail="Tenant has no Bandwidth site configured. Complete onboarding first.",
        )

    try:
        bw_order = await bandwidth_client.order_numbers(
            numbers=body.numbers,
            site_id=site_id,
            sip_peer_id=tenant.bandwidth_location_id,
        )
    except BandwidthError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Bandwidth order failed: {e.message}",
        )

    order_id = bw_order.get("orderId", bw_order.get("id", ""))

    # Persist each number locally
    created: list[NumberResponse] = []
    for number_str in body.numbers:
        # Determine type from prefix
        num_type = "toll_free" if number_str.lstrip("+1").startswith(("800", "888", "877", "866", "855", "844", "833")) else "local"
        pn = PhoneNumber(
            tenant_id=user.tenant_id,
            number=number_str,
            number_type=num_type,
            bandwidth_order_id=order_id,
            status="pending",
            capabilities=["sms", "mms"],
            monthly_cost=Decimal("1.00"),
        )
        db.add(pn)
        await db.flush()
        created.append(NumberResponse.model_validate(pn))

    await db.commit()

    return {
        "ordered": len(created),
        "order_id": order_id,
        "numbers": created,
    }


# ---------------------------------------------------------------------------
# DELETE /:id -- Release a phone number
# ---------------------------------------------------------------------------

@router.delete("/{number_id}")
async def release_number(
    number_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Release a phone number back to Bandwidth and mark it inactive."""
    result = await db.execute(
        select(PhoneNumber).where(
            PhoneNumber.id == number_id,
            PhoneNumber.tenant_id == user.tenant_id,
        )
    )
    phone = result.scalar_one_or_none()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")

    if phone.status == "released":
        raise HTTPException(status_code=400, detail="Number already released")

    try:
        await bandwidth_client.release_number(phone.number)
    except BandwidthError as e:
        logger.error("Bandwidth release failed for %s: %s", phone.number, e)
        raise HTTPException(
            status_code=502,
            detail=f"Bandwidth release failed: {e.message}",
        )

    phone.status = "released"
    await db.commit()

    return {"message": f"Number {phone.number} released", "id": str(phone.id)}


# ---------------------------------------------------------------------------
# PUT /:id -- Update number configuration
# ---------------------------------------------------------------------------

@router.put("/{number_id}")
async def update_number_config(
    number_id: uuid.UUID,
    body: NumberConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update configuration for a phone number (campaign assignment, capabilities)."""
    result = await db.execute(
        select(PhoneNumber).where(
            PhoneNumber.id == number_id,
            PhoneNumber.tenant_id == user.tenant_id,
        )
    )
    phone = result.scalar_one_or_none()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")

    if body.campaign_id is not None:
        phone.campaign_id = body.campaign_id
    if body.capabilities is not None:
        phone.capabilities = body.capabilities

    await db.commit()
    return {"number": NumberResponse.model_validate(phone)}


# ---------------------------------------------------------------------------
# GET /:id/stats -- Messaging statistics for a number
# ---------------------------------------------------------------------------

@router.get("/{number_id}/stats")
async def get_number_stats(
    number_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get messaging statistics for a specific phone number."""
    result = await db.execute(
        select(PhoneNumber).where(
            PhoneNumber.id == number_id,
            PhoneNumber.tenant_id == user.tenant_id,
        )
    )
    phone = result.scalar_one_or_none()
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")

    # Count sent messages (as from_number)
    sent_result = await db.execute(
        select(func.count(CampaignMessage.id)).where(
            CampaignMessage.from_number == phone.number,
            CampaignMessage.tenant_id == user.tenant_id,
            CampaignMessage.status.in_(["sending", "delivered"]),
        )
    )
    sent = sent_result.scalar() or 0

    delivered_result = await db.execute(
        select(func.count(CampaignMessage.id)).where(
            CampaignMessage.from_number == phone.number,
            CampaignMessage.tenant_id == user.tenant_id,
            CampaignMessage.status == "delivered",
        )
    )
    delivered = delivered_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(CampaignMessage.id)).where(
            CampaignMessage.from_number == phone.number,
            CampaignMessage.tenant_id == user.tenant_id,
            CampaignMessage.status == "failed",
        )
    )
    failed = failed_result.scalar() or 0

    return {"sent": sent, "delivered": delivered, "failed": failed}
