"""Contact management routes -- CRUD, import, export, bulk actions."""

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_id
from app.models.contact import Contact
from app.models.contact_list import ContactList
from app.models.contact_list_member import ContactListMember
from app.models.user import User
from app.schemas.contact import (
    ContactBulkAction,
    ContactCreate,
    ContactImportResponse,
    ContactResponse,
    ContactUpdate,
)
from app.services.contact_service import (
    bulk_action,
    get_contacts_paginated,
    import_contacts_from_csv,
    normalize_phone,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET / -- paginated contact list
# ---------------------------------------------------------------------------

@router.get("/")
async def list_contacts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    list_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List contacts with pagination, search, and filtering."""
    contacts, total = await get_contacts_paginated(
        db,
        tenant_id=user.tenant_id,
        page=page,
        page_size=per_page,
        search=search,
        status_filter=status_filter,
        list_id=list_id,
    )
    return {
        "contacts": [
            ContactResponse.model_validate(c) for c in contacts
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST / -- create single contact
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a single contact with phone validation and duplicate check."""
    phone = normalize_phone(data.phone_number)
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid phone number: {data.phone_number}",
        )

    # Duplicate check
    existing = await db.execute(
        select(Contact).where(
            and_(
                Contact.tenant_id == user.tenant_id,
                Contact.phone_number == phone,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this phone number already exists",
        )

    contact = Contact(
        tenant_id=user.tenant_id,
        phone_number=phone,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        custom_fields=data.custom_fields or {},
        status="active",
        opt_in_method=data.opt_in_method,
        opted_in_at=datetime.now(timezone.utc),
        message_count=0,
    )
    db.add(contact)
    await db.flush()

    # Add to lists
    if data.list_ids:
        for lid in data.list_ids:
            # Validate list belongs to tenant
            list_result = await db.execute(
                select(ContactList).where(
                    and_(
                        ContactList.id == lid,
                        ContactList.tenant_id == user.tenant_id,
                    )
                )
            )
            clist = list_result.scalar_one_or_none()
            if not clist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"List {lid} not found",
                )
            member = ContactListMember(
                contact_id=contact.id,
                list_id=lid,
            )
            db.add(member)
            clist.contact_count += 1

    await db.commit()
    await db.refresh(contact)
    return {"contact": ContactResponse.model_validate(contact)}


# ---------------------------------------------------------------------------
# POST /import -- CSV/Excel import
# ---------------------------------------------------------------------------

@router.post("/import")
async def import_contacts(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    list_id: uuid.UUID | None = Form(None),
    skip_duplicates: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Import contacts from a CSV or Excel file with column mapping.

    The ``mapping`` field is a JSON string: ``{"csv_col": "field_name", ...}``
    """
    import json

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    # Read file content
    content = await file.read()

    # Handle Excel files by converting to CSV
    if file.filename.endswith((".xlsx", ".xls")):
        try:
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(content))
            ws = wb.active
            output = io.StringIO()
            writer = csv.writer(output)
            for row in ws.iter_rows(values_only=True):
                writer.writerow([str(cell) if cell is not None else "" for cell in row])
            file_content = output.getvalue()
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Excel support requires openpyxl; please upload CSV instead",
            )
    else:
        file_content = content.decode("utf-8-sig")

    try:
        column_mapping = json.loads(mapping)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid mapping JSON",
        )

    # Validate list_id belongs to tenant
    if list_id:
        list_result = await db.execute(
            select(ContactList).where(
                and_(
                    ContactList.id == list_id,
                    ContactList.tenant_id == user.tenant_id,
                )
            )
        )
        if not list_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target list not found",
            )

    result = await import_contacts_from_csv(
        db,
        tenant_id=user.tenant_id,
        file_content=file_content,
        mapping=column_mapping,
        list_id=list_id,
        skip_duplicates=skip_duplicates,
    )

    return ContactImportResponse(
        total=result.total,
        imported=result.imported,
        skipped=result.skipped,
        failed=result.failed,
        errors=result.errors[:100],  # cap error list
    )


# ---------------------------------------------------------------------------
# GET /export -- CSV export
# ---------------------------------------------------------------------------

@router.get("/export")
async def export_contacts(
    status_filter: str | None = Query(None, alias="status"),
    list_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export all matching contacts as a CSV download."""
    query = select(Contact).where(Contact.tenant_id == user.tenant_id)

    if status_filter:
        query = query.where(Contact.status == status_filter)
    else:
        query = query.where(Contact.status != "blocked")

    if list_id:
        query = query.join(
            ContactListMember,
            and_(
                ContactListMember.contact_id == Contact.id,
                ContactListMember.list_id == list_id,
            ),
        )

    query = query.order_by(Contact.created_at.desc())
    result = await db.execute(query)
    contacts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "phone_number", "email", "first_name", "last_name",
        "status", "opt_in_method", "created_at",
    ])
    for c in contacts:
        writer.writerow([
            c.phone_number,
            c.email or "",
            c.first_name or "",
            c.last_name or "",
            c.status,
            c.opt_in_method or "",
            c.created_at.isoformat() if c.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts_export.csv"},
    )


# ---------------------------------------------------------------------------
# GET /{id} -- single contact detail
# ---------------------------------------------------------------------------

@router.get("/{contact_id}")
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single contact with list memberships."""
    result = await db.execute(
        select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.tenant_id == user.tenant_id,
            )
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # Fetch list memberships
    members_result = await db.execute(
        select(ContactList)
        .join(
            ContactListMember,
            ContactListMember.list_id == ContactList.id,
        )
        .where(ContactListMember.contact_id == contact_id)
    )
    lists = [
        {"id": str(cl.id), "name": cl.name, "tag_color": cl.tag_color}
        for cl in members_result.scalars().all()
    ]

    return {
        "contact": ContactResponse.model_validate(contact),
        "lists": lists,
        "conversation_url": f"/api/v1/inbox?contact_id={contact_id}",
    }


# ---------------------------------------------------------------------------
# PUT /{id} -- update contact
# ---------------------------------------------------------------------------

@router.put("/{contact_id}")
async def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update contact fields."""
    result = await db.execute(
        select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.tenant_id == user.tenant_id,
            )
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    if data.email is not None:
        contact.email = data.email
    if data.first_name is not None:
        contact.first_name = data.first_name
    if data.last_name is not None:
        contact.last_name = data.last_name
    if data.custom_fields is not None:
        contact.custom_fields = data.custom_fields
    if data.status is not None:
        contact.status = data.status
        if data.status == "opted_out":
            contact.opted_out_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(contact)
    return {"contact": ContactResponse.model_validate(contact)}


# ---------------------------------------------------------------------------
# DELETE /{id} -- soft delete
# ---------------------------------------------------------------------------

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete a contact by setting status to 'blocked'."""
    result = await db.execute(
        select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.tenant_id == user.tenant_id,
            )
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    contact.status = "blocked"
    await db.commit()
    return {"message": "Contact deleted"}


# ---------------------------------------------------------------------------
# POST /bulk -- bulk actions
# ---------------------------------------------------------------------------

@router.post("/bulk")
async def bulk_contacts(
    data: ContactBulkAction,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Perform a bulk action on a set of contacts.

    Supported actions: ``delete``, ``tag``, ``add_to_list``,
    ``remove_from_list``, ``unsubscribe``.
    """
    valid_actions = {"delete", "tag", "add_to_list", "remove_from_list", "unsubscribe"}
    if data.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action. Must be one of: {', '.join(sorted(valid_actions))}",
        )

    result = await bulk_action(
        db,
        tenant_id=user.tenant_id,
        contact_ids=data.contact_ids,
        action=data.action,
        value=data.value,
    )
    return result
