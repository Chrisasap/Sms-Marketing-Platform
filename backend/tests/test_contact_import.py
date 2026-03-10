"""Contact import tests -- CSV parsing, mapping, duplicate skipping, error tracking.

Refactored to use mock-based fixtures from conftest (no real DB engine).
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helper to build a CSV UploadFile-like payload
# ---------------------------------------------------------------------------

def _csv_content(rows: list[list[str]], header: list[str] | None = None) -> str:
    """Build a CSV string from a header row and data rows."""
    lines = []
    if header:
        lines.append(",".join(header))
    for row in rows:
        lines.append(",".join(row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fake ImportResult helper
# ---------------------------------------------------------------------------

class _FakeImportResult:
    def __init__(self, total=0, imported=0, skipped=0, failed=0, errors=None):
        self.total = total
        self.imported = imported
        self.skipped = skipped
        self.failed = failed
        self.errors = errors or []


# ---------------------------------------------------------------------------
# Test: basic CSV import
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_csv_basic(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/contacts/import with a valid CSV should import contacts."""
    csv = _csv_content(
        header=["phone", "fname", "lname", "email"],
        rows=[
            ["+14155550001", "Alice", "Smith", "alice@example.com"],
            ["+14155550002", "Bob", "Jones", "bob@example.com"],
            ["+14155550003", "Carol", "Lee", "carol@example.com"],
        ],
    )
    mapping = json.dumps({
        "phone": "phone_number",
        "fname": "first_name",
        "lname": "last_name",
        "email": "email",
    })

    fake_result = _FakeImportResult(total=3, imported=3, skipped=0, failed=0)

    with patch(
        "app.routers.contacts.import_contacts_from_csv",
        new_callable=AsyncMock,
        return_value=fake_result,
    ):
        resp = await authenticated_client.post(
            "/api/v1/contacts/import",
            data={"mapping": mapping, "skip_duplicates": "true"},
            files={"file": ("contacts.csv", csv.encode(), "text/csv")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["imported"] == 3
    assert data["skipped"] == 0
    assert data["failed"] == 0


# ---------------------------------------------------------------------------
# Test: CSV import with custom field mapping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_csv_with_mapping(authenticated_client: AsyncClient, db_session):
    """POST /api/v1/contacts/import with custom field mapping should work."""
    csv = _csv_content(
        header=["Phone Number", "Name", "Company"],
        rows=[
            ["+14155550010", "Dave", "Acme Inc"],
            ["+14155550011", "Eve", "Globex"],
        ],
    )
    mapping = json.dumps({
        "Phone Number": "phone_number",
        "Name": "first_name",
        "Company": "company",
    })

    fake_result = _FakeImportResult(total=2, imported=2)

    with patch(
        "app.routers.contacts.import_contacts_from_csv",
        new_callable=AsyncMock,
        return_value=fake_result,
    ):
        resp = await authenticated_client.post(
            "/api/v1/contacts/import",
            data={"mapping": mapping, "skip_duplicates": "true"},
            files={"file": ("contacts.csv", csv.encode(), "text/csv")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2


# ---------------------------------------------------------------------------
# Test: CSV import -- skip duplicates
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_csv_skip_duplicates(authenticated_client: AsyncClient, db_session):
    """Import with duplicates should skip them."""
    csv = _csv_content(
        header=["phone", "fname"],
        rows=[
            ["+15551112222", "Duplicate"],
            ["+14155550099", "New"],
        ],
    )
    mapping = json.dumps({"phone": "phone_number", "fname": "first_name"})

    fake_result = _FakeImportResult(total=2, imported=1, skipped=1)

    with patch(
        "app.routers.contacts.import_contacts_from_csv",
        new_callable=AsyncMock,
        return_value=fake_result,
    ):
        resp = await authenticated_client.post(
            "/api/v1/contacts/import",
            data={"mapping": mapping, "skip_duplicates": "true"},
            files={"file": ("contacts.csv", csv.encode(), "text/csv")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["skipped"] == 1
    assert data["imported"] == 1


# ---------------------------------------------------------------------------
# Test: CSV import -- invalid phones tracked in errors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_csv_invalid_phones_tracked(authenticated_client: AsyncClient, db_session):
    """Invalid phone numbers should be tracked as errors."""
    csv = _csv_content(
        header=["phone", "fname"],
        rows=[
            ["bad-number", "Invalid1"],
            ["12", "Invalid2"],
            ["+14155550088", "Valid"],
        ],
    )
    mapping = json.dumps({"phone": "phone_number", "fname": "first_name"})

    fake_result = _FakeImportResult(
        total=3,
        imported=1,
        failed=2,
        errors=[
            {"row": 1, "error": "Invalid phone number: 'bad-number'"},
            {"row": 2, "error": "Invalid phone number: '12'"},
        ],
    )

    with patch(
        "app.routers.contacts.import_contacts_from_csv",
        new_callable=AsyncMock,
        return_value=fake_result,
    ):
        resp = await authenticated_client.post(
            "/api/v1/contacts/import",
            data={"mapping": mapping, "skip_duplicates": "true"},
            files={"file": ("contacts.csv", csv.encode(), "text/csv")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["failed"] == 2
    assert data["imported"] == 1
    assert len(data["errors"]) == 2
    assert any("Invalid phone" in e["error"] for e in data["errors"])


# ---------------------------------------------------------------------------
# Test: CSV import -- empty file
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_csv_empty_file(authenticated_client: AsyncClient, db_session):
    """Importing an empty CSV should return total=0."""
    csv = _csv_content(header=["phone", "fname"], rows=[])
    mapping = json.dumps({"phone": "phone_number", "fname": "first_name"})

    fake_result = _FakeImportResult(total=0, imported=0)

    with patch(
        "app.routers.contacts.import_contacts_from_csv",
        new_callable=AsyncMock,
        return_value=fake_result,
    ):
        resp = await authenticated_client.post(
            "/api/v1/contacts/import",
            data={"mapping": mapping, "skip_duplicates": "true"},
            files={"file": ("contacts.csv", csv.encode(), "text/csv")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["imported"] == 0
