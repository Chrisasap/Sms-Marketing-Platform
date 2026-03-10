"""Message template CRUD router.

Provides creation, retrieval, update, deletion, and preview rendering
of reusable message templates -- all tenant-scoped.
"""

import uuid
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.template import Template
from app.models.contact import Contact
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET / -- List templates with optional category filter
# ---------------------------------------------------------------------------

@router.get("/")
async def list_templates(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    category: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List message templates for the tenant.

    Non-shared templates are only visible to their creator.
    """
    tenant_id = user.tenant_id

    base_filter = [
        Template.tenant_id == tenant_id,
        or_(
            Template.is_shared == True,
            Template.created_by == user.id,
        ),
    ]

    if category:
        base_filter.append(Template.category == category)
    if search:
        base_filter.append(
            or_(
                Template.name.ilike(f"%{search}%"),
                Template.body.ilike(f"%{search}%"),
            )
        )

    # Count
    count_q = select(func.count(Template.id)).where(*base_filter)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Data
    data_q = (
        select(Template)
        .where(*base_filter)
        .order_by(Template.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(data_q)
    templates = result.scalars().all()

    return {
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "category": t.category,
                "body": t.body,
                "media_urls": t.media_urls or [],
                "is_shared": t.is_shared,
                "created_by": str(t.created_by),
                "created_at": t.created_at.isoformat(),
            }
            for t in templates
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST / -- Create a new template
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new message template."""
    template = Template(
        tenant_id=user.tenant_id,
        name=body.name,
        category=body.category,
        body=body.body,
        media_urls=body.media_urls or [],
        is_shared=body.is_shared,
        created_by=user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "template": {
            "id": str(template.id),
            "name": template.name,
            "category": template.category,
            "body": template.body,
            "media_urls": template.media_urls or [],
            "is_shared": template.is_shared,
            "created_by": str(template.created_by),
            "created_at": template.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# GET /{template_id} -- Get a single template
# ---------------------------------------------------------------------------

@router.get("/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific template by ID."""
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.tenant_id == user.tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check visibility: non-shared templates only visible to creator
    if not template.is_shared and template.created_by != user.id:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "template": {
            "id": str(template.id),
            "name": template.name,
            "category": template.category,
            "body": template.body,
            "media_urls": template.media_urls or [],
            "is_shared": template.is_shared,
            "created_by": str(template.created_by),
            "created_at": template.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# PUT /{template_id} -- Update a template
# ---------------------------------------------------------------------------

@router.put("/{template_id}")
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an existing message template.

    Only the creator or an admin/owner can update a template.
    """
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.tenant_id == user.tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Permission check: creator, admin, or owner
    if (
        template.created_by != user.id
        and user.role not in ("admin", "owner")
        and not user.is_superadmin
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this template"
        )

    if body.name is not None:
        template.name = body.name
    if body.category is not None:
        template.category = body.category
    if body.body is not None:
        template.body = body.body
    if body.media_urls is not None:
        template.media_urls = body.media_urls
    if body.is_shared is not None:
        template.is_shared = body.is_shared

    await db.commit()
    await db.refresh(template)

    return {
        "template": {
            "id": str(template.id),
            "name": template.name,
            "category": template.category,
            "body": template.body,
            "media_urls": template.media_urls or [],
            "is_shared": template.is_shared,
            "created_by": str(template.created_by),
            "created_at": template.created_at.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# DELETE /{template_id} -- Delete a template
# ---------------------------------------------------------------------------

@router.delete("/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a message template.

    Only the creator or an admin/owner can delete a template.
    """
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.tenant_id == user.tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if (
        template.created_by != user.id
        and user.role not in ("admin", "owner")
        and not user.is_superadmin
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this template"
        )

    await db.delete(template)
    await db.commit()

    return {"message": "Template deleted", "id": str(template_id)}


# ---------------------------------------------------------------------------
# POST /{template_id}/preview -- Preview with sample contact data
# ---------------------------------------------------------------------------

@router.post("/{template_id}/preview")
async def preview_template(
    template_id: uuid.UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Render a template with merge tags replaced by sample contact data.

    Optionally pass ``{"contact_id": "<uuid>"}`` to use a real contact's
    data. Otherwise, placeholder sample data is used.
    """
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.tenant_id == user.tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    body = body or {}
    contact_id = body.get("contact_id")

    # Build merge data either from a real contact or from sample defaults
    merge_data: dict[str, str] = {}
    if contact_id:
        contact_result = await db.execute(
            select(Contact).where(
                Contact.id == uuid.UUID(str(contact_id)),
                Contact.tenant_id == user.tenant_id,
            )
        )
        contact = contact_result.scalar_one_or_none()
        if contact:
            merge_data = {
                "first_name": contact.first_name or "",
                "last_name": contact.last_name or "",
                "phone": contact.phone_number or "",
                "email": contact.email or "",
            }
            if contact.custom_fields:
                for key, value in contact.custom_fields.items():
                    merge_data[key] = str(value)

    # Fall back to sample data for any missing merge tags
    sample_defaults = {
        "first_name": "Jane",
        "last_name": "Doe",
        "phone": "+15551234567",
        "email": "jane@example.com",
    }
    for key, val in sample_defaults.items():
        if key not in merge_data or not merge_data[key]:
            merge_data[key] = val

    # Render merge tags: {{tag_name}}
    rendered = template.body
    for key, value in merge_data.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    # List unresolved merge tags so the caller knows what's missing
    unresolved = re.findall(r"\{\{(\w+)\}\}", rendered)

    return {
        "original": template.body,
        "rendered": rendered,
        "merge_data": merge_data,
        "unresolved_tags": unresolved,
    }
