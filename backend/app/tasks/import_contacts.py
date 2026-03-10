"""Celery task for background contact import from CSV files."""

import logging
import os
import uuid

from app.celery_app import celery_app
from app.database import get_sync_session

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def import_contacts_task(
    self,
    tenant_id: str,
    file_path: str,
    mapping: dict,
    list_id: str | None = None,
    skip_duplicates: bool = True,
):
    """Process a CSV file and import contacts using the contact service.

    This task runs synchronously in a Celery worker. It reads the CSV from
    ``file_path``, calls the import logic, and returns the results.

    Parameters
    ----------
    tenant_id : str
        UUID of the tenant (as string).
    file_path : str
        Path to the uploaded CSV file on disk.
    mapping : dict
        Column mapping ``{ csv_column: contact_field_name }``.
    list_id : str | None
        Optional UUID of a list to add imported contacts to.
    skip_duplicates : bool
        Whether to skip contacts that already exist (by phone number).
    """
    import csv
    import io
    from datetime import datetime, timezone

    import phonenumbers
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.contact import Contact
    from app.models.contact_list import ContactList
    from app.models.contact_list_member import ContactListMember
    from app.services.contact_service import normalize_phone

    with get_sync_session() as db:
        try:
            tenant_uuid = uuid.UUID(tenant_id)
            list_uuid = uuid.UUID(list_id) if list_id else None

            # Read file
            if not os.path.exists(file_path):
                return {
                    "status": "failed",
                    "error": f"File not found: {file_path}",
                    "total": 0,
                    "imported": 0,
                    "skipped": 0,
                    "failed": 0,
                    "errors": [],
                }

            with open(file_path, "r", encoding="utf-8-sig") as f:
                file_content = f.read()

            reader = csv.DictReader(io.StringIO(file_content))
            rows = list(reader)

            total = len(rows)
            imported = 0
            skipped = 0
            failed = 0
            errors = []

            if not rows:
                # Successfully processed (empty file) -- safe to clean up
                cleanup_import_file.delay(file_path)
                return {
                    "status": "completed",
                    "total": 0,
                    "imported": 0,
                    "skipped": 0,
                    "failed": 0,
                    "errors": [],
                }

            # Reverse mapping: field -> csv column
            field_to_col = {v: k for k, v in mapping.items()}
            phone_col = field_to_col.get("phone_number")

            if not phone_col:
                cleanup_import_file.delay(file_path)
                return {
                    "status": "failed",
                    "error": "No phone_number mapping provided",
                    "total": total,
                    "imported": 0,
                    "skipped": total,
                    "failed": total,
                    "errors": [{"row": 0, "error": "No phone_number mapping"}],
                }

            known_fields = {"phone_number", "email", "first_name", "last_name"}

            # Pre-fetch existing phones
            existing_rows = db.execute(
                select(Contact.phone_number).where(Contact.tenant_id == tenant_uuid)
            ).all()
            existing_phones = {r[0] for r in existing_rows}

            contacts_to_insert = []
            phones_in_batch = set()

            for row_idx, row in enumerate(rows, start=1):
                raw_phone = row.get(phone_col, "")
                phone = normalize_phone(raw_phone)

                if phone is None:
                    failed += 1
                    errors.append(
                        {"row": row_idx, "error": f"Invalid phone: {raw_phone!r}"}
                    )
                    continue

                if phone in existing_phones or phone in phones_in_batch:
                    if skip_duplicates:
                        skipped += 1
                        continue
                    skipped += 1
                    continue

                phones_in_batch.add(phone)

                contact_data = {
                    "id": uuid.uuid4(),
                    "tenant_id": tenant_uuid,
                    "phone_number": phone,
                    "status": "active",
                    "opt_in_method": "import",
                    "opted_in_at": datetime.now(timezone.utc),
                    "message_count": 0,
                }
                custom_fields = {}

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
                batch_size = 500
                for i in range(0, len(contacts_to_insert), batch_size):
                    batch = contacts_to_insert[i : i + batch_size]
                    stmt = pg_insert(Contact).values(batch)
                    if skip_duplicates:
                        stmt = stmt.on_conflict_do_nothing(
                            constraint="uq_contact_tenant_phone"
                        )
                    db.execute(stmt)

                imported = len(contacts_to_insert)

                # Add to list
                if list_uuid:
                    members = [
                        {
                            "id": uuid.uuid4(),
                            "contact_id": c["id"],
                            "list_id": list_uuid,
                        }
                        for c in contacts_to_insert
                    ]
                    for i in range(0, len(members), batch_size):
                        batch = members[i : i + batch_size]
                        member_stmt = pg_insert(ContactListMember).values(batch)
                        member_stmt = member_stmt.on_conflict_do_nothing(
                            constraint="uq_contact_list_membership"
                        )
                        db.execute(member_stmt)

                    # Update count
                    from sqlalchemy import update as sql_update

                    db.execute(
                        sql_update(ContactList)
                        .where(ContactList.id == list_uuid)
                        .values(
                            contact_count=ContactList.contact_count + imported
                        )
                    )

            db.commit()

            # Only clean up the file after successful import
            cleanup_import_file.delay(file_path)

            return {
                "status": "completed",
                "total": total,
                "imported": imported,
                "skipped": skipped,
                "failed": failed,
                "errors": errors[:100],
            }

        except Exception as exc:
            logger.exception("Import task failed: %s", exc)
            db.rollback()
            # Do NOT delete the file here -- it may be needed for retry
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                # All retries exhausted, now safe to clean up
                cleanup_import_file.delay(file_path)
                return {
                    "status": "failed",
                    "error": str(exc),
                    "total": 0,
                    "imported": 0,
                    "skipped": 0,
                    "failed": 0,
                    "errors": [],
                }


@celery_app.task
def cleanup_import_file(file_path: str):
    """Remove the temporary import file after processing is complete."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"status": "cleaned", "file": file_path}
    except OSError:
        return {"status": "cleanup_failed", "file": file_path}
