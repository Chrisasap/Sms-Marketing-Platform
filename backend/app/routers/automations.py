"""Auto-reply and drip sequence automation router.

Manages keyword/schedule-based auto-replies and multi-step drip campaigns
with enrollment tracking -- all tenant-scoped.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.contact import Contact
from app.models.auto_reply import AutoReply
from app.models.drip_sequence import DripSequence, DripStep, DripEnrollment
from app.schemas.automation import (
    AutoReplyCreate,
    AutoReplyUpdate,
    AutoReplyResponse,
    DripSequenceCreate,
    DripStepCreate,
    DripSequenceResponse,
    DripStepResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ===========================================================================
# Auto-Replies
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /auto-replies -- List auto-replies
# ---------------------------------------------------------------------------

@router.get("/auto-replies")
async def list_auto_replies(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all auto-reply rules for the tenant."""
    tenant_id = user.tenant_id

    base_filter = [AutoReply.tenant_id == tenant_id]
    if is_active is not None:
        base_filter.append(AutoReply.is_active == is_active)

    count_q = select(func.count(AutoReply.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    data_q = (
        select(AutoReply)
        .where(*base_filter)
        .order_by(AutoReply.priority.desc(), AutoReply.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    auto_replies = result.scalars().all()

    return {
        "auto_replies": [
            {
                "id": str(ar.id),
                "phone_number_id": str(ar.phone_number_id) if ar.phone_number_id else None,
                "trigger_type": ar.trigger_type,
                "trigger_value": ar.trigger_value,
                "response_body": ar.response_body,
                "media_urls": ar.media_urls or [],
                "is_active": ar.is_active,
                "priority": ar.priority,
                "created_at": ar.created_at.isoformat(),
            }
            for ar in auto_replies
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST /auto-replies -- Create auto-reply
# ---------------------------------------------------------------------------

@router.post("/auto-replies", status_code=status.HTTP_201_CREATED)
async def create_auto_reply(
    body: AutoReplyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Create a new auto-reply rule.

    trigger_type options: ``keyword``, ``after_hours``, ``opt_in``,
    ``first_message``, ``all``.
    """
    valid_triggers = {"keyword", "after_hours", "opt_in", "first_message", "all"}
    if body.trigger_type not in valid_triggers:
        raise HTTPException(
            status_code=400,
            detail=f"trigger_type must be one of: {', '.join(sorted(valid_triggers))}",
        )

    auto_reply = AutoReply(
        tenant_id=user.tenant_id,
        phone_number_id=body.phone_number_id,
        trigger_type=body.trigger_type,
        trigger_value=body.trigger_value,
        response_body=body.response_body,
        media_urls=body.media_urls or [],
        is_active=body.is_active,
        priority=body.priority,
    )
    db.add(auto_reply)
    await db.commit()
    await db.refresh(auto_reply)

    return {
        "auto_reply": {
            "id": str(auto_reply.id),
            "phone_number_id": (
                str(auto_reply.phone_number_id) if auto_reply.phone_number_id else None
            ),
            "trigger_type": auto_reply.trigger_type,
            "trigger_value": auto_reply.trigger_value,
            "response_body": auto_reply.response_body,
            "media_urls": auto_reply.media_urls or [],
            "is_active": auto_reply.is_active,
            "priority": auto_reply.priority,
            "created_at": auto_reply.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# PUT /auto-replies/{id} -- Update auto-reply
# ---------------------------------------------------------------------------

@router.put("/auto-replies/{auto_reply_id}")
async def update_auto_reply(
    auto_reply_id: uuid.UUID,
    body: AutoReplyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Update an existing auto-reply rule."""
    result = await db.execute(
        select(AutoReply).where(
            AutoReply.id == auto_reply_id,
            AutoReply.tenant_id == user.tenant_id,
        )
    )
    auto_reply = result.scalar_one_or_none()
    if not auto_reply:
        raise HTTPException(status_code=404, detail="Auto-reply not found")

    if body.trigger_type is not None:
        valid_triggers = {"keyword", "after_hours", "opt_in", "first_message", "all"}
        if body.trigger_type not in valid_triggers:
            raise HTTPException(
                status_code=400,
                detail=f"trigger_type must be one of: {', '.join(sorted(valid_triggers))}",
            )
        auto_reply.trigger_type = body.trigger_type
    if body.trigger_value is not None:
        auto_reply.trigger_value = body.trigger_value
    if body.response_body is not None:
        auto_reply.response_body = body.response_body
    if body.media_urls is not None:
        auto_reply.media_urls = body.media_urls
    if body.is_active is not None:
        auto_reply.is_active = body.is_active
    if body.priority is not None:
        auto_reply.priority = body.priority

    await db.commit()
    await db.refresh(auto_reply)

    return {
        "auto_reply": {
            "id": str(auto_reply.id),
            "phone_number_id": (
                str(auto_reply.phone_number_id) if auto_reply.phone_number_id else None
            ),
            "trigger_type": auto_reply.trigger_type,
            "trigger_value": auto_reply.trigger_value,
            "response_body": auto_reply.response_body,
            "media_urls": auto_reply.media_urls or [],
            "is_active": auto_reply.is_active,
            "priority": auto_reply.priority,
            "created_at": auto_reply.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# DELETE /auto-replies/{id} -- Delete auto-reply
# ---------------------------------------------------------------------------

@router.delete("/auto-replies/{auto_reply_id}")
async def delete_auto_reply(
    auto_reply_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Delete an auto-reply rule."""
    result = await db.execute(
        select(AutoReply).where(
            AutoReply.id == auto_reply_id,
            AutoReply.tenant_id == user.tenant_id,
        )
    )
    auto_reply = result.scalar_one_or_none()
    if not auto_reply:
        raise HTTPException(status_code=404, detail="Auto-reply not found")

    await db.delete(auto_reply)
    await db.commit()

    return {"message": "Auto-reply deleted", "id": str(auto_reply_id)}


# ===========================================================================
# Drip Sequences
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /drip-sequences -- List drip sequences
# ---------------------------------------------------------------------------

@router.get("/drip-sequences")
async def list_drip_sequences(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all drip sequences for the tenant."""
    tenant_id = user.tenant_id

    base_filter = [DripSequence.tenant_id == tenant_id]
    if is_active is not None:
        base_filter.append(DripSequence.is_active == is_active)

    count_q = select(func.count(DripSequence.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    data_q = (
        select(DripSequence)
        .where(*base_filter)
        .order_by(DripSequence.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    sequences = result.scalars().all()

    items = []
    for seq in sequences:
        # Get enrollment counts
        enrollment_count_q = select(func.count(DripEnrollment.id)).where(
            DripEnrollment.sequence_id == seq.id
        )
        enrollment_result = await db.execute(enrollment_count_q)
        enrollment_count = enrollment_result.scalar() or 0

        active_enrollment_q = select(func.count(DripEnrollment.id)).where(
            DripEnrollment.sequence_id == seq.id,
            DripEnrollment.status == "active",
        )
        active_result = await db.execute(active_enrollment_q)
        active_count = active_result.scalar() or 0

        items.append({
            "id": str(seq.id),
            "name": seq.name,
            "trigger_event": seq.trigger_event,
            "is_active": seq.is_active,
            "step_count": len(seq.steps) if seq.steps else 0,
            "total_enrollments": enrollment_count,
            "active_enrollments": active_count,
            "created_at": seq.created_at.isoformat(),
        })

    return {
        "drip_sequences": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST /drip-sequences -- Create drip sequence with steps
# ---------------------------------------------------------------------------

@router.post("/drip-sequences", status_code=status.HTTP_201_CREATED)
async def create_drip_sequence(
    body: DripSequenceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Create a new drip sequence with optional steps.

    Each step defines a delay (in minutes) and a message template with
    optional merge tags.
    """
    sequence = DripSequence(
        tenant_id=user.tenant_id,
        name=body.name,
        trigger_event=body.trigger_event,
        is_active=False,  # Start as inactive
    )
    db.add(sequence)
    await db.flush()

    # Create steps
    for step_data in body.steps:
        step = DripStep(
            sequence_id=sequence.id,
            step_order=step_data.step_order,
            delay_minutes=step_data.delay_minutes,
            message_template=step_data.message_template,
            media_urls=step_data.media_urls or [],
            condition=step_data.condition,
        )
        db.add(step)

    await db.commit()
    await db.refresh(sequence)

    return {
        "drip_sequence": {
            "id": str(sequence.id),
            "name": sequence.name,
            "trigger_event": sequence.trigger_event,
            "is_active": sequence.is_active,
            "steps": [
                {
                    "id": str(s.id),
                    "step_order": s.step_order,
                    "delay_minutes": s.delay_minutes,
                    "message_template": s.message_template,
                    "media_urls": s.media_urls or [],
                    "condition": s.condition,
                }
                for s in sorted(sequence.steps, key=lambda x: x.step_order)
            ],
            "created_at": sequence.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# GET /drip-sequences/{id} -- Get sequence with steps
# ---------------------------------------------------------------------------

@router.get("/drip-sequences/{sequence_id}")
async def get_drip_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a drip sequence with all its steps."""
    result = await db.execute(
        select(DripSequence).where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == user.tenant_id,
        )
    )
    sequence = result.scalar_one_or_none()
    if not sequence:
        raise HTTPException(status_code=404, detail="Drip sequence not found")

    # Enrollment stats
    enrollment_q = select(
        DripEnrollment.status,
        func.count(DripEnrollment.id),
    ).where(
        DripEnrollment.sequence_id == sequence.id
    ).group_by(DripEnrollment.status)
    enrollment_result = await db.execute(enrollment_q)
    enrollment_stats = {row[0]: row[1] for row in enrollment_result.all()}

    return {
        "drip_sequence": {
            "id": str(sequence.id),
            "name": sequence.name,
            "trigger_event": sequence.trigger_event,
            "is_active": sequence.is_active,
            "steps": [
                {
                    "id": str(s.id),
                    "step_order": s.step_order,
                    "delay_minutes": s.delay_minutes,
                    "message_template": s.message_template,
                    "media_urls": s.media_urls or [],
                    "condition": s.condition,
                }
                for s in sorted(sequence.steps, key=lambda x: x.step_order)
            ],
            "enrollment_stats": {
                "active": enrollment_stats.get("active", 0),
                "completed": enrollment_stats.get("completed", 0),
                "paused": enrollment_stats.get("paused", 0),
                "canceled": enrollment_stats.get("canceled", 0),
            },
            "created_at": sequence.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# PUT /drip-sequences/{id} -- Update sequence
# ---------------------------------------------------------------------------

@router.put("/drip-sequences/{sequence_id}")
async def update_drip_sequence(
    sequence_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Update a drip sequence name, trigger, or replace its steps.

    If ``steps`` is provided in the body, all existing steps are replaced.
    """
    result = await db.execute(
        select(DripSequence).where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == user.tenant_id,
        )
    )
    sequence = result.scalar_one_or_none()
    if not sequence:
        raise HTTPException(status_code=404, detail="Drip sequence not found")

    if "name" in body:
        sequence.name = body["name"]
    if "trigger_event" in body:
        sequence.trigger_event = body["trigger_event"]

    # Replace steps if provided
    if "steps" in body:
        # Delete existing steps
        await db.execute(
            delete(DripStep).where(DripStep.sequence_id == sequence.id)
        )
        # Create new steps
        for step_data in body["steps"]:
            step = DripStep(
                sequence_id=sequence.id,
                step_order=step_data["step_order"],
                delay_minutes=step_data["delay_minutes"],
                message_template=step_data["message_template"],
                media_urls=step_data.get("media_urls", []),
                condition=step_data.get("condition"),
            )
            db.add(step)

    await db.commit()
    await db.refresh(sequence)

    return {
        "drip_sequence": {
            "id": str(sequence.id),
            "name": sequence.name,
            "trigger_event": sequence.trigger_event,
            "is_active": sequence.is_active,
            "steps": [
                {
                    "id": str(s.id),
                    "step_order": s.step_order,
                    "delay_minutes": s.delay_minutes,
                    "message_template": s.message_template,
                    "media_urls": s.media_urls or [],
                    "condition": s.condition,
                }
                for s in sorted(sequence.steps, key=lambda x: x.step_order)
            ],
            "created_at": sequence.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# DELETE /drip-sequences/{id} -- Delete sequence and steps
# ---------------------------------------------------------------------------

@router.delete("/drip-sequences/{sequence_id}")
async def delete_drip_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Delete a drip sequence and all its steps.

    Active enrollments will be canceled.
    """
    result = await db.execute(
        select(DripSequence).where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == user.tenant_id,
        )
    )
    sequence = result.scalar_one_or_none()
    if not sequence:
        raise HTTPException(status_code=404, detail="Drip sequence not found")

    # Cancel active enrollments
    active_enrollments_q = select(DripEnrollment).where(
        DripEnrollment.sequence_id == sequence.id,
        DripEnrollment.status == "active",
    )
    active_result = await db.execute(active_enrollments_q)
    for enrollment in active_result.scalars().all():
        enrollment.status = "canceled"

    # Delete steps
    await db.execute(
        delete(DripStep).where(DripStep.sequence_id == sequence.id)
    )

    # Delete enrollments
    await db.execute(
        delete(DripEnrollment).where(DripEnrollment.sequence_id == sequence.id)
    )

    await db.delete(sequence)
    await db.commit()

    return {"message": "Drip sequence deleted", "id": str(sequence_id)}


# ---------------------------------------------------------------------------
# POST /drip-sequences/{id}/activate -- Activate/deactivate
# ---------------------------------------------------------------------------

@router.post("/drip-sequences/{sequence_id}/activate")
async def toggle_drip_sequence(
    sequence_id: uuid.UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Activate or deactivate a drip sequence.

    Body: ``{"active": true}`` or ``{"active": false}``
    If no body, toggles the current state.
    """
    result = await db.execute(
        select(DripSequence).where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == user.tenant_id,
        )
    )
    sequence = result.scalar_one_or_none()
    if not sequence:
        raise HTTPException(status_code=404, detail="Drip sequence not found")

    body = body or {}
    if "active" in body:
        sequence.is_active = bool(body["active"])
    else:
        sequence.is_active = not sequence.is_active

    # Require at least one step to activate
    if sequence.is_active and (not sequence.steps or len(sequence.steps) == 0):
        raise HTTPException(
            status_code=400,
            detail="Cannot activate a drip sequence with no steps",
        )

    await db.commit()

    return {
        "id": str(sequence.id),
        "is_active": sequence.is_active,
        "message": (
            "Drip sequence activated" if sequence.is_active
            else "Drip sequence deactivated"
        ),
    }


# ---------------------------------------------------------------------------
# GET /drip-sequences/{id}/enrollments -- List enrollments
# ---------------------------------------------------------------------------

@router.get("/drip-sequences/{sequence_id}/enrollments")
async def list_enrollments(
    sequence_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List contacts enrolled in a drip sequence."""
    # Verify sequence belongs to tenant
    seq_result = await db.execute(
        select(DripSequence.id).where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == user.tenant_id,
        )
    )
    if not seq_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Drip sequence not found")

    base_filter = [
        DripEnrollment.sequence_id == sequence_id,
        DripEnrollment.tenant_id == user.tenant_id,
    ]
    if status_filter:
        base_filter.append(DripEnrollment.status == status_filter)

    count_q = select(func.count(DripEnrollment.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    data_q = (
        select(DripEnrollment)
        .where(*base_filter)
        .order_by(DripEnrollment.enrolled_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    enrollments = result.scalars().all()

    return {
        "enrollments": [
            {
                "id": str(e.id),
                "contact_id": str(e.contact_id),
                "contact_phone": (
                    e.contact.phone_number if e.contact else None
                ),
                "contact_name": (
                    f"{e.contact.first_name or ''} {e.contact.last_name or ''}".strip()
                    if e.contact else None
                ),
                "current_step": e.current_step,
                "status": e.status,
                "enrolled_at": e.enrolled_at.isoformat(),
                "next_step_at": (
                    e.next_step_at.isoformat() if e.next_step_at else None
                ),
                "completed_at": (
                    e.completed_at.isoformat() if e.completed_at else None
                ),
            }
            for e in enrollments
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST /drip-sequences/{id}/enroll -- Enroll contacts
# ---------------------------------------------------------------------------

@router.post("/drip-sequences/{sequence_id}/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_contacts(
    sequence_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "owner")),
):
    """Enroll one or more contacts in a drip sequence.

    Body: ``{"contact_ids": ["<uuid>", ...]}``
    """
    # Verify sequence
    seq_result = await db.execute(
        select(DripSequence).where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == user.tenant_id,
        )
    )
    sequence = seq_result.scalar_one_or_none()
    if not sequence:
        raise HTTPException(status_code=404, detail="Drip sequence not found")

    if not sequence.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot enroll contacts in an inactive sequence",
        )

    contact_ids = body.get("contact_ids", [])
    if not contact_ids:
        raise HTTPException(status_code=400, detail="No contact_ids provided")

    enrolled = []
    skipped = []

    for cid in contact_ids:
        contact_uuid = uuid.UUID(str(cid))

        # Verify contact belongs to tenant
        contact_result = await db.execute(
            select(Contact).where(
                Contact.id == contact_uuid,
                Contact.tenant_id == user.tenant_id,
            )
        )
        contact = contact_result.scalar_one_or_none()
        if not contact:
            skipped.append({"contact_id": str(cid), "reason": "Contact not found"})
            continue

        if contact.status == "unsubscribed":
            skipped.append({"contact_id": str(cid), "reason": "Contact opted out"})
            continue

        # Check if already enrolled (active)
        existing_q = select(DripEnrollment).where(
            DripEnrollment.sequence_id == sequence.id,
            DripEnrollment.contact_id == contact_uuid,
            DripEnrollment.status == "active",
        )
        existing_result = await db.execute(existing_q)
        if existing_result.scalar_one_or_none():
            skipped.append({"contact_id": str(cid), "reason": "Already enrolled"})
            continue

        # Calculate next step time based on first step delay
        next_step_at = datetime.now(timezone.utc)
        if sequence.steps:
            first_step = min(sequence.steps, key=lambda s: s.step_order)
            next_step_at += timedelta(minutes=first_step.delay_minutes)

        enrollment = DripEnrollment(
            sequence_id=sequence.id,
            contact_id=contact_uuid,
            tenant_id=user.tenant_id,
            current_step=0,
            status="active",
            next_step_at=next_step_at,
        )
        db.add(enrollment)
        enrolled.append(str(cid))

    await db.commit()

    return {
        "enrolled": enrolled,
        "skipped": skipped,
        "enrolled_count": len(enrolled),
        "skipped_count": len(skipped),
    }
