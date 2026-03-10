"""Two-way messaging inbox router.

Provides conversation management, threaded message views, replies,
internal notes, assignment, and status management -- all tenant-scoped.
"""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import (
    ConversationResponse,
    ConversationUpdate,
    ReplyRequest,
)
from app.services.message_sender import send_inbox_reply

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET / -- List conversations with pagination, filtering, and search
# ---------------------------------------------------------------------------

@router.get("/")
async def list_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    assigned_to: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List inbox conversations ordered by most recent message.

    Supports filtering by status (open/closed), assigned user, and free-text
    search against contact phone number or name.
    """
    tenant_id = user.tenant_id

    base_filter = [Conversation.tenant_id == tenant_id]

    if status_filter:
        base_filter.append(Conversation.status == status_filter)
    if assigned_to:
        base_filter.append(Conversation.assigned_to == assigned_to)

    # Build search join condition
    needs_contact_join = bool(search)

    # Count query
    count_q = select(func.count(Conversation.id)).where(*base_filter)
    if needs_contact_join:
        count_q = (
            count_q
            .join(Contact, Contact.id == Conversation.contact_id)
            .where(
                or_(
                    Contact.phone_number.ilike(f"%{search}%"),
                    Contact.first_name.ilike(f"%{search}%"),
                    Contact.last_name.ilike(f"%{search}%"),
                )
            )
        )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Data query -- eager-load contact to avoid N+1
    data_q = select(Conversation).options(selectinload(Conversation.contact)).where(*base_filter)
    if needs_contact_join:
        data_q = (
            data_q
            .join(Contact, Contact.id == Conversation.contact_id)
            .where(
                or_(
                    Contact.phone_number.ilike(f"%{search}%"),
                    Contact.first_name.ilike(f"%{search}%"),
                    Contact.last_name.ilike(f"%{search}%"),
                )
            )
        )
    data_q = (
        data_q.order_by(Conversation.last_message_at.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        # Fetch last message preview
        last_msg_q = (
            select(Message.body)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_q)
        last_msg_body = last_msg_result.scalar_one_or_none()

        contact = conv.contact
        items.append({
            "id": str(conv.id),
            "contact_id": str(conv.contact_id),
            "contact_phone": conv.contact_phone,
            "contact_name": (
                f"{contact.first_name or ''} {contact.last_name or ''}".strip()
                if contact else None
            ),
            "phone_number_id": str(conv.phone_number_id),
            "status": conv.status,
            "assigned_to": str(conv.assigned_to) if conv.assigned_to else None,
            "last_message_at": (
                conv.last_message_at.isoformat() if conv.last_message_at else None
            ),
            "unread_count": conv.unread_count,
            "tags": conv.tags or [],
            "last_message_preview": (
                last_msg_body[:120] if last_msg_body else None
            ),
            "created_at": conv.created_at.isoformat(),
        })

    return {
        "conversations": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# GET /{conversation_id} -- Get single conversation with contact info
# ---------------------------------------------------------------------------

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    message_offset: int = Query(0, ge=0, description="Offset for message pagination"),
    message_limit: int = Query(50, ge=1, le=200, description="Max messages to return"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve a single conversation with full contact details.

    Messages are paginated (default: 50 most recent) to avoid loading
    the entire history.  Use ``message_offset`` and ``message_limit``
    to page through older messages.
    """
    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.contact),
            selectinload(Conversation.assigned_user),
        )
        .where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    contact = conv.contact
    assigned_user = conv.assigned_user

    # Paginated messages -- most recent first, limited to avoid loading all
    msg_q = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == user.tenant_id,
        )
        .order_by(Message.created_at.desc())
        .offset(message_offset)
        .limit(message_limit)
    )
    msg_result = await db.execute(msg_q)
    recent_messages = list(reversed(msg_result.scalars().all()))

    # Total message count for pagination info
    msg_count_q = select(func.count(Message.id)).where(
        Message.conversation_id == conversation_id,
        Message.tenant_id == user.tenant_id,
    )
    msg_count_result = await db.execute(msg_count_q)
    total_messages = msg_count_result.scalar() or 0

    return {
        "conversation": {
            "id": str(conv.id),
            "contact_id": str(conv.contact_id),
            "contact_phone": conv.contact_phone,
            "phone_number_id": str(conv.phone_number_id),
            "status": conv.status,
            "assigned_to": str(conv.assigned_to) if conv.assigned_to else None,
            "assigned_user_name": (
                f"{assigned_user.first_name} {assigned_user.last_name}"
                if assigned_user else None
            ),
            "last_message_at": (
                conv.last_message_at.isoformat() if conv.last_message_at else None
            ),
            "unread_count": conv.unread_count,
            "tags": conv.tags or [],
            "created_at": conv.created_at.isoformat(),
        },
        "contact": {
            "id": str(contact.id),
            "phone_number": contact.phone_number,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "status": contact.status,
            "custom_fields": contact.custom_fields or {},
            "message_count": contact.message_count,
            "last_messaged_at": (
                contact.last_messaged_at.isoformat()
                if contact.last_messaged_at else None
            ),
        } if contact else None,
        "messages": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "sender_type": m.sender_type,
                "body": m.body,
                "status": m.status,
                "created_at": m.created_at.isoformat(),
            }
            for m in recent_messages
        ],
        "total_messages": total_messages,
        "message_offset": message_offset,
        "message_limit": message_limit,
    }


# ---------------------------------------------------------------------------
# GET /{conversation_id}/messages -- Paginated message thread
# ---------------------------------------------------------------------------

@router.get("/{conversation_id}/messages")
async def list_messages(
    conversation_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return paginated message thread for a conversation (oldest first)."""
    # Verify conversation belongs to tenant
    conv_result = await db.execute(
        select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Count
    count_q = select(func.count(Message.id)).where(
        Message.conversation_id == conversation_id,
        Message.tenant_id == user.tenant_id,
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Fetch messages oldest first (newest last)
    data_q = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == user.tenant_id,
        )
        .order_by(Message.created_at.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    messages = result.scalars().all()

    # Reset unread count when messages are viewed
    conv_update = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_update.scalar_one_or_none()
    if conv and conv.unread_count > 0:
        conv.unread_count = 0
        await db.commit()

    return {
        "messages": [
            {
                "id": str(m.id),
                "conversation_id": str(m.conversation_id),
                "direction": m.direction,
                "sender_type": m.sender_type,
                "sender_id": str(m.sender_id) if m.sender_id else None,
                "body": m.body,
                "media_urls": m.media_urls or [],
                "bandwidth_message_id": m.bandwidth_message_id,
                "status": m.status,
                "error_code": m.error_code,
                "segments": m.segments,
                "cost": float(m.cost),
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST /{conversation_id}/reply -- Send a reply
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/reply", status_code=status.HTTP_201_CREATED)
async def reply_to_conversation(
    conversation_id: uuid.UUID,
    body: ReplyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send an outbound reply in the conversation.

    Creates a ``Message`` record with direction=outbound, calls Bandwidth to
    deliver the message, deducts credits, and updates the conversation
    timestamp.
    """
    # Verify conversation exists and belongs to tenant
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if the contact has opted out
    contact_result = await db.execute(
        select(Contact).where(Contact.id == conv.contact_id)
    )
    contact = contact_result.scalar_one_or_none()
    if contact and contact.status == "unsubscribed":
        raise HTTPException(
            status_code=400,
            detail="Contact has opted out. Cannot send messages.",
        )

    try:
        result = await send_inbox_reply(
            db=db,
            tenant_id=user.tenant_id,
            conversation_id=conversation_id,
            user_id=user.id,
            text=body.body,
            media_urls=body.media_urls if body.media_urls else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to send inbox reply")
        raise HTTPException(status_code=502, detail=f"Send failed: {str(e)}")


# ---------------------------------------------------------------------------
# PUT /{conversation_id} -- Update conversation metadata
# ---------------------------------------------------------------------------

@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update conversation status, assigned_to, or tags."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if body.status is not None:
        if body.status not in ("open", "closed", "snoozed"):
            raise HTTPException(
                status_code=400,
                detail="Status must be one of: open, closed, snoozed",
            )
        conv.status = body.status
    if body.assigned_to is not None:
        # Verify the target user belongs to the same tenant
        from app.models.user import User as UserModel
        assignee_result = await db.execute(
            select(UserModel).where(
                UserModel.id == body.assigned_to,
                UserModel.tenant_id == user.tenant_id,
                UserModel.is_active == True,
            )
        )
        if not assignee_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Assignee not found in this tenant"
            )
        conv.assigned_to = body.assigned_to
    if body.tags is not None:
        conv.tags = body.tags

    await db.commit()
    await db.refresh(conv)

    return {
        "id": str(conv.id),
        "status": conv.status,
        "assigned_to": str(conv.assigned_to) if conv.assigned_to else None,
        "tags": conv.tags or [],
        "message": "Conversation updated",
    }


# ---------------------------------------------------------------------------
# POST /{conversation_id}/assign -- Assign to a user
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Assign the conversation to a specific team member.

    Body: ``{"user_id": "<uuid>"}``  Pass ``null`` to unassign.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    target_user_id = body.get("user_id")
    if target_user_id is not None:
        target_user_id = uuid.UUID(str(target_user_id))
        # Verify assignee exists in tenant
        from app.models.user import User as UserModel
        assignee_result = await db.execute(
            select(UserModel).where(
                UserModel.id == target_user_id,
                UserModel.tenant_id == user.tenant_id,
                UserModel.is_active == True,
            )
        )
        assignee = assignee_result.scalar_one_or_none()
        if not assignee:
            raise HTTPException(
                status_code=400, detail="User not found in this tenant"
            )
        conv.assigned_to = target_user_id
    else:
        conv.assigned_to = None

    await db.commit()

    return {
        "message": "Conversation assigned",
        "conversation_id": str(conv.id),
        "assigned_to": str(conv.assigned_to) if conv.assigned_to else None,
    }


# ---------------------------------------------------------------------------
# POST /{conversation_id}/close -- Close conversation
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/close")
async def close_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Close a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.status == "closed":
        raise HTTPException(
            status_code=400, detail="Conversation is already closed"
        )

    conv.status = "closed"
    await db.commit()

    return {
        "message": "Conversation closed",
        "conversation_id": str(conv.id),
        "status": "closed",
    }


# ---------------------------------------------------------------------------
# POST /{conversation_id}/note -- Add an internal note
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/note", status_code=status.HTTP_201_CREATED)
async def add_internal_note(
    conversation_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add an internal note to a conversation.

    Notes are stored as ``Message`` records with ``sender_type='system'``
    and are not sent to the contact.

    Body: ``{"body": "Note text here"}``
    """
    # Verify conversation
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    note_text = body.get("body", "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note body is required")

    note = Message(
        conversation_id=conversation_id,
        tenant_id=user.tenant_id,
        direction="internal",
        sender_type="system",
        sender_id=user.id,
        body=note_text,
        media_urls=[],
        status="delivered",
        segments=0,
        cost=0,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return {
        "id": str(note.id),
        "conversation_id": str(note.conversation_id),
        "sender_type": note.sender_type,
        "sender_id": str(note.sender_id),
        "body": note.body,
        "created_at": note.created_at.isoformat(),
        "message": "Internal note added",
    }
