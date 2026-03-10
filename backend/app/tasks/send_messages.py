"""Celery tasks for mass campaign sending and single-message retries."""

import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import get_settings
from app.database import get_sync_session
from app.models.campaign import Campaign
from app.models.campaign_message import CampaignMessage
from app.models.contact import Contact
from app.models.phone_number import PhoneNumber
from app.models.tenant import Tenant
from app.models.billing_event import BillingEvent
from app.services.message_sender import (
    calculate_segments,
    calculate_cost,
    render_template,
    SMS_SEGMENT_COST,
    MMS_MESSAGE_COST,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_sync_db() -> Session:
    """Return a sync session from the shared pool."""
    from app.database import _get_sync_engine
    _, factory = _get_sync_engine()
    return factory()


# ---------------------------------------------------------------------------
# Bandwidth send helper (sync wrapper)
# ---------------------------------------------------------------------------

def _send_via_bandwidth(
    to: str,
    from_number: str,
    text: str,
    media_urls: list[str] | None = None,
    tag: str | None = None,
) -> dict:
    """Synchronous helper to send a message via Bandwidth.

    Uses httpx in sync mode since Celery workers are not running an
    async event loop.
    """
    import httpx

    payload = {
        "applicationId": settings.bandwidth_application_id,
        "to": [to],
        "from": from_number,
        "text": text,
    }
    if media_urls:
        payload["media"] = media_urls
    if tag:
        payload["tag"] = tag

    url = (
        f"https://messaging.bandwidth.com/api/v2/users/"
        f"{settings.bandwidth_account_id}/messages"
    )
    try:
        resp = httpx.post(
            url,
            json=payload,
            auth=(settings.bandwidth_api_token, settings.bandwidth_api_secret),
            timeout=30.0,
        )
        if resp.status_code == 429:
            return {"error": "rate_limited", "status_code": 429}
        if resp.status_code >= 400:
            return {
                "error": resp.text,
                "status_code": resp.status_code,
            }
        data = resp.json()
        return {"id": data.get("id"), "status_code": resp.status_code}
    except httpx.TimeoutException:
        return {"error": "timeout", "status_code": 0}
    except Exception as exc:
        return {"error": str(exc), "status_code": 0}


# ---------------------------------------------------------------------------
# Rate-limit check (sync Redis)
# ---------------------------------------------------------------------------

def _check_rate_limit(tenant_id: str, mps_limit: int = 10) -> bool:
    """Simple sync Redis rate-limit check.  Returns True if allowed."""
    try:
        import redis

        r = redis.from_url(settings.redis_url, decode_responses=True)
        key = f"rate:tenant:{tenant_id}"
        now = time.time()
        window_start = now - 1

        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, 2)
        results = pipe.execute()

        current_count = results[1]
        if current_count >= mps_limit:
            r.zrem(key, str(now))
            return False
        return True
    except Exception:
        # If Redis is down, allow sending (fail-open for availability)
        return True


# ---------------------------------------------------------------------------
# Credit deduction helper
# ---------------------------------------------------------------------------

def _deduct_credits(db: Session, tenant_id, segments: int, is_mms: bool, cost, campaign_id=None):
    """Atomically deduct credits from a tenant and record a BillingEvent."""
    result = db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id, Tenant.credit_balance >= cost)
        .values(credit_balance=Tenant.credit_balance - cost)
    )
    # Even if rowcount==0 (insufficient balance), we still record the billing event
    # so usage is tracked. The tenant may be on a paid plan with metered billing.

    billing_event = BillingEvent(
        tenant_id=tenant_id,
        event_type="mms_sent" if is_mms else "sms_sent",
        quantity=segments,
        unit_cost=MMS_MESSAGE_COST if is_mms else SMS_SEGMENT_COST,
        total_cost=cost,
        campaign_id=campaign_id,
    )
    db.add(billing_event)


# ---------------------------------------------------------------------------
# Main campaign send task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_campaign_messages(self, campaign_id: str):
    """Process all queued CampaignMessage records for a campaign.

    For each message:
    1. Render the template with contact merge tags
    2. Check rate limits before sending
    3. Send via Bandwidth
    4. Update status and campaign counters
    5. Handle errors gracefully (mark failed, continue to next)
    """
    db = _get_sync_db()
    try:
        campaign_uuid = uuid.UUID(campaign_id)

        campaign = db.execute(
            select(Campaign).where(Campaign.id == campaign_uuid)
        ).scalar_one_or_none()

        if not campaign:
            logger.error("Campaign %s not found", campaign_id)
            return {"campaign_id": campaign_id, "status": "not_found"}

        if campaign.status not in ("sending",):
            logger.info(
                "Campaign %s is in '%s' status, skipping send",
                campaign_id,
                campaign.status,
            )
            return {"campaign_id": campaign_id, "status": campaign.status}

        tenant_id_str = str(campaign.tenant_id)

        # Determine MPS limit
        mps_limit = campaign.throttle_mps or 10

        # Load all queued messages
        queued_messages = (
            db.execute(
                select(CampaignMessage)
                .where(
                    and_(
                        CampaignMessage.campaign_id == campaign_uuid,
                        CampaignMessage.status == "queued",
                    )
                )
                .order_by(CampaignMessage.created_at)
            )
            .scalars()
            .all()
        )

        if not queued_messages:
            # All messages already processed
            campaign.status = "completed"
            db.commit()
            return {
                "campaign_id": campaign_id,
                "status": "completed",
                "sent": 0,
            }

        sent_count = 0
        failed_count = 0

        for msg in queued_messages:
            # Re-check campaign status (may have been paused/canceled)
            db.refresh(campaign)
            if campaign.status != "sending":
                logger.info(
                    "Campaign %s status changed to '%s', stopping",
                    campaign_id,
                    campaign.status,
                )
                break

            # Rate limit
            while not _check_rate_limit(tenant_id_str, mps_limit):
                time.sleep(0.1)

            # Load contact for template rendering
            contact = db.execute(
                select(Contact).where(Contact.id == msg.contact_id)
            ).scalar_one_or_none()

            if not contact:
                msg.status = "failed"
                msg.error_description = "Contact not found"
                msg.failed_at = datetime.now(timezone.utc)
                failed_count += 1
                db.commit()
                continue

            # Check opt-out status
            if contact.status in ("opted_out", "blocked"):
                msg.status = "canceled"
                msg.error_description = f"Contact {contact.status}"
                db.commit()
                continue

            # Render template
            rendered_body = render_template(campaign.message_template, contact)
            msg.message_body = rendered_body

            # Calculate segments and cost
            segments = calculate_segments(rendered_body)
            is_mms = bool(msg.media_urls)
            cost = calculate_cost(segments, is_mms)
            msg.segments = segments
            msg.cost = cost

            # Send
            result = _send_via_bandwidth(
                to=msg.to_number,
                from_number=msg.from_number,
                text=rendered_body,
                media_urls=msg.media_urls if msg.media_urls else None,
                tag=campaign_id,
            )

            if result.get("error") == "rate_limited":
                # Back off and retry this message
                time.sleep(1.0)
                retry_result = _send_via_bandwidth(
                    to=msg.to_number,
                    from_number=msg.from_number,
                    text=rendered_body,
                    media_urls=msg.media_urls if msg.media_urls else None,
                    tag=campaign_id,
                )
                if retry_result.get("error"):
                    msg.status = "failed"
                    msg.error_code = str(retry_result.get("status_code", ""))
                    msg.error_description = retry_result.get("error", "")
                    msg.failed_at = datetime.now(timezone.utc)
                    failed_count += 1
                else:
                    msg.bandwidth_message_id = retry_result.get("id")
                    msg.status = "sent"
                    msg.sent_at = datetime.now(timezone.utc)
                    sent_count += 1
                    # Deduct credits atomically and record billing event
                    _deduct_credits(db, campaign.tenant_id, segments, is_mms, cost, campaign_uuid)
            elif result.get("error"):
                msg.status = "failed"
                msg.error_code = str(result.get("status_code", ""))
                msg.error_description = result.get("error", "")
                msg.failed_at = datetime.now(timezone.utc)
                failed_count += 1
            else:
                msg.bandwidth_message_id = result.get("id")
                msg.status = "sent"
                msg.sent_at = datetime.now(timezone.utc)
                sent_count += 1
                # Deduct credits atomically and record billing event
                _deduct_credits(db, campaign.tenant_id, segments, is_mms, cost, campaign_uuid)

            # Update campaign counters periodically
            campaign.sent_count = (
                db.execute(
                    select(func.count(CampaignMessage.id)).where(
                        and_(
                            CampaignMessage.campaign_id == campaign_uuid,
                            CampaignMessage.status.in_(["sent", "sending", "delivered"]),
                        )
                    )
                ).scalar()
                or 0
            )
            campaign.failed_count = (
                db.execute(
                    select(func.count(CampaignMessage.id)).where(
                        and_(
                            CampaignMessage.campaign_id == campaign_uuid,
                            CampaignMessage.status == "failed",
                        )
                    )
                ).scalar()
                or 0
            )
            db.commit()

        # Final status update
        db.refresh(campaign)
        if campaign.status == "sending":
            # Check if all messages have been processed
            remaining = (
                db.execute(
                    select(func.count(CampaignMessage.id)).where(
                        and_(
                            CampaignMessage.campaign_id == campaign_uuid,
                            CampaignMessage.status == "queued",
                        )
                    )
                ).scalar()
                or 0
            )
            if remaining == 0:
                campaign.status = "completed"
                db.commit()

        return {
            "campaign_id": campaign_id,
            "status": campaign.status,
            "sent": sent_count,
            "failed": failed_count,
        }

    except Exception as exc:
        logger.exception("Error sending campaign %s: %s", campaign_id, exc)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # Mark campaign as failed if all retries exhausted
            try:
                campaign = db.execute(
                    select(Campaign).where(Campaign.id == uuid.UUID(campaign_id))
                ).scalar_one_or_none()
                if campaign:
                    campaign.status = "failed"
                    db.commit()
            except Exception:
                pass
            return {"campaign_id": campaign_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Single message send task (for retries / individual sends)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_single_task(self, message_data: dict):
    """Send a single message. Used for retrying failed messages or
    individual ad-hoc sends from the campaign.

    ``message_data`` keys:
    - campaign_message_id (str)
    - to_number (str)
    - from_number (str)
    - body (str)
    - media_urls (list[str] | None)
    - campaign_id (str)
    - tenant_id (str)
    """
    db = _get_sync_db()
    try:
        msg_id = uuid.UUID(message_data["campaign_message_id"])
        msg = db.execute(
            select(CampaignMessage).where(CampaignMessage.id == msg_id)
        ).scalar_one_or_none()

        if not msg:
            return {"status": "not_found", "message_id": str(msg_id)}

        # Rate limit
        tenant_id_str = message_data.get("tenant_id", "")
        while not _check_rate_limit(tenant_id_str):
            time.sleep(0.1)

        result = _send_via_bandwidth(
            to=message_data["to_number"],
            from_number=message_data["from_number"],
            text=message_data["body"],
            media_urls=message_data.get("media_urls"),
            tag=message_data.get("campaign_id"),
        )

        if result.get("error"):
            msg.status = "failed"
            msg.error_code = str(result.get("status_code", ""))
            msg.error_description = result.get("error", "")
            msg.failed_at = datetime.now(timezone.utc)
            db.commit()
            raise Exception(f"Send failed: {result.get('error')}")

        msg.bandwidth_message_id = result.get("id")
        msg.status = "sent"
        msg.sent_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "sent",
            "message_id": str(msg_id),
            "bandwidth_message_id": result.get("id"),
        }

    except Exception as exc:
        logger.exception("Error sending message: %s", exc)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


# Need func for the count queries above
from sqlalchemy import func
