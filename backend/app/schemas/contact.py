from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class ContactCreate(BaseModel):
    phone_number: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    custom_fields: dict[str, Any] = {}
    opt_in_method: str = "api"
    list_ids: list[UUID] = []


class ContactUpdate(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    custom_fields: dict[str, Any] | None = None
    status: str | None = None


class ContactResponse(BaseModel):
    id: UUID
    phone_number: str
    email: str | None
    first_name: str | None
    last_name: str | None
    custom_fields: dict[str, Any]
    status: str
    opted_in_at: datetime | None
    opted_out_at: datetime | None
    opt_in_method: str | None
    last_messaged_at: datetime | None
    message_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactImportRequest(BaseModel):
    list_id: UUID | None = None
    mapping: dict[str, str]  # csv_column -> field_name
    skip_duplicates: bool = True


class ContactImportResponse(BaseModel):
    total: int
    imported: int
    skipped: int
    failed: int
    errors: list[dict[str, Any]] = []


class ContactBulkAction(BaseModel):
    contact_ids: list[UUID]
    action: str  # delete, tag, add_to_list, remove_from_list
    value: str | None = None  # tag name or list_id
