"""Compliance router -- 10DLC brand/campaign registration, opt-out management, TCPA, quiet hours."""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.brand import Brand10DLC
from app.models.campaign_10dlc import Campaign10DLC
from app.models.phone_number import PhoneNumber
from app.models.contact import Contact
from app.models.opt_out_log import OptOutLog
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.models.dlc_application import DLCApplication
from app.schemas.compliance import (
    BrandCreate,
    BrandResponse,
    CampaignRegistrationCreate,
    CampaignRegistrationResponse,
    DLCApplicationResponse,
)
from app.services.bandwidth import bandwidth_client, BandwidthError

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic helpers
# ---------------------------------------------------------------------------

class ManualOptOutRequest(BaseModel):
    phone_number: str
    reason: str | None = None


class QuietHoursConfig(BaseModel):
    enabled: bool = True
    start: str = "21:00"
    end: str = "08:00"
    timezone: str = "US/Eastern"


class ConsentRecordCreate(BaseModel):
    phone_number: str
    consent_type: str = "express_written"
    source: str = "web_form"
    ip_address: str | None = None


class ComplianceDashboard(BaseModel):
    total_brands: int
    total_campaigns: int
    active_numbers: int
    opt_out_count_30d: int
    pending_brands: int
    pending_campaigns: int


# ==================== 10DLC Brands ====================

@router.post("/brands/apply", status_code=status.HTTP_201_CREATED)
async def apply_brand_registration(
    body: BrandCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a brand registration application for admin review.

    Creates the Brand10DLC record in 'draft' status and a DLCApplication
    linking to it. The application goes into the admin review queue.
    """
    tenant_id = user.tenant_id

    # Create the brand record (not yet submitted to Bandwidth)
    brand = Brand10DLC(
        tenant_id=tenant_id,
        entity_type=body.entity_type,
        legal_name=body.legal_name,
        dba_name=body.dba_name or body.legal_name,
        ein=body.ein,
        phone=body.phone,
        email=body.email,
        street=body.street,
        city=body.city,
        state=body.state,
        zip_code=body.zip_code,
        country=body.country,
        website=body.website,
        vertical=body.vertical,
        brand_relationship=body.brand_relationship,
        is_main=body.is_main,
        stock_symbol=body.stock_symbol,
        stock_exchange=body.stock_exchange,
        business_contact_email=body.business_contact_email,
        alt_business_id=body.alt_business_id,
        alt_business_id_type=body.alt_business_id_type,
        vetting_status="draft",
        registration_status="draft",
    )
    db.add(brand)
    await db.flush()

    # Create application for review queue
    application = DLCApplication(
        tenant_id=tenant_id,
        application_type="brand",
        brand_id=brand.id,
        form_data=body.model_dump(),
        status="pending_review",
        submitted_by=user.id,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(application)

    # Audit
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user.id,
        action="brand_application_submitted",
        resource_type="dlc_application",
        resource_id=str(brand.id),
        details={"legal_name": body.legal_name, "entity_type": body.entity_type},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(application)

    # Auto-trigger AI review now that the application is persisted
    try:
        from app.tasks.ai_dlc_review import run_ai_dlc_review
        run_ai_dlc_review.delay(str(application.id))
        logger.info("AI review task queued for brand application %s", application.id)
    except Exception:
        logger.exception("Failed to queue AI review task for brand application %s", application.id)

    return DLCApplicationResponse.model_validate(application)


@router.get("/brands")
async def list_brands(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all 10DLC brands for the tenant."""
    count_result = await db.execute(
        select(func.count(Brand10DLC.id)).where(
            Brand10DLC.tenant_id == user.tenant_id
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Brand10DLC)
        .where(Brand10DLC.tenant_id == user.tenant_id)
        .order_by(Brand10DLC.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    brands = result.scalars().all()

    return {
        "brands": [BrandResponse.model_validate(b) for b in brands],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/brands/{brand_id}")
async def get_brand(
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get brand registration details, refreshing status from Bandwidth if available."""
    result = await db.execute(
        select(Brand10DLC).where(
            Brand10DLC.id == brand_id,
            Brand10DLC.tenant_id == user.tenant_id,
        )
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Try to refresh status from Bandwidth
    if brand.bandwidth_brand_id and brand.registration_status == "pending":
        try:
            bw_brand = await bandwidth_client.get_brand(brand.bandwidth_brand_id)
            bw_status = bw_brand.get("identityStatus", bw_brand.get("status", ""))
            if bw_status:
                brand.registration_status = bw_status.lower()
            trust_score = bw_brand.get("trustScore")
            if trust_score is not None:
                brand.trust_score = int(trust_score)
            await db.commit()
        except BandwidthError:
            pass  # Use cached data

    return BrandResponse.model_validate(brand)


# ==================== 10DLC Campaigns ====================

@router.post("/campaigns/apply", status_code=status.HTTP_201_CREATED)
async def apply_campaign_registration(
    body: CampaignRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a campaign registration application for admin review."""
    tenant_id = user.tenant_id

    # Verify brand exists and belongs to tenant
    brand_result = await db.execute(
        select(Brand10DLC).where(
            Brand10DLC.id == body.brand_id,
            Brand10DLC.tenant_id == tenant_id,
        )
    )
    brand = brand_result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Create campaign record (not yet submitted to Bandwidth)
    campaign = Campaign10DLC(
        tenant_id=tenant_id,
        brand_id=brand.id,
        use_case=body.use_case,
        description=body.description,
        message_flow=body.message_flow,
        sample_messages=body.sample_messages,
        help_message=body.help_message,
        help_keywords=body.help_keywords,
        optin_message=body.optin_message,
        optin_keywords=body.optin_keywords,
        optout_message=body.optout_message,
        optout_keywords=body.optout_keywords,
        subscriber_optin=body.subscriber_optin,
        subscriber_optout=body.subscriber_optout,
        subscriber_help=body.subscriber_help,
        number_pool=body.number_pool,
        direct_lending=body.direct_lending,
        embedded_links=body.embedded_links,
        embedded_phone=body.embedded_phone,
        affiliate_marketing=body.affiliate_marketing,
        age_gated=body.age_gated,
        auto_renewal=body.auto_renewal,
        sub_usecases=body.sub_usecases,
        privacy_policy_link=body.privacy_policy_link,
        terms_and_conditions_link=body.terms_and_conditions_link,
        status="draft",
    )
    db.add(campaign)
    await db.flush()

    application = DLCApplication(
        tenant_id=tenant_id,
        application_type="campaign",
        brand_id=brand.id,
        campaign_id=campaign.id,
        form_data=body.model_dump(mode="json"),
        status="pending_review",
        submitted_by=user.id,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(application)

    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user.id,
        action="campaign_application_submitted",
        resource_type="dlc_application",
        resource_id=str(campaign.id),
        details={"use_case": body.use_case, "brand_id": str(brand.id)},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(application)

    # Auto-trigger AI review now that the application is persisted
    try:
        from app.tasks.ai_dlc_review import run_ai_dlc_review
        run_ai_dlc_review.delay(str(application.id))
        logger.info("AI review task queued for campaign application %s", application.id)
    except Exception:
        logger.exception("Failed to queue AI review task for campaign application %s", application.id)

    return DLCApplicationResponse.model_validate(application)


@router.get("/campaigns")
async def list_campaigns(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    brand_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all 10DLC campaigns for the tenant."""
    query = select(Campaign10DLC).where(
        Campaign10DLC.tenant_id == user.tenant_id
    )
    count_query = select(func.count(Campaign10DLC.id)).where(
        Campaign10DLC.tenant_id == user.tenant_id
    )

    if brand_id:
        query = query.where(Campaign10DLC.brand_id == brand_id)
        count_query = count_query.where(Campaign10DLC.brand_id == brand_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(Campaign10DLC.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    campaigns = result.scalars().all()

    return {
        "campaigns": [
            CampaignRegistrationResponse.model_validate(c) for c in campaigns
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get 10DLC campaign details, refreshing status from Bandwidth."""
    result = await db.execute(
        select(Campaign10DLC).where(
            Campaign10DLC.id == campaign_id,
            Campaign10DLC.tenant_id == user.tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Refresh from Bandwidth if still pending
    if campaign.bandwidth_campaign_id and campaign.status == "pending":
        try:
            bw_campaign = await bandwidth_client.get_campaign(
                campaign.bandwidth_campaign_id
            )
            bw_status = bw_campaign.get("campaignStatus", bw_campaign.get("status", ""))
            if bw_status:
                campaign.status = bw_status.lower()
            mps = bw_campaign.get("messagingVolume", {}).get("mps")
            if mps:
                campaign.mps_limit = int(mps)
            daily = bw_campaign.get("messagingVolume", {}).get("dailyLimit")
            if daily:
                campaign.daily_limit = int(daily)
            await db.commit()
        except BandwidthError:
            pass

    return CampaignRegistrationResponse.model_validate(campaign)


# ==================== DLC Applications ====================

@router.get("/applications")
async def list_my_applications(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    app_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the current tenant's DLC applications."""
    tenant_id = user.tenant_id
    base = [DLCApplication.tenant_id == tenant_id]
    if status_filter:
        base.append(DLCApplication.status == status_filter)
    if app_type:
        base.append(DLCApplication.application_type == app_type)

    count_result = await db.execute(
        select(func.count(DLCApplication.id)).where(*base)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(DLCApplication)
        .where(*base)
        .order_by(DLCApplication.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    apps = result.scalars().all()

    return {
        "applications": [DLCApplicationResponse.model_validate(a) for a in apps],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/applications/{application_id}")
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detail of a specific DLC application."""
    result = await db.execute(
        select(DLCApplication).where(
            DLCApplication.id == application_id,
            DLCApplication.tenant_id == user.tenant_id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return DLCApplicationResponse.model_validate(app)


@router.get("/applications/{application_id}/review-status")
async def get_application_review_status(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get AI review status for a DLC application (tenant-scoped).

    Returns a limited view of the AI review: score, verdict, and summary.
    Detailed issues and enhanced fields are admin-only.
    """
    from app.models.ai_review_result import AIReviewResult

    # Verify the application belongs to this tenant
    app_result = await db.execute(
        select(DLCApplication.id).where(
            DLCApplication.id == application_id,
            DLCApplication.tenant_id == user.tenant_id,
        )
    )
    if not app_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Application not found")

    # Get the latest AI review result
    review_result = await db.execute(
        select(AIReviewResult)
        .where(AIReviewResult.dlc_application_id == application_id)
        .order_by(AIReviewResult.created_at.desc())
        .limit(1)
    )
    review = review_result.scalar_one_or_none()

    if not review:
        return {"status": "pending"}

    return {
        "status": "completed",
        "score": review.score,
        "verdict": review.verdict,
        "summary": review.summary,
        "reviewed_at": review.created_at.isoformat() if review.created_at else None,
    }


# ==================== Compliance Dashboard ====================

@router.get("/dashboard")
async def compliance_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compliance overview dashboard with key metrics."""
    tenant_id = user.tenant_id

    # Total brands
    brands_count = await db.execute(
        select(func.count(Brand10DLC.id)).where(
            Brand10DLC.tenant_id == tenant_id
        )
    )
    total_brands = brands_count.scalar() or 0

    pending_brands_count = await db.execute(
        select(func.count(Brand10DLC.id)).where(
            Brand10DLC.tenant_id == tenant_id,
            Brand10DLC.registration_status == "pending",
        )
    )
    pending_brands = pending_brands_count.scalar() or 0

    # Total campaigns
    campaigns_count = await db.execute(
        select(func.count(Campaign10DLC.id)).where(
            Campaign10DLC.tenant_id == tenant_id
        )
    )
    total_campaigns = campaigns_count.scalar() or 0

    pending_campaigns_count = await db.execute(
        select(func.count(Campaign10DLC.id)).where(
            Campaign10DLC.tenant_id == tenant_id,
            Campaign10DLC.status == "pending",
        )
    )
    pending_campaigns = pending_campaigns_count.scalar() or 0

    # Active numbers
    numbers_count = await db.execute(
        select(func.count(PhoneNumber.id)).where(
            PhoneNumber.tenant_id == tenant_id,
            PhoneNumber.status == "active",
        )
    )
    active_numbers = numbers_count.scalar() or 0

    # Opt-outs in last 30 days
    from datetime import timedelta

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    optout_count = await db.execute(
        select(func.count(OptOutLog.id)).where(
            OptOutLog.tenant_id == tenant_id,
            OptOutLog.created_at >= thirty_days_ago,
        )
    )
    opt_out_count_30d = optout_count.scalar() or 0

    return ComplianceDashboard(
        total_brands=total_brands,
        total_campaigns=total_campaigns,
        active_numbers=active_numbers,
        opt_out_count_30d=opt_out_count_30d,
        pending_brands=pending_brands,
        pending_campaigns=pending_campaigns,
    )


# ==================== Opt-Out Management ====================

@router.get("/opt-outs")
async def list_opt_outs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all opted-out contacts for the tenant."""
    tenant_id = user.tenant_id

    count_result = await db.execute(
        select(func.count(Contact.id)).where(
            Contact.tenant_id == tenant_id,
            Contact.status == "unsubscribed",
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Contact)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.status == "unsubscribed",
        )
        .order_by(Contact.opted_out_at.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    contacts = result.scalars().all()

    return {
        "opt_outs": [
            {
                "id": str(c.id),
                "phone_number": c.phone_number,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "opted_out_at": c.opted_out_at.isoformat() if c.opted_out_at else None,
            }
            for c in contacts
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/opt-outs")
async def add_opt_out(
    body: ManualOptOutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually add a phone number to the opt-out list."""
    tenant_id = user.tenant_id

    result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.phone_number == body.phone_number,
        )
    )
    contact = result.scalar_one_or_none()

    if contact:
        contact.status = "unsubscribed"
        contact.opted_out_at = datetime.now(timezone.utc)
    else:
        contact = Contact(
            tenant_id=tenant_id,
            phone_number=body.phone_number,
            status="unsubscribed",
            opted_out_at=datetime.now(timezone.utc),
            opt_in_method="manual_opt_out",
        )
        db.add(contact)
        await db.flush()

    opt_out_log = OptOutLog(
        tenant_id=tenant_id,
        contact_id=contact.id,
        phone_number=body.phone_number,
        keyword_used="manual",
    )
    db.add(opt_out_log)

    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user.id,
        action="manual_opt_out",
        resource_type="contact",
        resource_id=str(contact.id),
        details={"phone_number": body.phone_number, "reason": body.reason},
    )
    db.add(audit)

    await db.commit()

    return {"message": f"Number {body.phone_number} added to opt-out list"}


@router.delete("/opt-outs")
async def remove_opt_out(
    phone: str = Query(..., description="E.164 phone number to remove from opt-out list"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove a phone number from the opt-out list (re-subscribe).

    Uses query parameter ``phone`` instead of a path parameter to avoid
    issues with E.164 numbers (leading ``+``) in URL paths.

    This action is audit-logged because re-subscribing someone requires
    documented consent.
    """
    tenant_id = user.tenant_id

    result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.phone_number == phone,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    if contact.status != "unsubscribed":
        raise HTTPException(
            status_code=400, detail="Contact is not opted out"
        )

    contact.status = "active"
    contact.opted_in_at = datetime.now(timezone.utc)
    contact.opted_out_at = None
    contact.opt_in_method = "manual_resubscribe"

    # Audit trail for TCPA compliance
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user.id,
        action="opt_out_removed",
        resource_type="contact",
        resource_id=str(contact.id),
        details={"phone_number": phone},
    )
    db.add(audit)

    await db.commit()

    return {"message": f"Number {phone} removed from opt-out list"}


# ==================== TCPA Consent Records ====================

@router.get("/tcpa-consent")
async def list_consent_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List TCPA consent records (contacts who have opted in)."""
    tenant_id = user.tenant_id

    count_result = await db.execute(
        select(func.count(Contact.id)).where(
            Contact.tenant_id == tenant_id,
            Contact.opted_in_at.isnot(None),
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Contact)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.opted_in_at.isnot(None),
        )
        .order_by(Contact.opted_in_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    contacts = result.scalars().all()

    return {
        "records": [
            {
                "id": str(c.id),
                "phone_number": c.phone_number,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "opt_in_method": c.opt_in_method,
                "opted_in_at": c.opted_in_at.isoformat() if c.opted_in_at else None,
                "status": c.status,
            }
            for c in contacts
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/tcpa-consent")
async def record_consent(
    body: ConsentRecordCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record explicit TCPA consent for a phone number."""
    tenant_id = user.tenant_id

    result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.phone_number == body.phone_number,
        )
    )
    contact = result.scalar_one_or_none()

    if contact:
        contact.opted_in_at = datetime.now(timezone.utc)
        contact.opt_in_method = f"{body.consent_type}:{body.source}"
        if contact.status == "unsubscribed":
            contact.status = "active"
            contact.opted_out_at = None
    else:
        contact = Contact(
            tenant_id=tenant_id,
            phone_number=body.phone_number,
            status="active",
            opted_in_at=datetime.now(timezone.utc),
            opt_in_method=f"{body.consent_type}:{body.source}",
        )
        db.add(contact)
        await db.flush()

    # Audit
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user.id,
        action="consent_recorded",
        resource_type="contact",
        resource_id=str(contact.id),
        details={
            "phone_number": body.phone_number,
            "consent_type": body.consent_type,
            "source": body.source,
            "ip_address": body.ip_address,
        },
    )
    db.add(audit)
    await db.commit()

    return {"message": "Consent recorded"}


# ==================== Quiet Hours ====================

@router.get("/quiet-hours")
async def get_quiet_hours(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get quiet hours configuration for the tenant."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    qh = tenant.settings.get("quiet_hours", {})
    return {
        "enabled": qh.get("enabled", True),
        "start": qh.get("start", "21:00"),
        "end": qh.get("end", "08:00"),
        "timezone": qh.get("timezone", "US/Eastern"),
    }


@router.put("/quiet-hours")
async def update_quiet_hours(
    body: QuietHoursConfig,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update quiet hours configuration.

    Messages will not be sent during the quiet window.
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    settings_dict = dict(tenant.settings) if tenant.settings else {}
    settings_dict["quiet_hours"] = {
        "enabled": body.enabled,
        "start": body.start,
        "end": body.end,
        "timezone": body.timezone,
    }
    tenant.settings = settings_dict

    # Audit
    audit = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="quiet_hours_updated",
        resource_type="tenant",
        resource_id=str(user.tenant_id),
        details=settings_dict["quiet_hours"],
    )
    db.add(audit)

    await db.commit()

    return {"message": "Quiet hours updated"}


# ==================== Audit Log ====================

@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: str | None = None,
    resource_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get compliance audit log entries."""
    tenant_id = user.tenant_id

    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    count_query = select(func.count(AuditLog.id)).where(
        AuditLog.tenant_id == tenant_id
    )

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()

    return {
        "entries": [
            {
                "id": str(e.id),
                "user_id": str(e.user_id) if e.user_id else None,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "details": e.details,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
