"""Celery tasks for drip sequence processing."""
from app.celery_app import celery_app
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.drip_sequences.process_due_steps")
def process_due_steps():
    """Process all drip enrollments that have a step due now. Runs every minute via Beat."""
    from sqlalchemy import select, and_, update
    from app.config import get_settings
    from app.database import get_sync_session
    from app.models.drip_sequence import DripEnrollment, DripStep, DripSequence
    from app.models.contact import Contact
    from app.models.phone_number import PhoneNumber
    from app.models.tenant import Tenant
    from app.models.billing_event import BillingEvent
    from app.services.message_sender import render_template, calculate_segments, calculate_cost, SMS_SEGMENT_COST, MMS_MESSAGE_COST
    import httpx

    settings = get_settings()

    with get_sync_session() as db:
        now = datetime.now(timezone.utc)
        # Find all active enrollments with a due step
        enrollments = db.execute(
            select(DripEnrollment).where(
                DripEnrollment.status == "active",
                DripEnrollment.next_step_at <= now,
            )
        ).scalars().all()

        for enrollment in enrollments:
            try:
                # Get the current step
                step = db.execute(
                    select(DripStep).where(
                        DripStep.sequence_id == enrollment.sequence_id,
                        DripStep.step_order == enrollment.current_step,
                    )
                ).scalar_one_or_none()

                if not step:
                    enrollment.status = "completed"
                    enrollment.completed_at = now
                    db.commit()
                    continue

                # Get contact
                contact = db.get(Contact, enrollment.contact_id)
                if not contact or contact.status != "active":
                    enrollment.status = "canceled"
                    db.commit()
                    continue

                # Get a from number for this tenant
                from_number = db.execute(
                    select(PhoneNumber).where(
                        PhoneNumber.tenant_id == enrollment.tenant_id,
                        PhoneNumber.status == "active",
                    )
                ).scalars().first()

                if not from_number:
                    logger.warning(f"No active number for tenant {enrollment.tenant_id}")
                    continue

                # Render and send message
                text = render_template(step.message_template, contact)

                # Calculate cost
                segments = calculate_segments(text)
                is_mms = bool(step.media_urls)
                cost = calculate_cost(segments, is_mms)

                # Check tenant has credits (for free_trial tenants)
                tenant = db.get(Tenant, enrollment.tenant_id)
                if tenant and tenant.plan_tier == "free_trial" and tenant.credit_balance < cost:
                    logger.warning(f"Tenant {enrollment.tenant_id} has insufficient credits for drip step")
                    continue

                # Send via Bandwidth (sync)
                bw_url = f"https://messaging.bandwidth.com/api/v2/users/{settings.bandwidth_account_id}/messages"
                payload = {
                    "applicationId": settings.bandwidth_application_id,
                    "to": [contact.phone_number],
                    "from": from_number.number,
                    "text": text,
                }
                if step.media_urls:
                    payload["media"] = step.media_urls

                with httpx.Client(
                    auth=(settings.bandwidth_api_token, settings.bandwidth_api_secret),
                    timeout=30.0,
                ) as client:
                    resp = client.post(bw_url, json=payload)
                    resp.raise_for_status()

                # Deduct credits atomically after successful send
                db.execute(
                    update(Tenant)
                    .where(Tenant.id == enrollment.tenant_id, Tenant.credit_balance >= cost)
                    .values(credit_balance=Tenant.credit_balance - cost)
                )

                # Record billing event
                billing_event = BillingEvent(
                    tenant_id=enrollment.tenant_id,
                    event_type="mms_sent" if is_mms else "sms_sent",
                    quantity=segments,
                    unit_cost=MMS_MESSAGE_COST if is_mms else SMS_SEGMENT_COST,
                    total_cost=cost,
                )
                db.add(billing_event)

                logger.info(f"Drip step {step.step_order} sent to {contact.phone_number}")

                # Advance enrollment
                next_step = db.execute(
                    select(DripStep).where(
                        DripStep.sequence_id == enrollment.sequence_id,
                        DripStep.step_order == enrollment.current_step + 1,
                    )
                ).scalar_one_or_none()

                if next_step:
                    enrollment.current_step += 1
                    enrollment.next_step_at = now + timedelta(minutes=next_step.delay_minutes)
                else:
                    enrollment.status = "completed"
                    enrollment.completed_at = now

                db.commit()

            except Exception as e:
                logger.error(f"Error processing drip enrollment {enrollment.id}: {e}")
                db.rollback()


@celery_app.task(name="app.tasks.drip_sequences.enroll_contact")
def enroll_contact(sequence_id: str, contact_id: str, tenant_id: str):
    """Enroll a contact in a drip sequence."""
    from sqlalchemy import select
    from app.models.drip_sequence import DripEnrollment, DripStep
    from app.database import get_sync_session
    import uuid

    with get_sync_session() as db:
        first_step = db.execute(
            select(DripStep).where(DripStep.sequence_id == uuid.UUID(sequence_id)).order_by(DripStep.step_order)
        ).scalars().first()

        if not first_step:
            return

        now = datetime.now(timezone.utc)
        enrollment = DripEnrollment(
            sequence_id=uuid.UUID(sequence_id),
            contact_id=uuid.UUID(contact_id),
            tenant_id=uuid.UUID(tenant_id),
            current_step=first_step.step_order,
            status="active",
            enrolled_at=now,
            next_step_at=now + timedelta(minutes=first_step.delay_minutes),
        )
        db.add(enrollment)
        db.commit()
