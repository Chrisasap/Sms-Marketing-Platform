"""Contact list management routes -- CRUD, add/remove members."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.contact import Contact
from app.models.contact_list import ContactList
from app.models.contact_list_member import ContactListMember
from app.models.user import User
from app.schemas.contact import ContactResponse
from app.schemas.contact_list import ListCreate, ListResponse, ListUpdate

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class AddContactsRequest(BaseModel):
    contact_ids: list[uuid.UUID]


class RemoveContactsRequest(BaseModel):
    contact_ids: list[uuid.UUID]


async def _get_list_or_404(
    db: AsyncSession, list_id: uuid.UUID, tenant_id: uuid.UUID
) -> ContactList:
    result = await db.execute(
        select(ContactList).where(
            and_(
                ContactList.id == list_id,
                ContactList.tenant_id == tenant_id,
            )
        )
    )
    clist = result.scalar_one_or_none()
    if not clist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="List not found",
        )
    return clist


# ---------------------------------------------------------------------------
# GET / -- list all contact lists with counts
# ---------------------------------------------------------------------------

@router.get("/")
async def list_contact_lists(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all contact lists for the current tenant."""
    base = select(ContactList).where(ContactList.tenant_id == user.tenant_id)
    count_q = select(func.count(ContactList.id)).where(
        ContactList.tenant_id == user.tenant_id
    )

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    lists_result = await db.execute(
        base.order_by(ContactList.created_at.desc()).offset(offset).limit(per_page)
    )
    lists = lists_result.scalars().all()

    return {
        "lists": [ListResponse.model_validate(cl) for cl in lists],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST / -- create list
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_list(
    data: ListCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new contact list."""
    clist = ContactList(
        tenant_id=user.tenant_id,
        name=data.name,
        description=data.description,
        tag_color=data.tag_color,
        is_smart=data.is_smart,
        smart_filter=data.smart_filter,
        contact_count=0,
    )
    db.add(clist)
    await db.commit()
    await db.refresh(clist)
    return {"list": ListResponse.model_validate(clist)}


# ---------------------------------------------------------------------------
# GET /{id} -- list detail with member count
# ---------------------------------------------------------------------------

@router.get("/{list_id}")
async def get_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get details for a specific list including live member count."""
    clist = await _get_list_or_404(db, list_id, user.tenant_id)

    # Live count
    count_result = await db.execute(
        select(func.count(ContactListMember.id)).where(
            ContactListMember.list_id == list_id
        )
    )
    live_count = count_result.scalar() or 0

    # Sync cached count if it drifted
    if clist.contact_count != live_count:
        clist.contact_count = live_count
        await db.commit()
        await db.refresh(clist)

    return {"list": ListResponse.model_validate(clist)}


# ---------------------------------------------------------------------------
# PUT /{id} -- update list
# ---------------------------------------------------------------------------

@router.put("/{list_id}")
async def update_list(
    list_id: uuid.UUID,
    data: ListUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a contact list's metadata."""
    clist = await _get_list_or_404(db, list_id, user.tenant_id)

    if data.name is not None:
        clist.name = data.name
    if data.description is not None:
        clist.description = data.description
    if data.tag_color is not None:
        clist.tag_color = data.tag_color
    if data.smart_filter is not None:
        clist.smart_filter = data.smart_filter

    await db.commit()
    await db.refresh(clist)
    return {"list": ListResponse.model_validate(clist)}


# ---------------------------------------------------------------------------
# DELETE /{id} -- delete list and junction records
# ---------------------------------------------------------------------------

@router.delete("/{list_id}")
async def delete_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a contact list and all its membership records."""
    clist = await _get_list_or_404(db, list_id, user.tenant_id)

    # Remove all membership records
    await db.execute(
        delete(ContactListMember).where(ContactListMember.list_id == list_id)
    )
    await db.delete(clist)
    await db.commit()
    return {"message": "List deleted"}


# ---------------------------------------------------------------------------
# GET /{id}/contacts -- paginated list members
# ---------------------------------------------------------------------------

@router.get("/{list_id}/contacts")
async def list_contacts_in_list(
    list_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all contacts belonging to a specific list."""
    await _get_list_or_404(db, list_id, user.tenant_id)

    base = (
        select(Contact)
        .join(
            ContactListMember,
            and_(
                ContactListMember.contact_id == Contact.id,
                ContactListMember.list_id == list_id,
            ),
        )
        .where(Contact.tenant_id == user.tenant_id)
    )

    count_q = (
        select(func.count(Contact.id))
        .join(
            ContactListMember,
            and_(
                ContactListMember.contact_id == Contact.id,
                ContactListMember.list_id == list_id,
            ),
        )
        .where(Contact.tenant_id == user.tenant_id)
    )

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    contacts_result = await db.execute(
        base.order_by(Contact.created_at.desc()).offset(offset).limit(per_page)
    )
    contacts = contacts_result.scalars().all()

    return {
        "contacts": [ContactResponse.model_validate(c) for c in contacts],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# POST /{id}/contacts -- add contacts to list
# ---------------------------------------------------------------------------

@router.post("/{list_id}/contacts")
async def add_contacts_to_list(
    list_id: uuid.UUID,
    data: AddContactsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add one or more contacts to a list by contact_ids."""
    clist = await _get_list_or_404(db, list_id, user.tenant_id)

    # Validate contacts belong to tenant
    valid_result = await db.execute(
        select(Contact.id).where(
            and_(
                Contact.id.in_(data.contact_ids),
                Contact.tenant_id == user.tenant_id,
            )
        )
    )
    valid_ids = {row[0] for row in valid_result}

    added = 0
    for cid in valid_ids:
        # Check for existing membership
        existing = await db.execute(
            select(ContactListMember).where(
                and_(
                    ContactListMember.contact_id == cid,
                    ContactListMember.list_id == list_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            continue
        member = ContactListMember(contact_id=cid, list_id=list_id)
        db.add(member)
        added += 1

    clist.contact_count += added
    await db.commit()

    return {"message": f"{added} contact(s) added to list", "added": added}


# ---------------------------------------------------------------------------
# DELETE /{id}/contacts -- remove contacts from list
# ---------------------------------------------------------------------------

@router.delete("/{list_id}/contacts")
async def remove_contacts_from_list(
    list_id: uuid.UUID,
    data: RemoveContactsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove one or more contacts from a list."""
    clist = await _get_list_or_404(db, list_id, user.tenant_id)

    result = await db.execute(
        delete(ContactListMember).where(
            and_(
                ContactListMember.list_id == list_id,
                ContactListMember.contact_id.in_(data.contact_ids),
            )
        )
    )
    removed = result.rowcount

    # Update cached count
    count_result = await db.execute(
        select(func.count(ContactListMember.id)).where(
            ContactListMember.list_id == list_id
        )
    )
    clist.contact_count = count_result.scalar() or 0

    await db.commit()
    return {"message": f"{removed} contact(s) removed from list", "removed": removed}
