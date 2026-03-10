"""Contact management service -- import, normalize, paginate, and bulk actions."""

import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import phonenumbers
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.contact_list import ContactList
from app.models.contact_list_member import ContactListMember

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phone-number normalisation
# ---------------------------------------------------------------------------

def normalize_phone(number: str, country: str = "US") -> str | None:
    """Parse *number* with the ``phonenumbers`` library and return the E.164
    representation, or ``None`` when the input is not a valid phone number.
    """
    if not number or not number.strip():
        return None
    try:
        parsed = phonenumbers.parse(number.strip(), country)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------

class ImportResult:
    """Container for import statistics."""

    def __init__(self) -> None:
        self.total: int = 0
        self.imported: int = 0
        self.skipped: int = 0
        self.failed: int = 0
        self.errors: list[dict[str, Any]] = []


async def import_contacts_from_csv(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    file_content: str,
    mapping: dict[str, str],
    list_id: uuid.UUID | None = None,
    skip_duplicates: bool = True,
    country: str = "US",
) -> ImportResult:
    """Parse CSV content, normalise phone numbers, and bulk-insert contacts.

    Parameters
    ----------
    mapping:
        ``{ csv_column_header: contact_field_name }``
        Supported field names: ``phone_number``, ``email``, ``first_name``,
        ``last_name``, and any key that should go into ``custom_fields``.
    """
    result = ImportResult()

    reader = csv.DictReader(io.StringIO(file_content))
    rows = list(reader)
    result.total = len(rows)

    if not rows:
        return result

    # Reverse mapping: contact field -> csv column
    field_to_col: dict[str, str] = {v: k for k, v in mapping.items()}
    phone_col = field_to_col.get("phone_number")

    if not phone_col:
        result.failed = result.total
        result.errors.append({"row": 0, "error": "No phone_number mapping provided"})
        return result

    # Collect known fields
    known_fields = {"phone_number", "email", "first_name", "last_name"}

    # Pre-fetch existing phone numbers for this tenant to detect duplicates
    existing_stmt = select(Contact.phone_number).where(
        Contact.tenant_id == tenant_id
    )
    existing_rows = await db.execute(existing_stmt)
    existing_phones: set[str] = {r[0] for r in existing_rows}

    contacts_to_insert: list[dict[str, Any]] = []
    contact_phones_in_batch: set[str] = set()

    for row_idx, row in enumerate(rows, start=1):
        raw_phone = row.get(phone_col, "")
        phone = normalize_phone(raw_phone, country)

        if phone is None:
            result.failed += 1
            result.errors.append(
                {"row": row_idx, "error": f"Invalid phone number: {raw_phone!r}"}
            )
            continue

        # Duplicate detection
        if phone in existing_phones or phone in contact_phones_in_batch:
            if skip_duplicates:
                result.skipped += 1
                continue
            # If not skipping, we still skip DB unique constraint violations
            result.skipped += 1
            continue

        contact_phones_in_batch.add(phone)

        # Build contact dict
        contact_data: dict[str, Any] = {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "phone_number": phone,
            "status": "active",
            "opt_in_method": "import",
            "opted_in_at": datetime.now(timezone.utc),
            "message_count": 0,
        }
        custom_fields: dict[str, Any] = {}

        for csv_col, field_name in mapping.items():
            value = row.get(csv_col, "")
            if not value:
                continue
            if field_name in known_fields and field_name != "phone_number":
                contact_data[field_name] = value.strip()
            elif field_name != "phone_number":
                custom_fields[field_name] = value.strip()

        contact_data["custom_fields"] = custom_fields
        contacts_to_insert.append(contact_data)

    # Bulk insert
    if contacts_to_insert:
        # Use batches of 500 to stay within reasonable statement sizes
        batch_size = 500
        for i in range(0, len(contacts_to_insert), batch_size):
            batch = contacts_to_insert[i : i + batch_size]
            stmt = pg_insert(Contact).values(batch)
            if skip_duplicates:
                stmt = stmt.on_conflict_do_nothing(
                    constraint="uq_contact_tenant_phone"
                )
            await db.execute(stmt)

        result.imported = len(contacts_to_insert)

        # Add to list if requested
        if list_id:
            members = [
                {
                    "id": uuid.uuid4(),
                    "contact_id": c["id"],
                    "list_id": list_id,
                }
                for c in contacts_to_insert
            ]
            for i in range(0, len(members), batch_size):
                batch = members[i : i + batch_size]
                member_stmt = pg_insert(ContactListMember).values(batch)
                member_stmt = member_stmt.on_conflict_do_nothing(
                    constraint="uq_contact_list_membership"
                )
                await db.execute(member_stmt)

            # Update contact_count on the list
            await db.execute(
                update(ContactList)
                .where(ContactList.id == list_id)
                .values(
                    contact_count=ContactList.contact_count + len(contacts_to_insert)
                )
            )

    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Paginated contact query
# ---------------------------------------------------------------------------

async def get_contacts_paginated(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    status_filter: str | None = None,
    list_id: uuid.UUID | None = None,
) -> tuple[list[Contact], int]:
    """Return a page of contacts and the total matching count.

    Supports:
    - Free-text search across phone, email, first_name, last_name
    - Status filter (active, opted_out, blocked)
    - List membership filter
    """
    base = select(Contact).where(Contact.tenant_id == tenant_id)
    count_base = select(func.count(Contact.id)).where(Contact.tenant_id == tenant_id)

    # List membership filter
    if list_id:
        base = base.join(
            ContactListMember,
            and_(
                ContactListMember.contact_id == Contact.id,
                ContactListMember.list_id == list_id,
            ),
        )
        count_base = count_base.join(
            ContactListMember,
            and_(
                ContactListMember.contact_id == Contact.id,
                ContactListMember.list_id == list_id,
            ),
        )

    # Status filter
    if status_filter:
        base = base.where(Contact.status == status_filter)
        count_base = count_base.where(Contact.status == status_filter)

    # Search
    if search:
        like_term = f"%{search}%"
        search_filter = or_(
            Contact.phone_number.ilike(like_term),
            Contact.email.ilike(like_term),
            Contact.first_name.ilike(like_term),
            Contact.last_name.ilike(like_term),
        )
        base = base.where(search_filter)
        count_base = count_base.where(search_filter)

    # Exclude blocked unless explicitly filtering for them
    if status_filter != "blocked":
        base = base.where(Contact.status != "blocked")
        count_base = count_base.where(Contact.status != "blocked")

    # Count
    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0

    # Page
    offset = (page - 1) * page_size
    base = base.order_by(Contact.created_at.desc()).offset(offset).limit(page_size)

    contacts_result = await db.execute(base)
    contacts = list(contacts_result.scalars().all())

    return contacts, total


# ---------------------------------------------------------------------------
# Bulk actions
# ---------------------------------------------------------------------------

async def bulk_action(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    contact_ids: list[uuid.UUID],
    action: str,
    value: str | None = None,
) -> dict[str, Any]:
    """Execute a bulk action on a set of contacts.

    Supported actions: ``delete``, ``tag``, ``add_to_list``,
    ``remove_from_list``, ``unsubscribe``.
    """
    if not contact_ids:
        return {"affected": 0}

    # Ensure all contacts belong to the tenant
    tenant_filter = and_(
        Contact.tenant_id == tenant_id,
        Contact.id.in_(contact_ids),
    )

    if action == "delete":
        # Soft-delete: set status to blocked
        stmt = (
            update(Contact)
            .where(tenant_filter)
            .values(status="blocked")
        )
        result = await db.execute(stmt)
        await db.commit()
        return {"affected": result.rowcount}

    elif action == "unsubscribe":
        stmt = (
            update(Contact)
            .where(tenant_filter)
            .values(
                status="opted_out",
                opted_out_at=datetime.now(timezone.utc),
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        return {"affected": result.rowcount}

    elif action == "tag":
        if not value:
            return {"affected": 0, "error": "Tag value required"}
        # Add tag to custom_fields.tags array
        contacts_result = await db.execute(
            select(Contact).where(tenant_filter)
        )
        contacts = contacts_result.scalars().all()
        count = 0
        for contact in contacts:
            tags = contact.custom_fields.get("tags", []) if contact.custom_fields else []
            if value not in tags:
                tags.append(value)
                contact.custom_fields = {**(contact.custom_fields or {}), "tags": tags}
                count += 1
        await db.commit()
        return {"affected": count}

    elif action == "add_to_list":
        if not value:
            return {"affected": 0, "error": "List ID required"}
        target_list_id = uuid.UUID(value)
        # Filter contact_ids to only those belonging to this tenant
        valid_result = await db.execute(
            select(Contact.id).where(
                Contact.tenant_id == tenant_id,
                Contact.id.in_(contact_ids),
            )
        )
        valid_ids = [row[0] for row in valid_result]
        if not valid_ids:
            return {"affected": 0}
        members = [
            {
                "id": uuid.uuid4(),
                "contact_id": cid,
                "list_id": target_list_id,
            }
            for cid in valid_ids
        ]
        stmt = pg_insert(ContactListMember).values(members)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_contact_list_membership")
        result = await db.execute(stmt)
        # Update count
        await db.execute(
            update(ContactList)
            .where(ContactList.id == target_list_id)
            .values(
                contact_count=select(func.count(ContactListMember.id))
                .where(ContactListMember.list_id == target_list_id)
                .correlate_except(ContactListMember)
                .scalar_subquery()
            )
        )
        await db.commit()
        return {"affected": len(contact_ids)}

    elif action == "remove_from_list":
        if not value:
            return {"affected": 0, "error": "List ID required"}
        target_list_id = uuid.UUID(value)
        # Filter contact_ids to only those belonging to this tenant
        valid_result = await db.execute(
            select(Contact.id).where(
                Contact.tenant_id == tenant_id,
                Contact.id.in_(contact_ids),
            )
        )
        valid_ids = [row[0] for row in valid_result]
        if not valid_ids:
            return {"affected": 0}
        stmt = delete(ContactListMember).where(
            and_(
                ContactListMember.contact_id.in_(valid_ids),
                ContactListMember.list_id == target_list_id,
            )
        )
        result = await db.execute(stmt)
        # Update count
        await db.execute(
            update(ContactList)
            .where(ContactList.id == target_list_id)
            .values(
                contact_count=select(func.count(ContactListMember.id))
                .where(ContactListMember.list_id == target_list_id)
                .correlate_except(ContactListMember)
                .scalar_subquery()
            )
        )
        await db.commit()
        return {"affected": result.rowcount}

    return {"affected": 0, "error": f"Unknown action: {action}"}
